"""Procedural braille Earth, Saturn and black-hole animations; no assets or packages.

The geography is stylized, and the black hole is an artistic lensing illustration.
Geometry is cached per viewport; animation uses elapsed time, never random frames.
"""
import math
import random

DOTS = ((1,8),(2,16),(4,32),(64,128))
# A 4x4 ordered dither spans two braille cells, preserving detail without color.
_BAYER=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
DITHER=tuple({DOTS[y][x]:(_BAYER[y][x+parity*2]+.5)/16
              for y in range(4) for x in range(2)} for parity in range(2))
GAS_MASKS=tuple(tuple(sum(bit for bit,threshold in row.items() if threshold<level/16)
                      for level in range(17)) for row in DITHER)
GRAY = (235,238,242,245,250,253,255,231)
PALETTES = {
    'earth': ((17,18,24,25,31,32,39,75), (22,28,29,35,71,77,114,157),
              (237,240,244,248,251,253,255,231), (17,24,31,38,45,81,159,231)),
    'saturn': ((58,94,136,137,179,180,222,230), (58,94,100,101,137,179,186,223),
               (235,237,239,243,246,250,223,230), GRAY),
    'black-hole': ((52,88,94,130,166,172,208,214), (52,94,130,172,214,220,229,230),
                   (17,18,54,55,61,99,141,183), (52,94,178,214,221,229,230,231)),
}
BASIC = {'earth':(4,2,7,6),'saturn':(3,3,7,7),'black-hole':(1,3,5,7)}


def scene_palette(name,theme):
    ramps=PALETTES[name]
    if theme=='mono':return GRAY*4
    # Preserve each object's recognizable colors; the sky follows the UI theme.
    if theme!='cosmic' and name!='black-hole':
        from themes import galaxy_palette
        sky=galaxy_palette(theme)
        ramps=(*ramps[:3],tuple(sky[8:12])+tuple(sky[-4:]))
    return tuple(color for ramp in ramps for color in ramp)


