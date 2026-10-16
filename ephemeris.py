"""Nonblocking NASA/JPL Horizons vectors with a local cache and bounded interpolation."""
from bisect import bisect_right
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import math
from pathlib import Path
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

IDS = dict(zip(('Mercury','Venus','Earth','Mars','Jupiter','Saturn','Uranus','Neptune'),
               (199,299,399,499,599,699,799,899)))
IDS.update({'Moon':301,'Phobos':401,'Deimos':402,'Amalthea':505,'Io':501,'Europa':502,
            'Ganymede':503,'Callisto':504,'Mimas':601,'Enceladus':602,'Tethys':603,
            'Dione':604,'Rhea':605,'Titan':606,'Hyperion':607,'Iapetus':608,'Phoebe':609,
            'Miranda':705,'Ariel':701,'Umbriel':702,'Titania':703,'Oberon':704,
            'Proteus':808,'Triton':801,'Nereid':802})
IDS.update({'Ceres':'1;','Pluto':999,'Haumea':'136108;','Makemake':'136472;',
            'Eris':'136199;','Charon':901})
API = 'https://ssd.jpl.nasa.gov/api/horizons.api'
CACHE = Path(__file__).with_name('ephemeris_cache.json')


def parse_vectors(payload):
    if payload.get('signature',{}).get('version') != '1.3':
        raise ValueError('Unsupported Horizons API version; using offline positions.')
    if payload.get('error'):
        raise ValueError(str(payload['error'])[:180])
    result = payload.get('result','')
    if '$$SOE' not in result or '$$EOE' not in result:
        raise ValueError('Horizons returned no vector table.')
    records = []
    table = result.split('$$SOE',1)[1].split('$$EOE',1)[0].strip()
    for row in csv.reader(io.StringIO(table)):
        if not row:
            continue
        if len(row) < 8:
            raise ValueError('Incomplete Horizons vector record.')
        jd = float(row[0])
        state = [float(v.replace('D','E')) for v in row[2:8]]
        record = [(jd-2440587.5)*86400, *state]
        if not all(math.isfinite(v) for v in record):
            raise ValueError('Invalid Horizons vector value.')
        records.append(record)
    if len(records) < 2 or any(a[0]>=b[0] for a,b in zip(records,records[1:])):
        raise ValueError('Horizons timestamps must be increasing.')
    return records


def interpolate(records, timestamp, velocity=False):
    """Cubic Hermite interpolation of km positions and km/s velocities; no extrapolation."""
    if not records or not records[0][0] <= timestamp <= records[-1][0]:
        return None
    index = min(len(records)-2, max(0,bisect_right([row[0] for row in records],timestamp)-1))
    a,b = records[index:index+2]
    seconds = b[0]-a[0]
    t = (timestamp-a[0])/seconds
    h00,h10,h01,h11 = 2*t**3-3*t*t+1, t**3-2*t*t+t, -2*t**3+3*t*t, t**3-t*t
    if velocity:
        h00,h10,h01,h11 = (6*t*t-6*t)/seconds, (3*t*t-4*t+1)/seconds, (-6*t*t+6*t)/seconds, (3*t*t-2*t)/seconds
    return tuple(h00*a[i]+h10*seconds*a[i+3]+h01*b[i]+h11*seconds*b[i+3] for i in (1,2,3))


def fetch_vectors(body_id, start, stop):
    options = {'COMMAND':str(body_id),'OBJ_DATA':'NO','MAKE_EPHEM':'YES',
               'EPHEM_TYPE':'VECTORS','CENTER':'500@10',
               'START_TIME':start.strftime('%Y-%m-%d %H:%M'),
               'STOP_TIME':stop.strftime('%Y-%m-%d %H:%M'),'STEP_SIZE':'15 m',
               'TIME_TYPE':'UT','REF_PLANE':'ECLIPTIC','REF_SYSTEM':'ICRF',
               'OUT_UNITS':'KM-S','VEC_TABLE':'2','VEC_CORR':'NONE','CSV_FORMAT':'YES'}
    query = {'format':'json', **{k:"'"+v+"'" for k,v in options.items()}}
    request = Request(API+'?'+urlencode(query),headers={'User-Agent':'SolarSim/2.0'})
    with urlopen(request,timeout=8) as response:
        payload = json.loads(response.read(3_000_000))
    return parse_vectors(payload)


