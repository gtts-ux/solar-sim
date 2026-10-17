"""Full-screen, time-based terminal animations and safe return to the simulator."""
import math
import random
import time
from themes import galaxy_palette
from screensaver_scenes import Earth, Saturn, BlackHole, scene_palette, BASIC, Planet, PLANET_STYLES

# Four eight-step ramps: blue arms, violet arms, amber bulge and white stars.
PALETTE = (17,18,24,25,32,39,75,117,
           17,53,54,55,61,99,141,189,
           52,94,130,172,214,221,229,230,
           235,238,242,245,250,253,255,231)
DOTS = ((1,8),(2,16),(4,32),(64,128))
FPS = 30


class Galaxy:
    """Stable particles rotate continuously; braille provides 2x4 dots per cell."""
    def __init__(self, seed=731):
        rng=random.Random(seed)
        self.particles=[]
        for i in range(4000):
            arm=i%4
            radius=.055+rng.random()**.8*1.10
            angle=arm*math.tau/4+math.log(radius)*3.6+rng.gauss(0,.11+.10*radius)
            radius+=rng.gauss(0,.012+.019*radius)
            x,y=radius*math.cos(angle),radius*math.sin(angle)
            self.particles.append((x,y,rng.gauss(0,.012),arm%2,.95+1.05*rng.random()))
        # A soft old-star bulge and elongated central bar, rather than a solid disc.
        for _ in range(1400):
            x,y=rng.gauss(0,.115),rng.gauss(0,.062)
            self.particles.append((x,y,rng.gauss(0,.026),2,1.2+rng.random()*1.25))
        for _ in range(700):
            radius=min(1.16,rng.expovariate(3.6))
            angle=rng.random()*math.tau
            self.particles.append((radius*math.cos(angle),radius*math.sin(angle),
                                   rng.gauss(0,.035),1,.39))
        self.stars=[(rng.random(),rng.random(),rng.random()*math.tau,rng.random()) for _ in range(260)]

    def frame(self,width,height,seconds,zoom=1):
        """Return rows of (glyph, palette index, bold), with no interface overlay."""
        if width<=0 or height<=0:
            return []
        count=width*height
        masks=[0]*count
        light=[0.0]*count
        warm=[0.0]*count
        violet=[0.0]*count
        angle=seconds*.065
        ca,sa=math.cos(angle),math.sin(angle)
        tilt=.53+.035*math.sin(seconds*.09)
        sky=-.27+.025*math.sin(seconds*.06)
        cs,ss=math.cos(sky),math.sin(sky)
        scale=min(width*.80,height*4*.86)*zoom
        cx,cy=width,height*2
        xx=(ca*cs-sa*tilt*ss)*scale
        xy=(-sa*cs-ca*tilt*ss)*scale
        xz=-ss*scale
        yx=(ca*ss+sa*tilt*cs)*scale
        yy=(-sa*ss+ca*tilt*cs)*scale
        yz=cs*scale
        pixel_width,pixel_height=width*2,height*4
        for x,y,z,family,power in self.particles:
            px=int(cx+x*xx+y*xy+z*xz)
            py=int(cy+x*yx+y*yy+z*yz)
            if 0<=px<pixel_width and 0<=py<pixel_height:
                index=(py//4)*width+px//2
                masks[index]|=DOTS[py%4][px%2]
                light[index]+=power
                if family==2:
                    warm[index]+=power
                elif family==1:
                    violet[index]+=power
        cells=[[(' ',24,False) for _ in range(width)] for _ in range(height)]
        for index,mask in enumerate(masks):
            if not mask:
                continue
            energy=light[index]
            level=min(7,int(math.log1p(energy)*2.6))
            family=2 if warm[index]>energy*.4 else 1 if violet[index]>energy*.52 else 0
            # Densely packed central stars become ivory; outer arms stay cool.
            if energy>22 and family==2:
                family,level=3,min(7,level)
            cells[index//width][index%width]=(chr(0x2800+mask),family*8+level,level>=6)
        # Faint foreground stars remain fixed as the galaxy rotates behind them.
        for sx,sy,phase,strength in self.stars[:min(260,max(8,count//58))]:
            x,y=min(width-1,int(sx*width)),min(height-1,int(sy*height))
            if light[y*width+x]>.65:
                continue
            brightness=.5+.5*math.sin(seconds*.65+phase)
            level=2+int(brightness*2+strength*2)
            glyph='+' if strength>.97 else '*' if strength>.88 else '·'
            cells[y][x]=(glyph,24+level,level>=6)
        return cells

    def runs(self,width,height,seconds,zoom=1):
        """Group equal-color neighboring cells to keep terminal output small."""
        for y,row in enumerate(self.frame(width,height,seconds,zoom)):
            x=0
            while x<len(row):
                glyph,color,bold=row[x]
                if glyph==' ':
                    x+=1
                    continue
                start=x
                chars=[glyph]
                x+=1
                while x<len(row) and row[x][0]!=' ' and row[x][1:]==(color,bold):
                    chars.append(row[x][0])
                    x+=1
                yield y,start,''.join(chars),color,bold


def animation(name):
    if name in PLANET_STYLES:return Planet(name)
    if name=='earth':return Earth()
    if name=='saturn':return Saturn()
    if name=='black-hole':return BlackHole()
    return Galaxy()


def show_screensaver(screen,sim,colors=False):
    """Temporarily own the display and preserve the caller's complete UI state."""
    import curses
    previous_background=screen.getbkgd()
    sim.tick()
    paused=sim.paused
    sim.paused=True
    try:
        name=getattr(getattr(sim,'settings',None),'screensaver','milky-way')
        scene=animation(name)
        theme=getattr(getattr(sim,'settings',None),'theme','cosmic')
        scene.monochrome=not colors or theme=='mono'
        palette=scene_palette(name,theme) if name in BASIC else galaxy_palette(theme)
        basic=BASIC.get(name,(4,5,3,7))
        extended=colors and curses.COLORS>=256 and curses.COLOR_PAIRS>len(PALETTE)+9
        if extended:
            for index,color in enumerate(palette):
                curses.init_pair(9+index,color,curses.COLOR_BLACK)
        started=time.monotonic()
        deadline=started
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        screen.leaveok(True)
        if extended:
            screen.bkgd(' ',curses.color_pair(9))
        screen.clear()
        while sim.running:
            now=time.monotonic()
            if now>=deadline:
                height,width=screen.getmaxyx()
                screen.erase()
                zoom=(1,.70,.90,1.12,1.35)[getattr(getattr(sim,'camera',None),'index',0)]
                for y,x,text,color,bold in scene.runs(max(0,width-1),height,now-started,zoom=zoom):
                    style=0
                    if colors:
                        style=curses.color_pair(9+color if extended else basic[color//8])
                    if bold:
                        style|=curses.A_BOLD
                    elif color%8<3:
                        style|=curses.A_DIM
                    try:
                        screen.addstr(y,x,text,style)
                    except curses.error:
                        pass
                screen.noutrefresh()
                curses.doupdate()
                deadline=max(deadline+1/FPS,time.monotonic())
            screen.timeout(max(1,math.ceil((deadline-time.monotonic())*1000)))
            try:
                key=screen.get_wch()
            except curses.error:
                continue
            if key in ('\n','\r',curses.KEY_ENTER,'\x1b'):
                break
            if key in (getattr(curses,'KEY_LEFT',-10),getattr(curses,'KEY_RIGHT',-11)) and hasattr(sim,'camera'):
                sim.camera.cycle(-1 if key==getattr(curses,'KEY_LEFT',-10) else 1)
            if key in ('\x03','\x04'):
                sim.running=False
    finally:
        sim.paused=paused
        sim.last_tick=time.monotonic()
        screen.bkgd(previous_background)
        screen.leaveok(False)
        screen.timeout(60)
        screen.clear()
        try:
            curses.curs_set(1)
        except curses.error:
            pass