class Raster:
    def __init__(self,width,height,monochrome=False):
        self.width,self.height=width,height
        self.monochrome=monochrome
        count=width*height
        self.masks=[0]*count
        self.power=[0.]*count
        self.samples=[0]*count
        self.families=[[0.]*count for _ in range(4)]

    def dot(self,index,bit,family,light):
        if light<.045:return
        if self.monochrome and light*(.58,.9,1.15,.75)[family]<DITHER[(index%self.width)&1][bit]:
            return
        self.masks[index]|=bit
        self.power[index]+=light
        self.samples[index]+=1
        self.families[family][index]+=light

    def cells(self):
        cells=[[(' ',24,False) for _ in range(self.width)] for _ in range(self.height)]
        f0,f1,f2,f3=self.families
        for index,mask in enumerate(self.masks):
            if not mask:continue
            family,energy=0,f0[index]
            if f1[index]>energy:family,energy=1,f1[index]
            if f2[index]>energy:family,energy=2,f2[index]
            if f3[index]>energy:family=3
            value=self.power[index]/self.samples[index]
            level=int(value*7.8)
            if level>7:level=7
            cells[index//self.width][index%self.width]=(chr(0x2800+mask),family*8+level,level>=6)
        return cells


class Scene:
    def __init__(self):
        self._geometry_key=None
        rng=random.Random(904)
        self.stars=[(rng.random(),rng.random(),rng.random()*math.tau,rng.random()) for _ in range(200)]

    def geometry(self,width,height,zoom):
        key=(width,height,zoom)
        if key!=self._geometry_key:
            self.samples=self.build_geometry(width,height,zoom)
            self._geometry_key=key
        return self.samples

    def finish(self,raster,seconds,cells=None):
        if cells is None:cells=raster.cells()
        for sx,sy,phase,strength in self.stars[:max(4,min(200,raster.width*raster.height//55))]:
            x=min(raster.width-1,int(sx*raster.width));y=min(raster.height-1,int(sy*raster.height))
            if self.sky_visible(x,y,raster.width,raster.height) and cells[y][x][0]==' ':
                level=2+int((.5+.5*math.sin(seconds*.45+phase))*2+strength*2)
                glyph='+' if strength>.97 else '*' if strength>.90 else '·'
                cells[y][x]=(glyph,24+level,False)
        return cells

    def sky_visible(self,x,y,width,height):
        return (x*2+1-width)**2+(y*4+2-height*2)**2>self.radius*self.radius*1.03

    def runs(self,width,height,seconds,zoom=1):
        for y,row in enumerate(self.frame(width,height,seconds,zoom)):
            x=0
            while x<len(row):
                glyph,color,bold=row[x]
                if glyph==' ':x+=1;continue
                start=x;chars=[glyph];x+=1
                while x<len(row) and row[x][0]!=' ' and row[x][1:]==(color,bold):
                    chars.append(row[x][0]);x+=1
                yield y,start,''.join(chars),color,bold

    @staticmethod
    def pixels(width,height,radius,bound):
        cx,cy=width,height*2
        for py in range(max(0,int(cy-radius*bound)),min(height*4,math.ceil(cy+radius*bound))):
            y=(cy-py-.5)/radius
            for px in range(max(0,int(cx-radius*bound)),min(width*2,math.ceil(cx+radius*bound))):
                x=(px+.5-cx)/radius
                yield (py//4)*width+px//2,DOTS[py%4][px%2],x,y


# Hand-drawn low-resolution coastline outlines (longitude, latitude in degrees).
# No downloaded maps: the texture is rasterized once and rotated on a shaded sphere.
COASTS = (
    ((-168,70),(-145,71),(-129,70),(-120,74),(-97,81),(-75,78),(-61,66),(-52,52),
     (-63,48),(-59,44),(-70,43),(-76,35),(-81,25),(-83,29),(-89,29),(-97,22),
     (-88,16),(-83,9),(-79,9),(-86,15),(-101,18),(-110,30),(-117,33),(-124,43),
     (-130,54),(-141,60),(-154,58),(-166,62)),
    ((-81,12),(-70,10),(-60,7),(-51,3),(-35,-5),(-37,-13),(-42,-23),(-49,-29),
     (-54,-38),(-66,-55),(-73,-50),(-75,-36),(-71,-18),(-80,-5)),
    ((-53,60),(-43,60),(-21,70),(-18,79),(-36,84),(-57,82),(-65,71)),
    ((-17,35),(0,37),(11,34),(25,32),(34,31),(35,23),(44,12),(51,11),(43,0),
     (40,-11),(35,-23),(28,-34),(18,-35),(12,-19),(9,-2),(1,5),(-10,5),(-16,15)),
    ((-10,36),(-10,44),(-1,44),(2,51),(9,55),(5,59),(12,71),(28,71),(33,64),
     (44,68),(61,70),(80,75),(111,73),(140,70),(175,65),(179,52),(157,53),
     (144,45),(135,35),(122,31),(121,23),(109,20),(106,10),(100,5),(96,17),
     (88,22),(80,8),(74,15),(68,24),(59,25),(56,17),(44,12),(37,24),(36,35),
     (29,40),(23,35),(19,41),(13,38),(10,44),(3,42)),
    ((112,-11),(130,-12),(137,-11),(142,-10),(146,-18),(153,-26),(151,-35),
     (139,-39),(130,-33),(116,-35),(113,-24)),
    ((-8,50),(1,51),(-3,59),(-7,58)), ((-24,63),(-13,64),(-14,67),(-23,66)),
    ((130,31),(136,34),(142,40),(144,45),(140,41),(135,35)),
    ((47,-13),(51,-16),(48,-25),(44,-25),(44,-18)),
    ((95,5),(105,-6),(113,-7),(118,-4),(115,6),(108,7),(103,2)),
    ((130,-3),(141,-2),(151,-6),(145,-10),(136,-8)),
    ((166,-34),(178,-38),(172,-43),(166,-47),(168,-40)),
)


class Earth(Scene):
    TW,TH=512,256
    def __init__(self):
        super().__init__()
        self.land=bytearray(self.TW*self.TH)
        # Scanline fill avoids testing every coastline for every frame/pixel.
        for polygon in COASTS:
            for row in range(self.TH):
                lat=90-(row+.5)*180/self.TH
                crossings=[]
                for (x1,y1),(x2,y2) in zip(polygon,(*polygon[1:],polygon[0])):
                    if (y1>lat)!=(y2>lat):crossings.append(x1+(lat-y1)*(x2-x1)/(y2-y1))
                crossings.sort()
                for left,right in zip(crossings[::2],crossings[1::2]):
                    for col in range(max(0,int((left+180)*self.TW/360)),min(self.TW,math.ceil((right+180)*self.TW/360))):
                        self.land[row*self.TW+col]=1
        self.cloud=bytearray()
        for row in range(self.TH):
            lat=math.pi*(.5-(row+.5)/self.TH)
            for col in range(self.TW):
                lon=(col/self.TW-.5)*math.tau
                field=math.sin(lon*5+math.sin(lat*7)*2)+.5*math.sin(lon*13-lat*11)+.25*math.sin(lon*29+lat*23)
                self.cloud.append(round(max(0.,min(1.,(field-.48)*.65))*255))
                if abs(lat)>1.24+.045*math.sin(lon*7):self.land[row*self.TW+col]=2

    def build_geometry(self,width,height,zoom):
        radius=max(1,min(width*.73,height*1.48)*zoom)
        self.radius=radius
        samples=[]
        tilt=math.radians(23.4);ca,sa=math.cos(tilt),math.sin(tilt)
        for index,bit,x,y in self.pixels(width,height,radius,1.08):
            rr=x*x+y*y
            if rr>1.16:continue
            if rr>1:
                glow=math.exp(-(math.sqrt(rr)-1)*38)*.42
                samples.append((index,bit,None,0,glow,0.,0.));continue
            z=math.sqrt(1-rr)
            lat=math.asin(max(-1,min(1,-x*sa+y*ca)))
            lon=math.atan2(x*ca+y*sa,z)
            row=min(self.TH-1,int((.5-lat/math.pi)*self.TH))
            light=.12+.88*max(0,-x*.65+y*.25+z*.7176)
            col=(lon/math.tau+.5)*self.TW
            water_light=light*(.70+.10*math.cos(lat))
            land_light=light*(.70+.15*math.cos(lat*3))
            samples.append((index,bit,col,row*self.TW,light,water_light,land_light))
        return samples

    def frame(self,width,height,seconds,zoom=1):
        if width<=0 or height<=0:return []
        raster=Raster(width,height,getattr(self,'monochrome',False))
        rotation=(seconds*.105+.08)*self.TW/math.tau
        cloud_rotation=rotation*1.055
        texture,clouds=self.land,self.cloud
        tw=self.TW
        draw=raster.dot
        for index,bit,col,offset,light,water_light,land_light in self.geometry(width,height,zoom):
            if col is None:draw(index,bit,3,light);continue
            family=texture[offset+int(col+rotation)%tw]
            cloud=clouds[offset+int(col+cloud_rotation)%tw]
            if family==2:
                brightness=light*.92
            elif cloud>102:
                family=2;brightness=light*(.75+cloud/1020)
            else:
                brightness=land_light if family else water_light
            draw(index,bit,family,brightness)
        return self.finish(raster,seconds)


class Saturn(Scene):
    def build_geometry(self,width,height,zoom):
        radius=max(1,min(width*.34,height*1.03)*zoom)
        self.radius=radius
        samples=[]
        ca,sa=math.cos(-.32),math.sin(-.32)
        tilt=.36;ct=math.sqrt(1-tilt*tilt)
        for index,bit,x,y in self.pixels(width,height,radius,2.38):
            u,v=x*ca+y*sa,-x*sa+y*ca
            rr=x*x+y*y
            ring_r=math.hypot(u,v/tilt)
            ring_z=-v/tilt*ct
            z=math.sqrt(1-rr) if rr<1 else -100.
            gap=1.98<ring_r<2.08 or 2.255<ring_r<2.28
            if 1.26<ring_r<2.35 and ring_z>z and not gap:
                angle=math.atan2(v/tilt,u)
                band=.68+.16*math.sin(ring_r*80)+.10*math.sin(ring_r*218)
                sunlight=x*(-.65)+y*.25+ring_z*.7176
                if sunlight<0 and rr+ring_z*ring_z-sunlight*sunlight<1:band*=.24
                samples.append((index,bit,2,band,angle,ring_r));continue
            if rr<=1:
                lat=math.asin(max(-1,min(1,v*ct+z*tilt)))
                lon=math.atan2(u,z*ct-v*tilt)
                light=.14+.86*max(0,-x*.65+y*.25+z*.7176)
                band=.74+.10*math.sin(lat*29)+.06*math.sin(lat*61)
                family=1 if math.sin(lat*29)<-.35 else 0
                samples.append((index,bit,family,light*band,lon,lat))
        return samples

    def frame(self,width,height,seconds,zoom=1):
        if width<=0 or height<=0:return []
        raster=Raster(width,height,getattr(self,'monochrome',False))
        for index,bit,family,light,angle,lat in self.geometry(width,height,zoom):
            if family==2:
                brightness=light*(.90+.10*math.sin(angle*5+seconds*.21+lat*12))
            else:
                lon=angle+seconds*.16
                brightness=light*(.94+.06*math.sin(lon*6+lat*16))
                # A persistent pale storm gives the sphere visible axial rotation.
                delta=(lon-.6+math.pi)%math.tau-math.pi
                storm=math.exp(-(delta/.32)**2-((lat-.32)/.10)**2)
                brightness=min(1.,brightness+storm*.26)
            raster.dot(index,bit,family,brightness)
        return self.finish(raster,seconds)


class BlackHole(Scene):
    """A softly integrated gas volume with advected, periodic cloud turbulence.

    Curved secondary emission is an artistic lensing approximation, not GR tracing.
    Only the viewport geometry and density atlas are cached; clouds move with time.
    """
    TW,TH=256,128

    def __init__(self):
        super().__init__()
        rng=random.Random(8814)
        # Smooth periodic value noise, rather than isolated random dots each frame.
        grids=[(nx,ny,weight,[rng.random() for _ in range(nx*ny)])
               for nx,ny,weight in ((8,4,.24),(16,8,.30),(32,16,.25),(64,32,.15),(128,64,.06))]
        self.cloud=[]
        for y in range(self.TH):
            for x in range(self.TW):
                value=0.
                for nx,ny,weight,grid in grids:
                    gx=x*nx/self.TW;gy=y*ny/self.TH
                    ix,iy=int(gx),int(gy);fx,fy=gx-ix,gy-iy
                    fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy)
                    a=grid[iy*nx+ix];b=grid[iy*nx+(ix+1)%nx]
                    c=grid[((iy+1)%ny)*nx+ix];d=grid[((iy+1)%ny)*nx+(ix+1)%nx]
                    value+=weight*((a+(b-a)*fx)*(1-fy)+(c+(d-c)*fx)*fy)
                self.cloud.append(max(0.,(value-.34)*3.4)**2.4)

    def build_geometry(self,width,height,zoom):
        radius=max(1,min(width*.205,height*.65)*zoom)
        self.radius=radius
        samples=[]
        ca,sa=math.cos(-.12),math.sin(-.12)
        inclination=.43;ci=math.sqrt(1-inclination*inclination)
        # Color is resolved per terminal cell. Cache its exact eight-dot shadow
        # mask, then integrate the volume once, rather than eight identical colors.
        for index in range(width*height):
            col,row=index%width,index//width
            x=(col*2+1-width)/radius;y=(height*2-row*4-2)/radius
            mask=0
            for dy in range(4):
                for dx in range(2):
                    px=(col*2+dx+.5-width)/radius
                    py=(height*2-row*4-dy-.5)/radius
                    if px*px+py*py>=1:mask|=DOTS[dy][dx]
            if not mask:continue
            rho=max(1.,math.hypot(x,y))
            u,v=x*ca+y*sa,-x*sa+y*ca
            layers=[]
            for depths in ((.3,.9,1.6,2.4,3.3),(-.3,-.9,-1.6,-2.4,-3.3)):
                column=mean_r=mean_h=mean_s=mean_c=0.
                for z in depths:
                    plane=z*ci-v*inclination
                    r=math.hypot(u,plane)
                    h=v*ci+z*inclination
                    # A thick, hot flow: diffuse edges, with no hard outer disk boundary.
                    density=math.exp(-((r-2.15)/1.15)**2-(h/(.22+.21*r))**2)
                    density*=min(1.,max(0.,(r-.9)*2))/(.65+r*.45)
                    angle=math.atan2(plane,u)
                    column+=density
                    mean_r+=r*density;mean_h+=h*density
                    mean_s+=math.sin(angle)*density;mean_c+=math.cos(angle)*density
                if column<.002:
                    layers.append((0.,0.,0,0.));continue
                r=mean_r/column;h=mean_h/column
                angle=math.atan2(mean_s,mean_c)
                # Radial winding and differential angular velocity stretch clouds into wisps.
                tex_u=angle*self.TW/math.tau+r*19+math.sin(angle*2)*7
                row=int((r*.19+h*.21)*self.TH)%self.TH
                speed=self.TW/math.tau*.68/(r**1.5+.6)
                layers.append((column,tex_u,row*self.TW,speed))
            lens_r=math.hypot(u,v/.98)
            lens=math.exp(-((lens_r-1.43)/.25)**2)*(.34 if v>0 else .10)
            photon=math.exp(-((rho-1.045)/.042)**2)*.19
            haze=math.exp(-((rho-1.65)/.95)**2)*.055
            boost=1-.33*u/(rho+.1)
            if sum(layer[0] for layer in layers)*boost+lens+photon+haze<.035:continue
            samples.append((index,mask,*layers,lens,photon,haze,boost))
        return samples

    def sky_visible(self,x,y,width,height):
        return math.hypot((x*2+1-width)/self.radius,(y*4+2-height*2)/self.radius)>1.12

    def frame(self,width,height,seconds,zoom=1):
        if width<=0 or height<=0:return []
        raster=Raster(width,height)
        cells=[[(' ',24,False) for _ in range(width)] for _ in range(height)]
        mono=getattr(self,'monochrome',False)
        texture=self.cloud;tw=self.TW
        for index,mask,near,far,lens,photon,haze,boost in self.geometry(width,height,zoom):
            column=0.;cloud_light=0.
            for amount,u,row,speed in (near,far):
                if not amount:continue
                phase=u+seconds*speed
                base=math.floor(phase);blend=phase-base
                a=texture[row+base%tw];b=texture[row+(base+1)%tw]
                density=a+(b-a)*blend
                column+=amount*density
                cloud_light+=density
            opacity=column/(1.25+column)
            brightness=min(.99,opacity*boost+lens*(.20+.45*cloud_light)+photon+haze*cloud_light)
            if brightness<.02:continue
            family=3 if brightness>.94 else 1 if brightness>.40 else 0
            # Sparse subcell coverage lets faint gas dissolve into space instead of
            # drawing a solid contour. This same stable dither supports monochrome.
            coverage=brightness*(.65,.95,1.15,.90)[family] if mono else brightness/.24
            if coverage<1:
                level=max(0,min(16,round(coverage*16)))
                mask&=GAS_MASKS[(index%width)&1][level]
            if not mask:continue
            level=min(7,int(brightness*7.8))
            cells[index//width][index%width]=(chr(0x2800+mask),family*8+level,level>=6)
        return self.finish(raster,seconds,cells)
