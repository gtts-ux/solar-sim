"""Historical flight replays: timed milestones and schematic trajectories, not flight ephemerides."""
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re


def utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Stage:
    date: datetime
    name: str
    visual: str
    note: str


@dataclass(frozen=True)
class Flight:
    name: str
    vehicle: str
    operator: str
    summary: str
    stages: tuple
    sources: tuple
    aliases: tuple = ()

    @property
    def start(self):
        return self.stages[0].date

    @property
    def end(self):
        return self.stages[-1].date

    @property
    def lunar(self):
        return any(s.visual in ('outbound','lunar_orbit','descent','surface','ascent','flyby','return','distant_orbit') for s in self.stages)


def flight(name,vehicle,operator,summary,stages,sources,aliases=()):
    return Flight(name,vehicle,operator,summary,tuple(Stage(utc(date),label,visual,note)
                  for date,label,visual,note in stages),tuple(sources),tuple(aliases))


FLIGHTS = [
    flight('Apollo 11','Saturn V / Columbia / Eagle','NASA','First crewed lunar landing and safe return.',[
        ('1969-07-16T13:32','Launch','launch','Saturn V lifts off from Kennedy Space Center.'),
        ('1969-07-16T13:44','Earth parking orbit','earth_orbit','Spacecraft checks before leaving Earth orbit.'),
        ('1969-07-16T16:22','Translunar injection','tli','S-IVB sends the spacecraft toward the Moon.'),
        ('1969-07-16T16:45','Lunar transfer coast','outbound','Columbia and Eagle cruise toward the Moon.'),
        ('1969-07-19T17:21','Lunar orbit','lunar_orbit','Enter lunar orbit; prepare Eagle for descent.'),
        ('1969-07-20T17:44','Lunar descent','descent','Eagle separates; Columbia remains in lunar orbit.'),
        ('1969-07-20T20:17','Moon landing','surface','Eagle touches down in the Sea of Tranquility.'),
        ('1969-07-21T02:56','Surface EVA','surface','Armstrong and Aldrin explore; Collins orbits in Columbia.'),
        ('1969-07-21T17:54','Lunar ascent','ascent','Eagle lifts off, leaving its descent stage behind.'),
        ('1969-07-21T21:35','Lunar rendezvous','lunar_orbit','The crew reunites aboard Columbia.'),
        ('1969-07-22T04:55','Trans-Earth injection','tei','The command/service module departs lunar orbit.'),
        ('1969-07-22T05:20','Return to Earth','return','Homeward coast and course corrections.'),
        ('1969-07-24T16:35','Re-entry and parachutes','reentry','Command module descends through the atmosphere.'),
        ('1969-07-24T16:50','Splashdown / mission complete','splash','Pacific Ocean recovery; all three astronauts return safely.')
    ],['https://www.nasa.gov/mission/apollo-11/','https://history.nasa.gov/afj/ap11fj/']),
    flight('Apollo 8','Saturn V / Apollo command-service module','NASA','First crewed lunar orbit; no landing.',[
        ('1968-12-21T12:51','Launch','launch','First crewed Saturn V launch.'),
        ('1968-12-21T13:03','Earth parking orbit','earth_orbit','Prepare the spacecraft for the translunar burn.'),
        ('1968-12-21T15:41','Translunar injection','tli','Leave Earth orbit.'),
        ('1968-12-21T16:00','Lunar transfer coast','outbound','Borman, Lovell and Anders head to the Moon.'),
        ('1968-12-24T09:59','Lunar orbit','lunar_orbit','Ten lunar orbits, observations and the Earthrise photographs.'),
        ('1968-12-25T06:10','Trans-Earth injection','tei','Depart the Moon after the Christmas Eve broadcast.'),
        ('1968-12-25T06:30','Return coast','return','Navigate back toward Earth.'),
        ('1968-12-27T15:37','Re-entry','reentry','Atmospheric entry and parachutes.'),
        ('1968-12-27T15:51','Splashdown / mission complete','splash','Pacific Ocean recovery; no lunar landing was attempted.')
    ],['https://www.nasa.gov/mission/apollo-8/']),
    flight('Apollo 13','Saturn V / Odyssey / Aquarius','NASA','Aborted landing; lunar flyby and emergency return.',[
        ('1970-04-11T19:13','Launch','launch','Apollo 13 launches toward its planned lunar landing.'),
        ('1970-04-11T19:25','Earth parking orbit','earth_orbit','Spacecraft checkout in Earth orbit.'),
        ('1970-04-11T22:18','Translunar injection','tli','Departure for the Moon.'),
        ('1970-04-11T22:40','Outbound coast','outbound','Cruise toward the Moon.'),
        ('1970-04-14T03:07','Oxygen-tank accident / abort','abort','Landing cancelled; Aquarius becomes the crew lifeboat.'),
        ('1970-04-14T05:00','Emergency lunar approach','outbound','Power conservation and trajectory recovery (schematic cue).'),
        ('1970-04-15T00:21','Lunar flyby / free return','flyby','Pass behind the Moon without entering lunar orbit.'),
        ('1970-04-15T02:40','Return-trajectory burn','tei','Aquarius propulsion shortens the trip home.'),
        ('1970-04-15T03:00','Emergency return coast','return','The crew prepares Odyssey for re-entry.'),
        ('1970-04-17T17:53','Re-entry','reentry','Odyssey returns through the atmosphere.'),
        ('1970-04-17T18:07','Splashdown / mission complete','splash','All three astronauts survive; no landing or lunar orbit occurred.')
    ],['https://www.nasa.gov/mission/apollo-13/','https://www.nasa.gov/history/detailed-chronology-of-events-surrounding-the-apollo-13-accident/']),
    flight('Apollo 17','Saturn V / America / Challenger','NASA','Final Apollo lunar landing; three surface EVAs.',[
        ('1972-12-07T05:33','Launch','launch','Night launch from Kennedy Space Center.'),
        ('1972-12-07T05:45','Earth parking orbit','earth_orbit','Checkout before translunar injection.'),
        ('1972-12-07T08:45','Translunar injection','tli','America and Challenger depart Earth orbit.'),
        ('1972-12-07T09:05','Lunar transfer coast','outbound','Cruise and navigation toward the Moon.'),
        ('1972-12-10T19:47','Lunar orbit','lunar_orbit','Prepare to explore Taurus-Littrow.'),
        ('1972-12-11T17:20','Lunar descent','descent','Cernan and Schmitt descend in Challenger.'),
        ('1972-12-11T19:54','Moon landing / surface exploration','surface','Three EVAs with the lunar rover; Evans remains in lunar orbit.'),
        ('1972-12-14T22:54','Lunar ascent','ascent','Challenger lifts off from Taurus-Littrow.'),
        ('1972-12-15T01:10','Lunar rendezvous','lunar_orbit','Transfer the crew and samples to America.'),
        ('1972-12-16T23:35','Trans-Earth injection','tei','Leave lunar orbit.'),
        ('1972-12-16T23:55','Return coast','return','The final Apollo lunar crew heads home.'),
        ('1972-12-19T19:10','Re-entry','reentry','Atmospheric entry, parachutes and recovery preparations.'),
        ('1972-12-19T19:24','Splashdown / mission complete','splash','The Apollo lunar-landing program ends with a successful return.')
    ],['https://www.nasa.gov/mission/apollo-17/']),
    flight('Artemis I','SLS / Orion','NASA / ESA','Uncrewed Orion test including distant retrograde lunar orbit.',[
        ('2022-11-16T06:47','Launch','launch','First SLS launch; Orion carries no astronauts.'),
        ('2022-11-16T07:00','Earth orbit and checkout','earth_orbit','Check the spacecraft and upper stage.'),
        ('2022-11-16T08:14','Translunar injection','tli','Orion departs for the Moon.'),
        ('2022-11-16T09:00','Outbound coast','outbound','Transit to lunar vicinity (rounded visualization cue).'),
        ('2022-11-21T12:44','Outbound lunar flyby','flyby','Powered flyby redirects Orion toward its distant orbit.'),
        ('2022-11-25T21:52','Distant retrograde orbit','distant_orbit','Orion tests navigation and systems in a distant lunar orbit.'),
        ('2022-12-01T21:53','Distant-orbit departure','lunar_orbit','Exit the distant orbit and approach the Moon again.'),
        ('2022-12-05T16:43','Return powered flyby','flyby','Final lunar flyby sets up the return to Earth.'),
        ('2022-12-05T18:00','Return coast','return','Orion heads for Earth; no Moon landing.'),
        ('2022-12-11T17:20','Re-entry','reentry','Test the heat shield at lunar-return speed.'),
        ('2022-12-11T17:40','Splashdown / mission complete','splash','Orion is recovered in the Pacific Ocean.')
    ],['https://www.nasa.gov/mission/artemis-i/'],['Artemis 1']),
    flight('Artemis II','SLS / Orion Integrity','NASA / ESA / CSA','Crewed lunar flyby flown in April 2026; no lunar orbit or landing.',[
        ('2026-04-01T22:35','Launch','launch','Four astronauts depart Kennedy aboard Orion.'),
        ('2026-04-01T22:47','Earth orbit and crew checkout','earth_orbit','Earth-orbit systems tests before committing to the Moon.'),
        ('2026-04-02T23:49','Translunar injection','tli','Orion begins its crewed journey toward the Moon.'),
        ('2026-04-03T00:10','Outbound lunar coast','outbound','The crew approaches the Moon on a free-return trajectory.'),
        ('2026-04-06T20:00','Lunar approach','outbound','Lunar observations and flyby preparation (rounded cue).'),
        ('2026-04-06T23:00','Lunar flyby / free return','flyby','Closest approach about 4,067 miles above the lunar surface; no capture or landing.'),
        ('2026-04-07T00:00','Return coast','return','Orion heads back to Earth (rounded transition cue).'),
        ('2026-04-10T23:53','Re-entry and parachutes','reentry','Orion returns through the atmosphere.'),
        ('2026-04-11T00:07','Splashdown / mission complete','splash','Pacific splashdown on April 10 local time, April 11 UTC.')
    ],['https://www.nasa.gov/mission/artemis-ii/',
       'https://www.nasa.gov/blogs/missions/2026/04/06/artemis-ii-flight-day-6-crew-wraps-historic-lunar-flyby/'],['Artemis 2']),
    flight('SpaceX Demo-2','Falcon 9 / Crew Dragon Endeavour','NASA / SpaceX','Crew Dragon crewed test flight to the ISS and back.',[
        ('2020-05-30T19:22','Launch','launch','Behnken and Hurley launch on Falcon 9.'),
        ('2020-05-30T19:35','Earth orbit','earth_orbit','Dragon separates and performs orbital checks.'),
        ('2020-05-31T12:00','ISS rendezvous','rendezvous','Dragon approaches the station (rounded approach cue).'),
        ('2020-05-31T14:16','Docked at ISS','docked','Crew joins station operations and orbital research.'),
        ('2020-08-01T23:35','Undocking and departure','undock','Dragon departs the ISS for its return.'),
        ('2020-08-02T17:56','Deorbit burn','deorbit','Reduce orbital energy for atmospheric entry.'),
        ('2020-08-02T18:36','Re-entry and parachutes','reentry','Dragon descends toward the Gulf of Mexico.'),
        ('2020-08-02T18:48','Splashdown / mission complete','splash','The first crewed Dragon test flight is complete.')
    ],['https://www.nasa.gov/nasas-spacex-demo-2-resources-archive/','https://www.spacex.com/launches/demo2'],['Demo-2','Demo 2','SpaceX Demo 2']),
    flight('SpaceX Crew-1','Falcon 9 / Crew Dragon Resilience','NASA / SpaceX / JAXA','First operational Crew Dragon rotation mission to ISS.',[
        ('2020-11-16T00:27','Launch','launch','Four crew launch on Resilience; November 15 local time.'),
        ('2020-11-16T00:40','Earth orbit','earth_orbit','Dragon checks its systems and begins phasing maneuvers.'),
        ('2020-11-17T02:00','ISS rendezvous','rendezvous','Approach the station (rounded approach cue).'),
        ('2020-11-17T04:01','Docked at ISS','docked','A long-duration station expedition begins.'),
        ('2021-05-02T00:35','Undocking and departure','undock','Resilience departs the station.'),
        ('2021-05-02T06:03','Deorbit sequence','deorbit','Return preparations and braking (rounded cue).'),
        ('2021-05-02T06:39','Re-entry and parachutes','reentry','Nighttime atmospheric return.'),
        ('2021-05-02T06:56','Splashdown / mission complete','splash','Night splashdown off Florida concludes Crew-1.')
    ],['https://www.nasa.gov/news-release/crew-1-astronauts-safely-splash-down-after-space-station-mission/'],['Crew-1','Crew 1','SpaceX Crew 1']),
    flight('Inspiration4','Falcon 9 / Crew Dragon Resilience','SpaceX / Inspiration4','Private orbital mission; no ISS docking.',[
        ('2021-09-16T00:02','Launch','launch','Four private astronauts launch aboard Resilience.'),
        ('2021-09-16T00:15','Earth orbit','earth_orbit','Dragon separates and begins its orbital mission.'),
        ('2021-09-16T03:00','Higher orbit','high_orbit','Raise the orbit toward roughly 585 km (rounded cue).'),
        ('2021-09-16T06:00','Orbital research and cupola views','earth_orbit','Crew research and observations; no station visit.'),
        ('2021-09-18T22:00','Deorbit sequence','deorbit','Prepare for return and brake from orbit (rounded cue).'),
        ('2021-09-18T22:55','Re-entry and parachutes','reentry','Resilience returns through the atmosphere (rounded cue).'),
        ('2021-09-18T23:06','Splashdown / mission complete','splash','Atlantic Ocean recovery ends the three-day mission.')
    ],['https://inspiration4.com/','https://www.spacex.com/launches/inspiration4'],['Inspiration 4','SpaceX Inspiration4']),
    flight('Polaris Dawn','Falcon 9 / Crew Dragon Resilience','SpaceX / Polaris Program','High Earth orbit, commercial spacewalk and safe return.',[
        ('2024-09-10T09:23','Launch','launch','Four astronauts launch on Polaris Dawn.'),
        ('2024-09-10T09:36','Earth orbit','earth_orbit','Dragon separates from Falcon 9.'),
        ('2024-09-10T16:00','High Earth orbit','high_orbit','Reach an apogee of 1,408 km during flight day one (rounded cue).'),
        ('2024-09-11T16:00','Lower orbit for EVA','earth_orbit','Prepare for spacewalk operations (rounded transition cue).'),
        ('2024-09-12T10:12','Commercial spacewalk operations','eva','Depressurization and suited EVA operations from Dragon.'),
        ('2024-09-12T12:00','Orbital research','earth_orbit','Experiments and optical communications tests (rounded cue).'),
        ('2024-09-15T06:00','Deorbit sequence','deorbit','Prepare for return (rounded cue).'),
        ('2024-09-15T07:20','Re-entry and parachutes','reentry','Final atmospheric descent (rounded cue).'),
        ('2024-09-15T07:37','Splashdown / mission complete','splash','Return off Dry Tortugas, Florida; time rounded to the minute.')
    ],['https://www.spacex.com/launches/polarisdawn',
       'https://polarisprogram.com/polaris-dawn-crew-returns-to-earth-achieving-major-objectives-during-their-five-day-mission/'],['SpaceX Polaris Dawn']),
]


