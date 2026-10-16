"""Selected human-made orbiters. Status snapshot 2026-10-16; orbits are illustrative."""
from dataclasses import dataclass
import math

from catalog import ALIASES, BODIES, Body, G, lookup

STATUS_DATE = '2026-10-16'


@dataclass(frozen=True)
class Spacecraft(Body):
    agency: str = ''
    insertion: str = ''
    status: str = ''
    mission_end: str = ''
    planned: bool = False
    inclination: float = 0
    node: float = 0
    source_url: str = ''
    notes: str = ''


def craft(name,parent,mass,span,peri,apo,inclination,agency,insertion,status,purpose,source,
          mission_end='',planned=False,notes=''):
    primary = lookup(parent)
    closest,farthest = primary.radius+peri,primary.radius+apo
    axis = (closest+farthest)/2
    period = math.tau*math.sqrt((axis*1000)**3/(G*primary.mass))/86400
    return Spacecraft(name,'Artificial satellite',parent,mass,span/2000,axis,period,0,
                      'Not applicable','Engineered spacecraft; quoted mass/span are approximate.',
                      'No atmosphere.',purpose,6,eccentricity=(farthest-closest)/(farthest+closest),
                      estimated_mass=True,agency=agency,insertion=insertion,status=status,
                      mission_end=mission_end,planned=planned,inclination=inclination,
                      node=sum(map(ord,name))%360,source_url=source,notes=notes)


SPACECRAFT = [
    craft('ISS','Earth',420000,109,400,420,51.64,'NASA / Roscosmos / ESA / JAXA / CSA','1998-11-20',
          'Operating space station','Crewed orbital laboratory; orbit is regularly reboosted.',
          'https://www.nasa.gov/international-space-station/space-station-facts-and-figures/'),
    craft('Tiangong','Earth',100000,55,390,400,41.5,'CMSA','2021-04-29','Operating space station',
          'Chinese modular crewed space station. Mass/configuration changes with visiting vehicles.',
          'https://en.cmse.gov.cn/'),
    craft('Hubble','Earth',11110,13.2,500,530,28.5,'NASA / ESA','1990-04-25','Operating observatory',
          'Space telescope observing ultraviolet, visible and near-infrared light.',
          'https://science.nasa.gov/mission/hubble/'),
    craft('Odyssey','Mars',725,6,400,400,93.1,'NASA','2001-10-24','Operating orbiter',
          '2001 Mars Odyssey: surface composition, thermal observations and rover relay.',
          'https://science.nasa.gov/mission/odyssey/'),
    craft('MRO','Mars',2180,13.6,250,316,92.7,'NASA','2006-03-10','Operating orbiter',
          'Mars Reconnaissance Orbiter: high-resolution imaging, subsurface radar and communications.',
          'https://science.nasa.gov/mission/mars-reconnaissance-orbiter/'),
    craft('MarsExpress','Mars',1120,12,300,10000,86.3,'ESA','2003-12-25','Operating orbiter',
          'Mars Express studies surface, interior, atmosphere and the martian environment.',
          'https://www.esa.int/Science_Exploration/Space_Science/Mars_Express'),
    craft('TGO','Mars',3700,17.5,400,400,74,'ESA / Roscosmos','2016-10-19','Operating orbiter',
          'ExoMars Trace Gas Orbiter studies atmospheric trace gases and relays surface-mission data.',
          'https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/Exploration/ExoMars/Trace_Gas_Orbiter'),
    craft('Hope','Mars',1350,7.9,20000,43000,25,'UAE Space Agency / MBRSC','2021-02-09','Operating orbiter',
          'Emirates Mars Mission: global martian atmosphere and weather.',
          'https://www.space.gov.ae/en/'),
    craft('Tianwen1','Mars',3175,13.4,265,12000,86.9,'CNSA','2021-02-10','Orbiter; science reported in 2026',
          'Tianwen-1 orbiter: remote sensing of Mars; nominal survey ellipse shown.',
          'https://arxiv.org/abs/2603.10350'),
    craft('MAVEN','Mars',2454,11.4,150,4500,75,'NASA','2014-09-22','Inactive; mission ended 2026-06-03',
          'Former atmospheric-science orbiter, still in orbit. Its last nominal orbit is illustrated.',
          'https://www.nasa.gov/news-release/nasa-says-farewell-to-maven-mars-mission-hosts-media-call-today/',
          mission_end='2026-06-03',notes='Last contact December 2025; actual present trajectory is not known here.'),
    craft('Juno','Jupiter',3625,20,4200,8000000,90,'NASA','2016-07-05','Orbiter; current operating status not independently verified',
          "Investigates Jupiter's interior, atmosphere and magnetic field; representative early science ellipse.",
          'https://science.nasa.gov/mission/juno/',notes='Orbit evolves substantially; this is not its current flight trajectory.'),
    craft('Akatsuki','Venus',518,5.1,1000,360000,172,'JAXA','2015-12-07','Inactive; mission terminated 2025-09-18',
          'Former Venus climate orbiter. Last nominal orbit shown; no current tracking is available here.',
          'https://cosmos.isas.jaxa.jp/our-last-presence-at-venus-has-gone-silent/',mission_end='2025-09-18'),
    craft('Dawn','Ceres',747,19.7,35,4000,90,'NASA','2015-03-06','Inactive; remains in Ceres orbit',
          'Former Ceres explorer; final low elliptical orbit illustrated.',
          'https://science.nasa.gov/mission/dawn/mission-status/',mission_end='2018-11-01'),
    craft('LRO','Moon',1916,5,50,200,90,'NASA','2009-06-23','Lunar orbiter',
          'Lunar Reconnaissance Orbiter maps the Moon and scouts exploration sites.',
          'https://science.nasa.gov/mission/lro/'),
    craft('MPO','Mercury',1200,7.5,480,1500,90,'ESA / BepiColombo','2026-11-21',
          'UPCOMING: Mercury capture scheduled 2026-11-21',
          'BepiColombo Mercury Planetary Orbiter will study the surface and interior.',
          'https://www.esa.int/Science_Exploration/Space_Science/BepiColombo/BepiColombo_factsheet',planned=True,
          notes='Not orbiting Mercury as of 2026-10-16. Stack capture planned 21 November; separation December; science April 2027.'),
    craft('Mio','Mercury',275,1.8,590,11640,90,'JAXA / BepiColombo','2026-11-21',
          'UPCOMING: Mercury capture scheduled 2026-11-21',
          'BepiColombo Mercury Magnetospheric Orbiter will investigate the magnetic environment.',
          'https://www.esa.int/Science_Exploration/Space_Science/BepiColombo/BepiColombo_factsheet',planned=True,
          notes='Not orbiting Mercury as of 2026-10-16. Planned science ellipse shown only in preview; separation planned December 2026.'),
]

