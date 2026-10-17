"""Cached Launch Library 2 status data. No generated flight telemetry."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

UTC=timezone.utc
API='https://ll.thespacedevs.com/2.3.0/launches/'
SOURCE='The Space Devs / Launch Library 2'
INTERVAL=900


def now_utc():return datetime.now(UTC)


def date(value):
    if not isinstance(value,str):return None
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:return None


def clean(value,limit=240):
    return ' '.join(''.join(c for c in str(value or '') if c.isprintable() or c in '\n\t').split())[:limit]


def https_url(value):
    if not isinstance(value,str) or any(c.isspace() or not c.isprintable() for c in value):return ''
    try:
        parsed=urlsplit(value)
        return value if parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password else ''
    except ValueError:return ''


@dataclass(frozen=True)
class Launch:
    id: str
    name: str
    provider: str
    groups: tuple
    net: str
    status_id: int
    status: str
    rocket: str
    pad: str
    description: str
    webcasts: tuple
    updated: str=''
    precision: str=''

    @property
    def in_flight(self):return self.status_id==6


def parse_launch(row):
    if not isinstance(row,dict) or not row.get('id') or not isinstance(row.get('name'),str):return None
    provider=row.get('launch_service_provider') or {}
    mission=row.get('mission') or {}
    rocket=(row.get('rocket') or {}).get('configuration') or {}
    pad=row.get('pad') or {}
    status=row.get('status') or {}
    if not all(isinstance(x,dict) for x in (provider,mission,rocket,pad,status)):return None
    provider_name=clean(provider.get('name'))
    agency_names=[provider_name]
    for parent in [mission,*[p for p in row.get('program') or [] if isinstance(p,dict)]]:
        agency_names += [clean(a.get('name')) for a in parent.get('agencies') or [] if isinstance(a,dict)]
    names=' / '.join(agency_names).lower()
    groups=[]
    if 'spacex' in names or 'space exploration technologies' in names:groups.append('spacex')
    if any(n.lower()=='nasa' or 'national aeronautics' in n.lower() for n in agency_names):groups.append('nasa')
    rocket_name=clean(rocket.get('full_name') or rocket.get('name'))
    if ('european space agency' in names or any(n.lower()=='esa' for n in agency_names)
        or 'arianespace' in provider_name.lower() or provider_name.lower()=='avio'
        or rocket_name.lower().startswith(('ariane','vega'))):groups.append('esa')
    if not groups:return None
    try:status_id=int(status.get('id',0))
    except (ValueError,TypeError):return None
    videos=[]
    for item in row.get('vid_urls') or []:
        if isinstance(item,dict):
            url=https_url(item.get('url'))
            if url and url not in videos:videos.append(url)
    return Launch(clean(row['id'],120),clean(row['name']),provider_name or 'Provider unspecified',tuple(groups),
                  clean(row.get('net')),status_id,clean(status.get('name') or 'Status unknown'),rocket_name,
                  clean(pad.get('name')),clean(mission.get('description'),1500),tuple(videos),
                  clean(row.get('last_updated')),clean((row.get('net_precision') or {}).get('name')))


def parse_page(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('results'),list):
        raise ValueError('Launch provider returned an invalid result list.')
    rows=[]
    for item in payload['results']:
        try:launch=parse_launch(item)
        except (AttributeError,TypeError,ValueError):launch=None
        if launch is not None:rows.append(launch)
    return rows,payload.get('next')


def get_json(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.netloc!='ll.thespacedevs.com' or not parsed.path.startswith('/2.3.0/launches/'):
        raise ValueError('Unexpected launch pagination URL.')
    request=Request(url,headers={'Accept':'application/json','User-Agent':'SolarSim/1.2 (terminal launch monitor)'})
    with urlopen(request,timeout=12) as response:
        content=response.read(12_000_001)
    if len(content)>12_000_000:raise ValueError('Launch provider response was too large.')
    return json.loads(content)


class LaunchFeed:
    def __init__(self,path):
        self.path=Path(path)
        self.lock=threading.RLock()
        self.rows=()
        self.updated=None
        self.next_request=None
        self.attempts=[]
        self.error=''
        self.thread=None
        self.cancel=threading.Event()
        self.revision=0
        try:
            if self.path.stat().st_size>12_000_000:raise ValueError('Oversized cache')
            payload=json.loads(self.path.read_text(encoding='utf-8'))
            if payload.get('version')!=1:raise ValueError('Unknown cache')
            rows=[]
            for row in payload.get('rows',[]):
                if not isinstance(row,dict):raise ValueError('Invalid cache row')
                row=dict(row);row['groups']=tuple(row['groups']);row['webcasts']=tuple(row['webcasts'])
                item=Launch(**row)
                if not isinstance(item.name,str) or not isinstance(item.status_id,int):raise ValueError('Invalid cache')
                rows.append(item)
            self.rows=tuple(rows)
            self.updated=date(payload.get('updated'))
            self.next_request=date(payload.get('next_request'))
            self.attempts=[value for value in (date(v) for v in payload.get('attempts',[])) if value]
            self.error=clean(payload.get('error'),200)
        except (OSError,ValueError,TypeError,KeyError,AttributeError):pass

    @property
    def busy(self):return self.thread is not None and self.thread.is_alive()

    def snapshot(self):
        with self.lock:return self.rows,self.updated,self.error,self.busy

    def save(self):
        with self.lock:
            payload={'version':1,'updated':self.updated.isoformat() if self.updated else None,
                     'next_request':self.next_request.isoformat() if self.next_request else None,
                     'attempts':[d.isoformat() for d in self.attempts],'rows':[asdict(r) for r in self.rows],
                     'error':self.error}
            temporary=self.path.with_name(self.path.name+f'.{os.getpid()}.tmp')
            try:
                temporary.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
                temporary.replace(self.path)
            except OSError:pass
            finally:
                try:temporary.unlink(missing_ok=True)
                except OSError:pass

    def request(self):
        with self.lock:
            if self.busy or self.cancel.is_set():return
            now=now_utc()
            if self.next_request and now<self.next_request:return
            self.next_request=now+timedelta(seconds=INTERVAL)
            self.thread=threading.Thread(target=self._sync,daemon=True,name='launch-status-feed')
            self.thread.start()

    def _request_page(self,url):
        with self.lock:
            now=now_utc()
            self.attempts=[d for d in self.attempts if d>now-timedelta(hours=1)]
            if len(self.attempts)>=12:raise ValueError('Hourly refresh budget reached; cached data retained.')
            self.attempts.append(now)
            self.save()
        return parse_page(get_json(url))

    def _sync(self):
        try:
            rows=[]
            url=API+'?'+urlencode({'status':6,'limit':100,'mode':'normal'})
            visited=set()
            while url and not self.cancel.is_set():
                if url in visited or len(visited)>=5:raise ValueError('In-flight feed pagination was incomplete.')
                visited.add(url)
                page,url=self._request_page(url)
                rows.extend(page)
            if self.cancel.is_set():return
            page,_=self._request_page(API+'upcoming/?'+urlencode({'limit':100,'mode':'normal'}))
            rows.extend(page)
            # The active-status endpoint wins over a duplicate in the upcoming endpoint.
            unique={}
            for row in rows:
                if row.id not in unique:unique[row.id]=row
            now=now_utc()
            filtered=[r for r in unique.values() if r.status_id in (1,2,5,6,8)]
            filtered.sort(key=lambda r:(not r.in_flight,date(r.net) or datetime.max.replace(tzinfo=UTC),r.name))
            with self.lock:
                self.rows=tuple(filtered);self.updated=now;self.error='';self.revision+=1
        except HTTPError as error:
            with self.lock:
                self.error=f'Launch provider HTTP {error.code}; cached status is unverified.'
                if error.code==429:
                    retry=(error.headers or {}).get('Retry-After','900')
                    try:delay=max(INTERVAL,int(retry))
                    except ValueError:
                        try:delay=max(INTERVAL,(parsedate_to_datetime(retry)-now_utc()).total_seconds())
                        except (TypeError,ValueError):delay=INTERVAL
                    self.next_request=now_utc()+timedelta(seconds=delay)
            error.close()
        except Exception as error:
            with self.lock:self.error='Launch update unavailable: '+clean(str(error),180)
        finally:self.save()

    def label(self):
        _,updated,error,busy=self.snapshot()
        age=(now_utc()-updated).total_seconds() if updated else None
        state='CACHED / STATUS UNVERIFIED' if age is not None and (age>INTERVAL or age<-5 or error) else 'FETCHED STATUS'
        text=f'{state} / {updated:%Y-%m-%d %H:%M:%S} UTC' if updated else 'No launch data has been fetched yet.'
        if busy:text+=' / Updating in background...'
        if error:text+='\n'+error
        if self.next_request:text+=f'\nNext refresh allowed: {self.next_request:%H:%M:%S} UTC (15-minute cache).'
        return text


def countdown(launch,now=None):
    now=now or now_utc();net=date(launch.net)
    if net is None:return 'Time to be announced'
    seconds=int((net-now).total_seconds())
    if launch.in_flight and net>now:return 'In flight reported; source NET is future, elapsed time unavailable'
    if seconds<0 and not launch.in_flight:return 'Scheduled time passed; awaiting provider confirmation'
    value=abs(seconds);days,value=divmod(value,86400);hours,value=divmod(value,3600);minutes,seconds=divmod(value,60)
    return f'T{"+" if launch.in_flight else "-"}{days}d {hours:02}:{minutes:02}:{seconds:02}'


def launch_detail(launch):
    net=date(launch.net)
    lines=[launch.name.upper(),f'Provider: {launch.provider}',f'Status: {launch.status}',countdown(launch),
           f'NET (not earlier than): {net:%Y-%m-%d %H:%M:%S} UTC' if net else 'NET: to be announced',
           f'Time precision: {launch.precision or "Not supplied"}',f'Rocket: {launch.rocket or "Not supplied"}',
           f'Pad: {launch.pad or "Not supplied"}',launch.description or 'No mission description supplied.','',
           'WEBCASTS / links supplied by the launch feed',*(launch.webcasts or ('No webcast link announced yet.',)),
           '',f'Source: {SOURCE}','Live status and countdown only; no live spacecraft position or flight path.']
    return '\n'.join(lines)