def normalize(name):
    return re.sub(r'[^a-z0-9]','',name.lower())


def find_flight(name):
    for item in FLIGHTS:
        if normalize(name) in [normalize(n) for n in (item.name,*item.aliases)]:
            return item
    raise ValueError(f'Unknown flight: {name}. Use /mission list.')


def parse_duration(text):
    units={'s':1,'sec':1,'secs':1,'second':1,'seconds':1,
           'm':60,'min':60,'mins':60,'minute':60,'minutes':60,
           'h':3600,'hr':3600,'hrs':3600,'hour':3600,'hours':3600}
    matches=list(re.finditer(r'(\d+(?:\.\d+)?)\s*([a-z]+)',text.lower()))
    residue=re.sub(r'(\d+(?:\.\d+)?)\s*([a-z]+)','',text.lower()).strip()
    if not matches or residue:
        raise ValueError('Duration examples: 30 seconds, 1 minute, 1m 30s.')
    total=0.0
    for match in matches:
        value,unit=match.groups()
        if unit not in units:
            raise ValueError('Use seconds, minutes or hours for playback duration.')
        total += float(value)*units[unit]
    if not math.isfinite(total) or not 1<=total<=86400:
        raise ValueError('Playback duration must be between 1 second and 24 hours.')
    return total