class Ephemeris:
    def __init__(self, online=False, cache_path=CACHE):
        self.online = online
        self.path = cache_path
        self.records = {}
        self.lock = threading.Lock()
        self.thread = None
        self.last_attempt = -math.inf
        self.message = 'Offline approximation; /sync downloads JPL positions'
        self.errors = []
        self.cancel = threading.Event()
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('version') == 1:
                for name,rows in data.get('bodies',{}).items():
                    if name in IDS and len(rows)>=2 and all(len(row)==7 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in row) for row in rows) and all(a[0]<b[0] for a,b in zip(rows,rows[1:])):
                        self.records[name] = rows
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        if self.records:
            self.message = 'JPL cache loaded / sources listed per body'

    @property
    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    def position(self, body, date):
        if body.name == 'Sun':
            return (0.,0.,0.)
        with self.lock:
            rows = self.records.get(body.name)
        return interpolate(rows,date.timestamp()) if rows else None

    def source(self, body, date):
        if body.name == 'Sun':
            return 'Heliocentric origin'
        if body.kind == 'Artificial satellite':
            if not body.planned and date.strftime('%Y-%m-%d')<body.insertion:
                return 'Not in orbit at the selected date'
            return 'PLANNED preview / not a current orbit' if body.planned else 'Illustrative spacecraft orbit / not live tracking'
        if self.position(body,date) is not None:
            return 'JPL Horizons / interpolated'
        if body.kind == 'Dwarf planet':
            return 'Illustrative dwarf orbit / sync for JPL'
        return 'Offline Kepler approximation' if body.parent == 'Sun' else 'Illustrative moon orbit'

    def velocity(self, body, date):
        if body.name == 'Sun':
            return (0.,0.,0.)
        with self.lock:
            rows = self.records.get(body.name)
        return interpolate(rows,date.timestamp(),velocity=True) if rows else None

    def ensure(self, date, force=False):
        if self.busy or self.cancel.is_set() or (not self.online and not force):
            return
        if not force and time.monotonic()-self.last_attempt < 300:
            return
        timestamp = (date+timedelta(hours=2)).timestamp()
        with self.lock:
            covered = all(name in self.records and self.records[name][0][0]<=date.timestamp()
                          and self.records[name][-1][0]>=timestamp for name in IDS)
        if not force and covered:
            self.message = f'JPL Horizons cache ready / {len(IDS)} bodies'
            return
        self.last_attempt = time.monotonic()
        self.online = True
        self.thread = threading.Thread(target=self._sync,args=(date,force),daemon=True)
        self.thread.start()

    def _sync(self, date, force):
        start = date.replace(minute=0,second=0,microsecond=0)-timedelta(hours=1)
        stop = start+timedelta(hours=26)
        self.errors = []
        loaded = 0
        for name,body_id in IDS.items():
            if self.cancel.is_set():
                break
            with self.lock:
                rows = self.records.get(name)
            if not force and rows and rows[0][0]<=date.timestamp() and rows[-1][0]>=(date+timedelta(hours=2)).timestamp():
                loaded += 1
                continue
            self.message = f'JPL sync {loaded}/{len(IDS)} / {name}'
            try:
                rows = fetch_vectors(body_id,start,stop)
                with self.lock:
                    self.records[name] = rows
                loaded += 1
            except Exception as error:
                self.errors.append(f'{name}: {error}')
                # A broken connection should not cause a timeout for every body.
                if len(self.errors)>=3:
                    break
            if self.cancel.wait(.08):
                break
        try:
            with self.lock:
                data = {'version':1,'source':'NASA/JPL Horizons, heliocentric J2000 ecliptic, UT, km and km/s',
                        'downloaded_utc':datetime.now(timezone.utc).isoformat(),'bodies':dict(self.records)}
            if data['bodies']:
                import os
                temporary = self.path.with_suffix(f'.{os.getpid()}.tmp')
                temporary.write_text(json.dumps(data),encoding='utf-8')
                temporary.replace(self.path)
        except OSError as error:
            self.errors.append(f'Cache: {error}')
        self.message = f'JPL sync finished / {loaded}/{len(IDS)} bodies'
        if self.errors:
            self.message += ' / some offline; /sync status'

    def details(self):
        return self.message + '\n\n' + ('\n'.join(self.errors) if self.errors else
            'Cached vectors are interpolated only within their downloaded time window.\nOutside that window the offline model is used and labeled.')
