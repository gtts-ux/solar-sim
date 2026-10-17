"""Shared physical camera scales for orbit maps and schematic mission geometry."""
from dataclasses import dataclass
import math

PRESETS = (('system','System / automatic',None),
           ('close','Close / 10 km',10.),
           ('earth','Earth / 15,000 km',15000.),
           ('high','High Earth orbit / 60,000 km',60000.),
           ('moon','Moon range / 480,000 km',480000.))


class Camera:
    def __init__(self):self.index=0
    @property
    def name(self):return PRESETS[self.index][0]
    @property
    def label(self):return PRESETS[self.index][1]
    @property
    def extent(self):return PRESETS[self.index][2]
    def cycle(self,direction):self.index=(self.index+direction)%len(PRESETS)
    def select(self,name):
        names=[p[0] for p in PRESETS]
        if name not in names:raise ValueError('Camera: system, close, earth, high or moon.')
        self.index=names.index(name)


@dataclass(frozen=True)
class Point:
    name: str
    x: float
    y: float
    color: int=7
    marker: str='o'
    radius: float=0


def render(width,height,camera,points,paths=(),focus=None):
    """A fixed kilometer scale; markers are enlarged, reference limbs are dotted."""
    width,height=max(12,width),max(6,height)
    cells=[[(' ',7,False) for _ in range(width)] for _ in range(height)]
    target=focus if camera.name=='close' and focus is not None else (0.,0.)
    extent=camera.extent or 480000.
    factor=max(1,min((width-12)/2,height-3))/extent
    cx,cy=(width-1)/2,(height-1)/2
    def xy(x,y):return cx+(x-target[0])*factor,cy-(y-target[1])*factor*.5
    def put(x,y,text,color=7,bold=False):
        x,y=round(x),round(y)
        if 0<=y<height:
            for offset,char in enumerate(text):
                if 0<=x+offset<width:cells[y][x+offset]=(char,color,bold)
    def segment(a,b):
        x0,y0=xy(*a);x1,y1=xy(*b)
        dx,dy=x1-x0,y1-y0
        lower,upper=0.,1.
        for p,q in ((-dx,x0),(dx,width-1-x0),(-dy,y0),(dy,height-1-y0)):
            if p==0:
                if q<0:return
            elif p<0:lower=max(lower,q/p)
            else:upper=min(upper,q/p)
            if lower>upper:return
        ax,ay=x0+lower*dx,y0+lower*dy
        bx,by=x0+upper*dx,y0+upper*dy
        steps=max(1,int(max(abs(bx-ax),abs(by-ay))))
        for i in range(steps+1):put(ax+(bx-ax)*i/steps,ay+(by-ay)*i/steps,'.',8)
    for path in paths:
        for a,b in zip(path,path[1:]):segment(a,b)
    for point in points:
        if point.radius and point.radius*factor>=2:
            for i in range(240):
                a=i*math.tau/240
                px,py=xy(point.x+point.radius*math.cos(a),point.y+point.radius*math.sin(a))
                put(px,py,'.',point.color)
    for point in points:
        px,py=xy(point.x,point.y)
        if 0<=round(px)<width and 0<=round(py)<height:
            put(px+2,py,point.name,point.color)
            put(px,py,point.marker,point.color,True)
    off=[p.name for p in points[:2] if not (0<=xy(p.x,p.y)[0]<width and 0<=xy(p.x,p.y)[1]<height)]
    if off:put(1,height-1,'Outside view: '+', '.join(off),8)
    put(1,0,camera.label,6,True)
    return cells


def mission_geometry(replay):
    """Kilometer-based illustration, not reconstructed spacecraft ephemerides."""
    moon_x=384400.
    visual=replay.stage.visual
    earth_radius=6371.
    orbit=earth_radius+(1408 if replay.flight.name=='Polaris Dawn' and visual=='high_orbit' else
                        585 if replay.flight.name=='Inspiration4' and visual=='high_orbit' else 400)
    moon_radius=1737.4
    lunar=moon_radius+110
    def point(t):
        a=-math.pi/2+t*math.tau*2
        if visual=='launch':return (400*t,earth_radius+400*t)
        if visual in ('earth_orbit','high_orbit','eva'):return (orbit*math.cos(a),orbit*math.sin(a))
        if visual=='tli':return (orbit+(30000-orbit)*t,3000*math.sin(math.pi*t))
        if visual in ('outbound','abort'):return (30000+(moon_x-lunar-30000)*t,55000*math.sin(math.pi*t))
        if visual in ('lunar_orbit','distant_orbit'):
            radius=70000 if visual=='distant_orbit' else lunar
            return (moon_x+radius*math.cos(a),radius*math.sin(a))
        if visual=='flyby':
            a=-math.pi/2+math.pi*t
            return (moon_x+8300*math.cos(a),8300*math.sin(a))
        if visual in ('descent','ascent'):
            radius=moon_radius+110*(1-t if visual=='descent' else t)
            return (moon_x+radius,0.)
        if visual=='surface':return (moon_x+moon_radius,0.)
        if visual=='tei':return (moon_x-lunar-(30000-lunar)*t,3000*math.sin(math.pi*t))
        if visual=='return':return (moon_x-30000-(moon_x-30000-orbit)*t,-45000*math.sin(math.pi*t))
        if visual in ('rendezvous','docked','undock'):
            a=.6-(1-t)*.4 if visual=='rendezvous' else .6
            r=orbit+(50*t if visual=='undock' else 0)
            return (r*math.cos(a),r*math.sin(a))
        if visual in ('deorbit','reentry'):return (orbit*(1-t)+earth_radius*t,0.)
        return (earth_radius,0.)
    points=[Point('Earth',0,0,4,'O',earth_radius)]
    if replay.flight.lunar:points.append(Point('Moon',moon_x,0,7,'o',moon_radius))
    if any(s.visual=='docked' for s in replay.flight.stages):
        points.append(Point('ISS',orbit*math.cos(.6),orbit*math.sin(.6),2,'+'))
    if visual=='surface':
        a=replay.stage_fraction*math.tau*2
        points.append(Point('Command module',moon_x+lunar*math.cos(a),lunar*math.sin(a),6,'c'))
    craft=point(replay.stage_fraction)
    points.append(Point('Spacecraft',*craft,3,'!' if visual=='abort' else '>'))
    paths=[[(orbit*math.cos(i*math.tau/180),orbit*math.sin(i*math.tau/180)) for i in range(180)],
           [point(i/240) for i in range(241)]]
    return points,paths,craft


def mission_scene(replay,width,height,camera):
    points,paths,focus=mission_geometry(replay)
    return render(width,height,camera,points,paths,focus)