def parse_request(args):
    # shlex handles optional quotes; searching split points supports unquoted names.
    for index in range(1,len(args)):
        try:
            item=find_flight(' '.join(args[:index]))
        except ValueError:
            continue
        return item,parse_duration(' '.join(args[index:]))
    return find_flight(' '.join(args)),60.0


def catalogue():
    lines=['FLIGHT REPLAYS / 10 historical missions','']
    lines += [f'  {f.name:<17} {f.start:%Y-%m-%d}  {f.summary}' for f in FLIGHTS]
    return '\n'.join(lines)+('\n\n/mission Apollo 11 1 minute\n/mission "Artemis II" 30 seconds\n'
        '/mission "SpaceX Demo-2" 1m 30s\n/mission info Apollo 11\n\n'
        'Playback follows historical stages; routes are schematic. Intermediate cues are rounded/approximate.')


def flight_info(item):
    lines=[item.name.upper()+' / historical flight',item.summary,'',
           'Vehicle: '+item.vehicle,'Operator: '+item.operator,
           f'Launch: {item.start:%Y-%m-%d %H:%M} UTC',f'Return: {item.end:%Y-%m-%d %H:%M} UTC','',
           'CHRONOLOGY / UTC, rounded milestones and approximate intermediate cues']
    lines += [f'  {s.date:%Y-%m-%d %H:%M}  {s.name}\n    {s.note}' for s in item.stages]
    lines += ['','SOURCES',*item.sources,'',f'/mission "{item.name}" 1 minute']
    return '\n'.join(lines)