for item in SPACECRAFT:
    BODIES[item.name.lower()] = item
ALIASES.update({'international space station':'iss','station':'iss','mars reconnaissance orbiter':'mro',
                'mars express':'marsexpress','mars odyssey':'odyssey','trace gas orbiter':'tgo',
                'tianwen-1':'tianwen1','bepicolombo':'mpo','bepi':'mpo','mercury planetary orbiter':'mpo'})


def orbiters(parent, date=None, preview=False):
    cutoff = date.strftime('%Y-%m-%d') if date else STATUS_DATE
    return [s for s in SPACECRAFT if s.parent.lower()==parent.lower() and
            ((s.planned and preview) or (not s.planned and s.insertion<=cutoff))]


def mission_profile(body,date,position_fn=None):
    parent = lookup(body.parent)
    future = body.planned or date.strftime('%Y-%m-%d')<body.insertion
    status = body.status if body.planned or not body.mission_end or date.strftime('%Y-%m-%d')>=body.mission_end else 'Mission had not yet reached its catalogued end date'
    lines = [f'{body.name.upper()} / Artificial satellite','',body.features,'','MISSION PROFILE',
             f'  Parent / destination   {body.parent}',f'  Agency                 {body.agency}',
             f'  Catalogue status       {status}',f'  Orbit insertion        {body.insertion}'+(' (planned, not confirmed)' if body.planned else ''),
             f'  Approximate mass       {body.mass:,.0f} kg (configuration-dependent)',
             f'  Approximate span       {2*body.radius*1000:,.1f} m',
             f'  Nominal periapsis      {body.orbit*(1-body.eccentricity)-parent.radius:,.0f} km above reference radius',
             f'  Nominal apoapsis       {body.orbit*(1+body.eccentricity)-parent.radius:,.0f} km above reference radius',
             f'  Model orbital period   {body.period*24*60:,.1f} minutes (derived from nominal ellipse)',
             f'  Nominal inclination    {body.inclination:g} degrees',
             '', 'ORBIT MODEL / illustrative, not live tracking',
             '  Approximate ellipse, synthetic phase/node, no TLE/SGP4 or live spacecraft ephemeris.',
             '  Not suitable for finding ISS in the sky or determining spacecraft visibility.',
             '  No surface gravity or density is assigned to engineered spacecraft.']
    if body.notes:
        lines += ['  '+body.notes]
    if future:
        lines += ['', '  Not shown as a current orbiter. For planned missions:',f'  /satellites {body.parent.lower()} preview']
    elif position_fn:
        xyz=position_fn(body)
        lines += ['',f'ILLUSTRATIVE POSITION / {date:%Y-%m-%d %H:%M:%S} UTC',
                  '  Heliocentric km: '+ ' / '.join(f'{v:,.2f}' for v in xyz)]
    lines += ['', 'Status catalogue checked '+STATUS_DATE,f'Source: {body.source_url}',
              f'Try /satellites {body.parent.lower()} or /{body.name.lower()} in orbit mode.']
    return '\n'.join(lines)
