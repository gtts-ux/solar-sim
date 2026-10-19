"""Version 2 public system-mod format, validation and local Keplerian geometry."""
from datetime import datetime, timezone
import json
import math
import re

from catalog import Body

FORMAT_MIN = '1.10.0'
LIMIT = 65536
MAX_BODIES = 64
EPOCH = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
KINDS = ('Star','Black hole','Planet','Dwarf planet','Moon')
TEXTS = ('temperature','composition','atmosphere','features')
NUMBERS = ('mass','radius','orbit','period','rotation')
ANGLES = ('inclination','node','periapsis','phase')
RESERVED = {'proxima-centauri','interstellar','exit','help','tutorial','inner','outer','con','prn','aux','nul',
            *('com'+str(i) for i in range(1,10)), *('lpt'+str(i) for i in range(1,10))}


def identifier(value):
    if not isinstance(value,str) or not 3<=len(value)<=48 or not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*',value):
        raise ValueError('id must be 3-48 lowercase letters/digits, with optional single hyphens.')
    if value in RESERVED:
        raise ValueError('This id is reserved; choose your own unique mod id.')
    return value


def text(value, label, limit=1200):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or not value.isprintable():
        raise ValueError(label+' must be printable text, 1-'+str(limit)+' characters.')
    return value


def body_name(value):
    text(value,'Body name or alias',48)
    if value!=value.strip() or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._-]*',value):
        raise ValueError('Body names/aliases use letters, digits, spaces, dots, underscores or hyphens.')
    return value