class Playback:
    def __init__(self,flight,duration):
        self.flight=flight
        self.duration=duration
        self.elapsed=0.0
        intervals=[(b.date-a.date).total_seconds() for a,b in zip(flight.stages,flight.stages[1:])]
        if not intervals or any(v<=0 for v in intervals):
            raise ValueError('Flight milestones must increase in time.')
        # Guarantee visible time for launch/landing, without letting a long ISS stay hide every other phase.
        floor=min(.035,.45/len(intervals))
        weights=[math.sqrt(v) for v in intervals]
        total=sum(weights)
        self.boundaries=[0.0]
        for weight in weights:
            self.boundaries.append(self.boundaries[-1]+duration*(floor+(1-floor*len(intervals))*weight/total))
        self.boundaries[-1]=duration

    @property
    def complete(self):
        return self.elapsed>=self.duration

    @property
    def index(self):
        return min(len(self.flight.stages)-1,max(0,bisect_right(self.boundaries,self.elapsed)-1))

    @property
    def stage(self):
        return self.flight.stages[self.index]

    @property
    def stage_fraction(self):
        i=self.index
        if self.complete:
            return 1.0
        return (self.elapsed-self.boundaries[i])/(self.boundaries[i+1]-self.boundaries[i])

    @property
    def date(self):
        if self.complete:
            return self.flight.end
        a,b=self.flight.stages[self.index:self.index+2]
        return a.date+(b.date-a.date)*self.stage_fraction

    def advance(self,seconds):
        self.elapsed=min(self.duration,max(0,self.elapsed+seconds))

    def seek(self,percent):
        if not math.isfinite(percent) or not 0<=percent<=100:
            raise ValueError('Seek percentage must be from 0 to 100.')
        self.elapsed=self.duration*percent/100

    def status(self,paused=False):
        state='COMPLETE' if self.complete else 'PAUSED' if paused else 'PLAYING'
        return (f'{self.flight.name.upper()} / {state}\n\n'
                f'Historical UTC: {self.date:%Y-%m-%d %H:%M:%S}\n'
                f'Playback: {self.elapsed:.1f} / {self.duration:g} seconds\n'
                f'Stage {self.index+1}/{len(self.flight.stages)}: {self.stage.name}\n{self.stage.note}\n\n'
                'Schematic route; intermediate timing cues are approximate. Time compression varies by stage.\n'
                '/pause /resume /mission seek 50 /mission restart /mission stop')

    def scene(self,width,height,camera=None):
        if camera is not None:
            from camera import mission_scene
            return mission_scene(self,width,height,camera)
        width,height=max(24,width),max(6,height)
        cells=[[(' ',7,False) for _ in range(width)] for _ in range(height)]
        ex,ey=(width*.2 if self.flight.lunar else width*.47),height*.55
        mx,my=width*.78,height*.45
        rx=min(width*.12,height*.85)
        ry=rx*.36
        mr=max(2,min(rx*.45,height*.6))
        visual=self.stage.visual

        def put(x,y,text,color=7,bold=False):
            x,y=round(x),round(y)
            if 0<=y<height:
                for k,char in enumerate(text):
                    if 0<=x+k<width:
                        cells[y][x+k]=(char,color,bold)

        def point(t):
            angle=-math.pi/2+t*math.tau*2
            if visual=='launch':
                return ex+rx*t*.3,ey-ry*t
            if visual in ('earth_orbit','high_orbit','eva'):
                factor=1.35 if visual=='high_orbit' else 1
                return ex+rx*factor*math.cos(angle),ey+ry*factor*math.sin(angle)
            if visual=='tli':
                return ex+rx*t,ey-ry*(1-t)
            if visual in ('outbound','abort'):
                return ex+rx+(mx-mr-ex-rx)*t,ey+(my-ey)*t-math.sin(math.pi*t)*height*.2
            if visual in ('lunar_orbit','distant_orbit'):
                factor=1.6 if visual=='distant_orbit' else 1
                return mx+mr*factor*math.cos(angle),my+mr*.4*factor*math.sin(angle)
            if visual=='flyby':
                a=-math.pi/2+math.pi*t
                return mx+mr*math.cos(a),my+mr*.55*math.sin(a)
            if visual=='descent':
                return mx+mr*(1-t),my+mr*.4*(1-t)
            if visual=='surface':
                return mx,my+1
            if visual=='ascent':
                return mx+mr*t,my-mr*.4*t
            if visual=='tei':
                return mx-mr*t,my+mr*.4*(1-t)
            if visual=='return':
                return mx-mr+(ex+rx-mx+mr)*t,my+(ey-my)*t+math.sin(math.pi*t)*height*.18
            if visual in ('rendezvous','docked','undock'):
                target=(ex+rx*.75,ey-ry*.65)
                if visual=='docked':
                    return target
                if visual=='rendezvous':
                    a=-math.pi+math.pi*.75*t
                    return ex+rx*math.cos(a),ey+ry*math.sin(a)
                return target[0]+rx*.4*t,target[1]+ry*.7*t
            if visual in ('deorbit','reentry'):
                return ex+rx*(1-t),ey-ry*math.sin(math.pi*t)
            return ex,ey+1

        for n in range(120):
            a=n/120*math.tau
            put(ex+rx*math.cos(a),ey+ry*math.sin(a),'.',8)
            if self.flight.lunar:
                put(mx+mr*math.cos(a),my+mr*.4*math.sin(a),'.',8)
        for n in range(100):
            x,y=point(n/99)
            put(x,y,'.',6)
        put(ex,ey,'O',4,True)
        put(ex-2,ey+2,'Earth',4,True)
        if self.flight.lunar:
            put(mx,my,'o',7,True)
            put(mx-2,my+2,'Moon',7,True)
        if any(s.visual=='docked' for s in self.flight.stages):
            put(ex+rx*.75,ey-ry*.65,'+',2,True)
            put(ex+rx*.75+2,ey-ry*.65,'ISS',2,True)
        x,y=point(self.stage_fraction)
        put(x,y,'!' if visual=='abort' else '>',3,True)
        if visual=='surface':
            put(mx+2,my+1,'LM',3,True)
            # Command module stays in orbit while the lander visits the surface.
            a=self.stage_fraction*math.tau*2
            put(mx+mr*math.cos(a),my+mr*.4*math.sin(a),'c',6,True)
        elif visual=='eva':
            put(x+2,y,'EVA',3,True)
        return cells