def semver(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{1,5}\.\d{1,5}\.\d{1,5}',value):
        raise ValueError('Versions use three numbers, for example 1.0.0.')
    return tuple(map(int,value.split('.')))


def validate(content, expected_id=None):
    try:
        if len(content)>LIMIT:raise ValueError('Package exceeds 64 KiB.')
        data=json.loads(content)
        required={'format','id','name','description','version','app_min','fictional','sources','bodies'}
        if not isinstance(data,dict) or set(data)!=required or type(data['format']) is not int or data['format']!=2:
            raise ValueError('Use format 2 and the documented top-level fields; start with --mod-template.')
        identifier(data['id'])
        if expected_id is not None and data['id']!=expected_id:raise ValueError('Package id differs from its installed filename.')
        text(data['name'],'Mod name',64);text(data['description'],'Description')
        semver(data['version'])
        if semver(data['app_min'])<semver(FORMAT_MIN):raise ValueError('Format 2 requires app_min '+FORMAT_MIN+' or newer.')
        if type(data['fictional']) is not bool:raise ValueError('fictional must be true or false.')
        sources=data['sources']
        if not isinstance(sources,list) or len(sources)>12 or (not data['fictional'] and not sources):
            raise ValueError('Provide up to 12 source links; real systems require at least one.')
        for source in sources:
            text(source,'Source URL',300)
            if not source.startswith('https://'):raise ValueError('Source links must use HTTPS.')
        entries=data['bodies']
        if not isinstance(entries,list) or not 2<=len(entries)<=MAX_BODIES:
            raise ValueError('Include one central body and 1-63 orbiting bodies (64 total).')
        by_name={};aliases={}
        base={'name','kind','parent','color',*NUMBERS,*TEXTS}
        optional={'aliases','estimated_mass','estimated_radius','eccentricity',*ANGLES}
        for i,entry in enumerate(entries):
            if not isinstance(entry,dict) or not base<=set(entry) or set(entry)-base-optional:
                raise ValueError('A body has missing or unsupported fields; check the tutorial field table.')
            name=body_name(entry['name']);key=name.lower()
            if key in by_name:raise ValueError('Duplicate body name: '+name)
            by_name[key]=entry
            if entry['kind'] not in KINDS:raise ValueError(name+': choose kind '+', '.join(KINDS)+'.')
            if type(entry['color']) is not int or not 1<=entry['color']<=7:raise ValueError(name+': color must be 1-7.')
            for field in (*NUMBERS,*ANGLES,'eccentricity'):
                value=entry.get(field,0.)
                if type(value) not in (float,int) or not math.isfinite(value):raise ValueError(name+': '+field+' must be finite.')
            if not 1e10<=entry['mass']<=1e40 or not .001<=entry['radius']<=1e10:
                raise ValueError(name+': mass/radius outside supported bounds; see tutorial.')
            if not -1e6<=entry['rotation']<=1e6:raise ValueError(name+': rotation must be between -1000000 and 1000000 hours.')
            if not 0<=entry.get('eccentricity',0)<.95:raise ValueError(name+': eccentricity must be at least 0 and below 0.95.')
            if not 0<=entry.get('inclination',0)<=180:raise ValueError(name+': inclination must be 0-180 degrees.')
            for field in ('node','periapsis','phase'):
                if not 0<=entry.get(field,0)<360:raise ValueError(name+': '+field+' must be 0 to less than 360 degrees.')
            if i==0:
                if entry['parent'] is not None or entry['kind'] not in ('Star','Black hole') or entry['orbit']!=0 or entry['period']!=0:
                    raise ValueError('The first body must be a central Star/Black hole with parent null, orbit 0 and period 0.')
                if entry.get('eccentricity',0)!=0:raise ValueError('The central body has no eccentric orbit.')
            else:
                body_name(entry['parent'])
                if entry['kind'] in ('Star','Black hole'):raise ValueError('Format 2 supports one central star or black hole.')
                if not .001<=entry['orbit']<=1e13 or not .0001<=entry['period']<=1e9:
                    raise ValueError(name+': orbit/period outside supported bounds; see tutorial.')
            for field in TEXTS:text(entry[field],name+' '+field)
            for field in ('estimated_mass','estimated_radius'):
                if field in entry and type(entry[field]) is not bool:raise ValueError(name+': '+field+' must be true or false.')
            names=entry.get('aliases',[])
            if not isinstance(names,list) or len(names)>8:raise ValueError(name+': aliases must be a list with up to 8 names.')
            for alias in [name,*names]:
                body_name(alias);alias=alias.lower()
                if alias=='core' and i!=0:raise ValueError('core is reserved for the central body.')
                if alias in aliases:raise ValueError('Duplicate name or alias: '+alias)
                aliases[alias]=name
        root=entries[0]['name']
        for entry in entries[1:]:
            parent=by_name.get(entry['parent'].lower())
            if parent is None or entry['parent']!=parent['name']:raise ValueError(entry['name']+': parent must exactly match another body name.')
            if entry['kind'] in ('Planet','Dwarf planet') and parent['name']!=root:
                raise ValueError(entry['name']+': planets/dwarfs must orbit the central body.')
            if entry['kind']=='Moon' and parent['kind'] not in ('Planet','Dwarf planet','Moon'):
                raise ValueError(entry['name']+': a Moon must orbit a planet, dwarf or another moon.')
            seen={entry['name']};node=entry
            while node['parent'] is not None:
                if node['parent'] in seen:raise ValueError('Parent cycle involving '+entry['name']+'.')
                seen.add(node['parent'])
                if len(seen)>8:raise ValueError('Limit parent chains to eight bodies.')
                node=by_name.get(node['parent'].lower())
                if node is None:raise ValueError('Unknown parent.')
            if node['name']!=root:raise ValueError('All bodies must belong to the one central system.')
        return data
    except (ValueError,KeyError,TypeError,OverflowError,RecursionError,UnicodeError) as error:
        raise ValueError('Invalid community mod: '+str(error)) from error


def bodies(data):
    result=[]
    for entry in data['bodies']:
        values={key:entry[key] for key in ('name','kind','parent','color',*NUMBERS,*TEXTS)}
        values['eccentricity']=entry.get('eccentricity',0.)
        values['estimated_mass']=entry.get('estimated_mass',True)
        values['known_moons']=sum(b['parent']==entry['name'] and b['kind']=='Moon' for b in data['bodies'])
        result.append(Body(**values))
    return result


def offset(body, entry, date, anomaly=None):
    """Parent-relative ellipse; phase is mean anomaly at 2000-01-01 12:00 UTC."""
    if anomaly is None:
        mean=(math.radians(entry.get('phase',0))+(date-EPOCH).total_seconds()/86400/body.period*math.tau)%math.tau
        anomaly=mean if body.eccentricity<.8 else math.pi
        for _ in range(35):
            delta=(anomaly-body.eccentricity*math.sin(anomaly)-mean)/(1-body.eccentricity*math.cos(anomaly))
            anomaly-=delta
            if abs(delta)<1e-12:break
    x=body.orbit*(math.cos(anomaly)-body.eccentricity)
    y=body.orbit*math.sqrt(1-body.eccentricity**2)*math.sin(anomaly)
    inc,node,peri=map(math.radians,(entry.get('inclination',0),entry.get('node',0),entry.get('periapsis',0)))
    ci,si,cn,sn,cw,sw=math.cos(inc),math.sin(inc),math.cos(node),math.sin(node),math.cos(peri),math.sin(peri)
    return ((cw*cn-sw*sn*ci)*x+(-sw*cn-cw*sn*ci)*y,
            (cw*sn+sw*cn*ci)*x+(-sw*sn+cw*cn*ci)*y,sw*si*x+cw*si*y)


def notice(data):
    return (data['name'].upper()+' / COMMUNITY SYSTEM'+(' / FICTIONAL' if data['fictional'] else '')+'\n\n'+
            data['description']+'\n\nAuthor-supplied data; local Keplerian illustration, not a live ephemeris.\n'
            '/planet lists planets  /body NAME opens any body  /core opens the center\n'
            '/orbit  /moons NAME  /compare NAME NAME  /sources\n'
            '/mod exit returns to normal planets. /mods lists installed catalogues.')


def describe(body, data, date, position):
    entry=next(b for b in data['bodies'] if b['name']==body.name)
    radius_note=' (estimate/model value)' if entry.get('estimated_radius',True) else ' (author-supplied)'
    mass_note=' (estimate/model value)' if body.estimated_mass else ' (author-supplied)'
    rows=[body.name.upper()+' / '+body.kind,'',data['name']+' / '+('Fictional community system' if data['fictional'] else 'Community-supplied catalogue'),
          '  Parent               '+(body.parent or 'Local system origin'),
          f'  Mass                 {body.mass:.6g} kg'+mass_note,
          f'  Mean radius          {body.radius:,.3f} km'+radius_note,
          f'  Diameter             {2*body.radius:,.3f} km'+radius_note,
          f'  Orbital radius       {body.orbit:,.3f} km (semi-major axis)',
          f'  Orbital period       {body.period:g} Earth days' if body.parent else '  Orbital period       Not applicable to the central body',
          f'  Sidereal rotation    {abs(body.rotation):g} hours'+(' (retrograde)' if body.rotation<0 else '') if body.rotation else '  Sidereal rotation    Unknown / unspecified',
          f'  Eccentricity         {body.eccentricity:g}',
          f'  Included moons       {body.known_moons} (not a complete census)',
          '', 'TEMPERATURE','  '+body.temperature,'','COMPOSITION','  '+body.composition,
          '', 'ATMOSPHERE','  '+body.atmosphere,'','NOTES','  '+body.features,
          '', 'POSITION / '+data['bodies'][0]['name']+' centered; illustrative Keplerian model',
          f'  UTC                  {date:%Y-%m-%d %H:%M:%S}',
          '  X / Y / Z (km)       '+' / '.join(f'{p:,.3f}' for p in position(body)),
          '', '/orbit  /body NAME  /sources  /mod exit']
    return '\n'.join(rows)
