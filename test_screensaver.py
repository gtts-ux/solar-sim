"""Galaxy rendering and safe return from full-screen animation."""
from types import SimpleNamespace
from pathlib import Path
import tempfile
import math
import unittest
from unittest.mock import Mock, patch

from screensaver import Galaxy, PALETTE, show_screensaver, animation
from screensaver_scenes import Earth, Saturn, BlackHole, MoonView, BASIC, DOTS, Raster, scene_palette, Planet, PLANET_STYLES, JupiterMoons
from themes import Settings, SCREENSAVERS, THEMES
from engine import Simulation
from solar_sim import completions
from camera import Camera


class GalaxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.galaxy=Galaxy()

    def test_frames_fit_resizes_and_include_cool_arms_and_warm_core(self):
        for width,height in ((1,1),(20,8),(64,22),(120,40),(200,60)):
            frame=self.galaxy.frame(width,height,12)
            self.assertEqual(len(frame),height)
            self.assertTrue(all(len(row)==width for row in frame))
            self.assertTrue(all(0<=color<len(PALETTE) for row in frame for _,color,_ in row))
        self.assertEqual(self.galaxy.frame(0,20,1),[])
        self.assertEqual(self.galaxy.frame(20,0,1),[])
        frame=self.galaxy.frame(120,40,12)
        families={color//8 for row in frame for char,color,_ in row if char!=' '}
        self.assertEqual(families,{0,1,2,3})
        text=''.join(char for row in frame for char,_,_ in row)
        self.assertTrue(any(0x2800<ord(char)<=0x28ff for char in text))
        self.assertNotIn('SOLAR',text)
        self.assertNotIn('Enter',text)

    def test_rotation_is_time_based_and_does_not_randomize_between_frames(self):
        first=self.galaxy.frame(100,32,8)
        neighbor=self.galaxy.frame(100,32,8+1/30)
        later=self.galaxy.frame(100,32,15)
        self.galaxy.frame(64,22,9)
        self.assertEqual(first,self.galaxy.frame(100,32,8))
        self.assertEqual(first,Galaxy().frame(100,32,8))
        changes=lambda frame:sum(a!=b for row,other in zip(first,frame) for a,b in zip(row,other))
        self.assertGreater(changes(neighbor),0)
        self.assertLess(changes(neighbor),changes(later))

    def test_grouped_draw_runs_reconstruct_the_exact_frame(self):
        expected=self.galaxy.frame(80,24,3)
        reconstructed=[[(' ',24,False) for _ in range(80)] for _ in range(24)]
        for y,x,text,color,bold in self.galaxy.runs(80,24,3):
            self.assertLessEqual(x+len(text),80)
            for offset,char in enumerate(text):
                reconstructed[y][x+offset]=(char,color,bold)
        self.assertEqual(reconstructed,expected)


class ScreensaverStateTests(unittest.TestCase):
    def run_saver(self,keys,paused=False,colors=False,color_count=256,draw_error=None,saver='milky-way',camera=None):
        error=type('CursesError',(Exception,),{})
        curses=SimpleNamespace(error=error,COLORS=color_count,COLOR_PAIRS=256,
                               COLOR_BLACK=0,KEY_ENTER=343,KEY_LEFT=260,KEY_RIGHT=261,A_BOLD=1,A_DIM=2,
                               init_pair=Mock(),color_pair=lambda color:color<<8,
                               curs_set=Mock(),doupdate=Mock())
        screen=Mock()
        screen.getmaxyx.return_value=(24,80)
        screen.getbkgd.return_value=987
        if draw_error:
            screen.addstr.side_effect=draw_error
        sim=SimpleNamespace(paused=paused,running=True,last_tick=0,tick=Mock(),
                            screen='mission',mission=object(),selected=object(),
                            settings=SimpleNamespace(theme='cosmic',screensaver=saver))
        if camera is not None:sim.camera=camera
        key_iterator=iter(keys)
        def next_key():
            self.assertTrue(sim.paused)
            return next(key_iterator)
        screen.get_wch.side_effect=next_key
        original=(sim.screen,sim.mission,sim.selected)
        self.addCleanup(lambda:self.assertEqual((sim.screen,sim.mission,sim.selected),original))
        with patch.dict('sys.modules',{'curses':curses}),patch('screensaver.time.monotonic',return_value=100),patch('screensaver.animation') as factory:
            factory.return_value.runs.return_value=[(2,4,'⣿⣤',18,False)]
            if draw_error:
                with self.assertRaises(RuntimeError):
                    show_screensaver(screen,sim,colors)
            else:
                show_screensaver(screen,sim,colors)
        factory.assert_called_once_with(saver)
        self.assertEqual(sim.paused,paused)
        self.assertEqual(sim.last_tick,100)
        sim.tick.assert_called_once()
        screen.timeout.assert_called_with(60)
        screen.leaveok.assert_called_with(False)
        screen.bkgd.assert_called_with(987)
        return sim,screen,curses

    def test_enter_and_escape_return_without_changing_view_or_pause(self):
        for key in ('\r','\n',343,'\x1b'):
            for paused in (True,False):
                with self.subTest(key=key,paused=paused):
                    sim,_,_=self.run_saver(['x',key],paused)
                    self.assertTrue(sim.running)

    def test_control_c_and_d_exit_without_leaking_terminal_settings(self):
        for key in ('\x03','\x04'):
            sim,_,_=self.run_saver([key])
            self.assertFalse(sim.running)

    def test_animation_arrows_zoom_locally_without_changing_the_orbit_camera(self):
        camera=Camera();camera.select('body')
        self.run_saver([261,261,260,'\r'],camera=camera)
        self.assertEqual(camera.name,'body')

    def test_extended_eight_color_and_monochrome_modes(self):
        for colors,count,expected in ((True,256,32),(True,8,0),(False,256,0)):
            _,screen,curses=self.run_saver(['\r'],colors=colors,color_count=count)
            self.assertEqual(curses.init_pair.call_count,expected)
            screen.addstr.assert_called_once()

    def test_each_choice_enters_and_restores_the_original_mission_and_clock(self):
        for saver in SCREENSAVERS:
            self.run_saver(['\r'],saver=saver)
        self.assertIsInstance(animation('earth'),Earth)
        self.assertIsInstance(animation('saturn'),Saturn)
        self.assertIsInstance(animation('black-hole'),BlackHole)
        self.assertIsInstance(animation('milky-way'),Galaxy)

    def test_animation_initialization_also_pauses_and_restores_on_failure(self):
        screen=Mock();screen.getbkgd.return_value=987
        sim=SimpleNamespace(paused=False,running=True,last_tick=0,tick=Mock())
        def fail(_):
            self.assertTrue(sim.paused)
            raise RuntimeError('initialization failed')
        curses=SimpleNamespace(error=type('CursesError',(Exception,),{}),curs_set=Mock())
        with patch.dict('sys.modules',{'curses':curses}),patch('screensaver.animation',side_effect=fail):
            with self.assertRaises(RuntimeError):show_screensaver(screen,sim)
        self.assertFalse(sim.paused)
        screen.bkgd.assert_called_with(987)

    def test_unexpected_draw_failure_restores_clock_and_terminal(self):
        self.run_saver(['\r'],draw_error=RuntimeError('draw failed'))

class BodySceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenes=(Earth(),Saturn(),BlackHole())

    def test_shapes_fit_tiny_and_large_resizes_with_valid_palette_indices(self):
        for scene in self.scenes:
            for w,h in ((1,1),(20,8),(64,22),(120,40),(200,60)):
                with self.subTest(scene=type(scene).__name__,size=(w,h)):
                    frame=scene.frame(w,h,8)
                    self.assertEqual(len(frame),h)
                    self.assertTrue(all(len(row)==w for row in frame))
                    self.assertTrue(all(0<=color<32 for row in frame for _,color,_ in row))
            self.assertEqual(scene.frame(0,20,1),[])
            self.assertEqual(scene.frame(20,0,1),[])

    def test_animation_is_repeatable_and_continuous_across_adjacent_frames(self):
        for scene in self.scenes:
            with self.subTest(scene=type(scene).__name__):
                a=scene.frame(120,40,8)
                b=scene.frame(120,40,8+1/30)
                c=scene.frame(120,40,15)
                changed=lambda f:sum(x!=y for row,other in zip(a,f) for x,y in zip(row,other))
                self.assertGreater(changed(b),0)
                self.assertLess(changed(b),changed(c))
                scene.frame(64,22,9)
                self.assertEqual(a,scene.frame(120,40,8))
                self.assertNotEqual(a,scene.frame(120,40,8,zoom=.7))
                text=''.join(char for row in a for char,_,_ in row)
                self.assertTrue(any(0x2800<ord(c)<=0x28ff for c in text))
                self.assertNotIn('Enter',text)
                self.assertNotIn('SOLAR',text)

    def test_monochrome_shading_keeps_dots_inside_each_cell(self):
        raster=Raster(2,1,monochrome=True)
        for i in range(2):
            for row in DOTS:
                for bit in row:raster.dot(i,bit,0,.6)
        self.assertTrue(all(0<mask<255 for mask in raster.masks))
        self.assertNotEqual(raster.masks[0],raster.masks[1])

    def test_draw_runs_reproduce_frame_and_monochrome_retains_texture(self):
        for scene in self.scenes:
            for mono in (False,True):
                scene.monochrome=mono
                frame=scene.frame(64,22,4)
                reconstructed=[[(' ',24,False) for _ in range(64)] for _ in range(22)]
                for y,x,text,color,bold in scene.runs(64,22,4):
                    self.assertLessEqual(x+len(text),64)
                    for i,char in enumerate(text):reconstructed[y][x+i]=(char,color,bold)
                self.assertEqual(reconstructed,frame)
            scene.monochrome=False

    def test_earth_has_recognizable_land_ocean_and_polar_ice(self):
        earth=self.scenes[0]
        def surface(lon,lat):
            return earth.land[int((90-lat)*earth.TH/180)*earth.TW+int((lon+180)*earth.TW/360)]
        for lon,lat in ((-100,40),(-45,-15),(20,10),(135,-25)):
            self.assertEqual(surface(lon,lat),1,(lon,lat))
        for lon,lat in ((-140,0),(-30,20)):
            self.assertEqual(surface(lon,lat),0,(lon,lat))
        self.assertEqual(surface(0,-80),2)

    def test_saturn_occludes_far_rings_and_near_rings_cover_the_planet(self):
        saturn=self.scenes[1]
        frame=saturn.frame(120,40,8)
        # Two symmetric points at ring-plane v=+/-0.6, projected into the globe.
        self.assertIn(frame[14][63][1]//8,(0,1))
        self.assertEqual(frame[25][56][1]//8,2)
        # A ring gap is transparent: it must not erase the globe behind it.
        radius=min(120*.34,40*1.03)
        for py in range(160):
            for px in range(240):
                if ((px+.5-120)/radius)**2+((80-py-.5)/radius)**2<.95:
                    glyph=frame[py//4][px//2][0]
                    self.assertTrue(0x2800<ord(glyph)<=0x28ff)
                    self.assertTrue((ord(glyph)-0x2800)&DOTS[py%4][px%2])

    def test_black_hole_shadow_stays_dark_and_scenes_have_distinct_palettes(self):
        frame=self.scenes[2].frame(120,40,8)
        for y in range(17,23):
            for x in range(55,65):self.assertEqual(frame[y][x][0],' ')
        self.assertEqual(len({scene_palette(n,'cosmic') for n in BASIC}),len(BASIC))
        for name in BASIC:
            for theme in THEMES:
                palette=scene_palette(name,theme)
                self.assertEqual(len(palette),32)
                self.assertTrue(all(0<=c<=255 for c in palette))


class GasCloudTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.scene=BlackHole()

    def test_gas_moves_in_shape_and_has_soft_edges_and_vertical_depth(self):
        scene=self.scene
        first=scene.frame(120,40,0)
        later=scene.frame(120,40,9)
        moved=sum(a[0]!=b[0] for row,other in zip(first,later) for a,b in zip(row,other))
        self.assertGreater(moved,100)  # Gas changes coverage, rather than just color.
        feathered=above_plane=0
        for y,row in enumerate(first):
            for x,(glyph,_,_) in enumerate(row):
                if not 0x2800<ord(glyph)<0x2900:continue
                if 0<ord(glyph)-0x2800<255:feathered+=1
                u=(x*2+1-120)/scene.radius;v=(80-y*4-2)/scene.radius
                if abs(v)>.8 and u*u+v*v>2.7:above_plane+=1
        self.assertGreater(feathered,100)
        self.assertGreater(above_plane,100)

    def test_subcell_shadow_blocks_gas_and_stars_at_every_zoom(self):
        scene=self.scene
        for zoom in (.7,1.,1.35):
            frame=scene.frame(80,28,12,zoom)
            for y,row in enumerate(frame):
                for x,(glyph,_,_) in enumerate(row):
                    for dy in range(4):
                        for dx in range(2):
                            u=(x*2+dx+.5-80)/scene.radius
                            v=(56-y*4-dy-.5)/scene.radius
                            if u*u+v*v>=.96:continue
                            if glyph==' ':continue
                            self.assertTrue(0x2800<ord(glyph)<0x2900)
                            self.assertFalse((ord(glyph)-0x2800)&DOTS[dy][dx])

class PlanetSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.scenes={name:Planet(name) for name in PLANET_STYLES}

    def test_all_planets_are_registered_without_renumbering_existing_choices(self):
        self.assertEqual(list(SCREENSAVERS)[:4],['milky-way','earth','saturn','black-hole'])
        self.assertEqual(len(SCREENSAVERS),11)
        for name in self.scenes:
            self.assertIn(name,SCREENSAVERS)
            self.assertEqual(animation(name).name,name)
            self.assertIn(name,BASIC)

    def test_frames_fit_resizes_and_rotate_continuously_with_repeatable_textures(self):
        for name,scene in self.scenes.items():
            with self.subTest(planet=name):
                for w,h in ((1,1),(20,8),(64,22),(120,40),(200,60)):
                    frame=scene.frame(w,h,8)
                    self.assertEqual((len(frame),len(frame[0])),(h,w))
                    self.assertTrue(all(0<=color<32 for row in frame for _,color,_ in row))
                a=scene.frame(100,34,8);b=scene.frame(100,34,8+1/30);c=scene.frame(100,34,15)
                changed=lambda f:sum(x!=y for row,other in zip(a,f) for x,y in zip(row,other))
                self.assertGreater(changed(b),0)
                self.assertLess(changed(b),changed(c))
                self.assertEqual(a,scene.frame(100,34,8))
                self.assertNotEqual(a,scene.frame(100,34,8,zoom=.7))
                self.assertEqual(scene.frame(0,20,1),[])
                self.assertEqual(scene.frame(20,0,1),[])

    def test_each_planet_has_its_recognizable_surface_or_cloud_features(self):
        def at(scene,lon,lat):
            row=int((.5-lat/math.pi)*scene.TH);col=int((lon/math.tau+.5)*scene.TW)%scene.TW
            return scene.material[row*scene.TW+col]
        mercury=self.scenes['mercury']
        self.assertGreater(max(mercury.albedo)-min(mercury.albedo),.5)
        self.assertIn(2,self.scenes['venus'].material)
        mars=self.scenes['mars']
        self.assertEqual(at(mars,0,1.4),2)
        self.assertEqual(at(mars,0,-1.4),2)
        self.assertIn(1,mars.material)
        jupiter=self.scenes['jupiter']
        self.assertEqual(at(jupiter,.45,-.37),2)
        belts=[at(jupiter,0,-.9+i*.018) for i in range(100)]
        self.assertGreater(sum(a!=b for a,b in zip(belts,belts[1:])),8)
        self.assertTrue(85<self.scenes['uranus'].tilt<110)
        self.assertEqual(at(self.scenes['neptune'],-.48,-.30),1)
        self.assertIn(2,self.scenes['neptune'].material)

    def test_color_and_monochrome_runs_reproduce_frames_and_shaded_silhouettes(self):
        for name,scene in self.scenes.items():
            for mono in (False,True):
                scene.monochrome=mono
                frame=scene.frame(64,22,4)
                rebuilt=[[(' ',24,False) for _ in range(64)] for _ in range(22)]
                for y,x,text,color,bold in scene.runs(64,22,4):
                    self.assertLessEqual(x+len(text),64)
                    for i,char in enumerate(text):rebuilt[y][x+i]=(char,color,bold)
                self.assertEqual(frame,rebuilt,(name,mono))
                text=''.join(c[0] for row in frame for c in row)
                self.assertTrue(any(0x2800<ord(c)<=0x28ff for c in text))
                self.assertNotIn('SOLAR',text)
            scene.monochrome=False

    def test_multidigit_settings_choices_aliases_and_completions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            sim=Simulation(settings_path=root/'settings.json',launch_cache_path=root/'launch.json')
            sim.command('/mission Apollo 11 1 minute');replay=sim.mission
            sim.command('/setting')
            for number,name in enumerate(PLANET_STYLES,10):
                sim.command(str(number))
                self.assertEqual(sim.settings.screensaver,name)
                self.assertEqual(Settings(root/'settings.json').screensaver,name)
                self.assertIs(sim.mission,replay)
                self.assertIn('/setting screensaver '+name,completions('/setting screensaver '+name[:3],sim))
            self.assertIn('1 to 16',sim.command('/setting 17'))
            self.assertEqual(sim.settings.screensaver,'neptune')
            for alias,name in (('mrs','mars'),('urnanus','uranus')):
                sim.command('/setting screensaver '+alias)
                self.assertEqual(sim.settings.screensaver,name)


class JupiterTransitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.scene=Planet('jupiter')

    def test_shadow_follows_sun_ray_with_soft_edge_and_rejects_moons_behind_surface(self):
        moons=JupiterMoons()
        point=(0.,0.,1.)
        lx,ly,lz=moons.light
        perpendicular=math.hypot(lx,ly)
        def moon(offset=0,along=.8):
            return ('Test',lx*along+ly/perpendicular*offset,
                    ly*along-lx/perpendicular*offset,1+lz*along,.12,0,1.)
        self.assertEqual(moons.shadow(point,moon()),1)
        self.assertEqual(moons.shadow(point,moon(.3)),0)
        self.assertEqual(moons.shadow(point,moon(along=-.8)),0)
        edge=[moons.shadow(point,moon(offset)) for offset in (.10,.12,.14)]
        self.assertTrue(1>edge[0]>edge[1]>edge[2]>0)

    def test_front_moon_casts_dark_dot_precise_shadow_and_back_moon_is_hidden(self):
        scene=self.scene;scene.monochrome=False
        w,h=100,34
        with patch.object(scene.moons,'draw'):
            baseline=scene.frame(w,h,0)
        lx,ly,lz=scene.moons.light
        front=('Test',lx*.8,ly*.8,1+lz*.8,.14,0,.95)
        with patch.object(scene.moons,'positions',return_value=[front]):
            transit=scene.frame(w,h,0)
        removed=0
        for (index,bit),(x,y,z) in scene.moons.surface.items():
            if x*x+y*y>.04**2:continue
            before=baseline[index//w][index%w][0]
            after=transit[index//w][index%w][0]
            if 0x2800<ord(before)<=0x28ff and (ord(before)-0x2800)&bit:
                self.assertFalse(after!=' ' and (ord(after)-0x2800)&bit)
                removed+=1
        self.assertGreater(removed,4)
        behind=('Test',0.,0.,-2.,.14,0,.95)
        with patch.object(scene.moons,'positions',return_value=[behind]):
            hidden=scene.frame(w,h,0)
        self.assertEqual(baseline,hidden)

    def test_all_four_moons_move_continuously_and_dark_silhouettes_block_stars(self):
        scene=self.scene
        initial=scene.moons.positions(0,scene.tilt)
        self.assertEqual([m[0] for m in initial],['Io','Europa','Ganymede','Callisto'])
        nearby=scene.moons.positions(1/30,scene.tilt)
        later=scene.moons.positions(1,scene.tilt)
        for a,b,c in zip(initial,nearby,later):
            distance=lambda v:math.dist(a[1:4],v[1:4])
            self.assertTrue(0<distance(b)<distance(c))
        for mono in (False,True):
            scene.monochrome=mono
            frame=scene.frame(100,34,0)
            self.assertTrue(scene.moons.blocked_cells)
            for index in scene.moons.blocked_cells:
                x,y=index%100,index//100
                self.assertFalse(scene.sky_visible(x,y,100,34))
                self.assertNotIn(frame[y][x][0],('+','*','·'))
        scene.monochrome=False

    def test_transits_fit_all_zooms_and_resizes_in_color_and_monochrome(self):
        scene=self.scene
        for mono in (False,True):
            scene.monochrome=mono
            for w,h in ((1,1),(20,8),(64,22),(120,40)):
                for zoom in (.7,.9,1.,1.12,1.35):
                    frame=scene.frame(w,h,6,zoom)
                    self.assertEqual(len(frame),h)
                    self.assertTrue(all(len(row)==w for row in frame))
                    self.assertTrue(all(0<=color<32 for row in frame for _,color,_ in row))
        scene.monochrome=False


class SaverPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'settings.json'

    def test_existing_theme_preferences_migrate_without_losing_either_choice(self):
        self.path.write_text('{"version":1,"theme":"amber"}')
        settings=Settings(self.path)
        self.assertEqual(settings.screensaver,'milky-way')
        self.assertEqual(settings.theme,'amber')
        for name in SCREENSAVERS:
            settings.set_screensaver(name)
            restored=Settings(self.path)
            self.assertEqual((restored.theme,restored.screensaver),('amber',name))
        settings.set_screensaver('black-hole')
        settings.set_theme('ocean')
        self.assertEqual(Settings(self.path).screensaver,'black-hole')
        self.assertEqual(Settings(self.path).theme,'ocean')

    def test_commands_numbers_aliases_completion_and_reset_preserve_the_choice(self):
        sim=Simulation(settings_path=self.path,launch_cache_path=self.path.with_name('launch.json'))
        sim.command('/mission Apollo 11 1 minute');replay=sim.mission
        sim.command('/setting')
        for i,name in enumerate(SCREENSAVERS,6):
            sim.command(str(i))
            self.assertEqual(sim.settings.screensaver,name)
            self.assertIs(sim.mission,replay)
        for alias,expected in (('milky way','milky-way'),('black hole','black-hole'),('galaxy','milky-way')):
            sim.command('/setting screensaver '+alias)
            self.assertEqual(sim.settings.screensaver,expected)
        sim.command('/setting screensaver earth');sim.command('/reset')
        self.assertEqual(sim.settings.screensaver,'earth')
        self.assertIn('/setting screensaver black-hole',completions('/setting screensaver bla',sim))
        self.assertIn('Choose milky-way',sim.command('/setting screensaver imaginary'))
        self.assertEqual(sim.settings.screensaver,'earth')

    def test_malformed_preferences_and_failed_saves_do_not_erase_current_values(self):
        for text in ('[]','bad','{"theme":[],"screensaver":"earth"}',
                     '{"theme":"ocean","screensaver":[]}', '{"screensaver":"imaginary"}'):
            self.path.write_text(text)
            value=Settings(self.path)
            self.assertIn(value.theme,THEMES)
            self.assertIn(value.screensaver,SCREENSAVERS)
        value=Settings(self.path/'missing')
        with self.assertRaises(OSError):value.set_screensaver('saturn')
        self.assertEqual(value.screensaver,'milky-way')


class MoonViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=MoonView()

    @staticmethod
    def mask(frame,index,width):
        glyph=frame[index//width][index%width][0]
        return ord(glyph)-0x2800 if '\u2800'<=glyph<='\u28ff' else 0

    def test_full_half_crescent_new_and_opposite_lit_hemisphere(self):
        scene=self.scene;scene.monochrome=False
        frames={t:scene.frame(120,40,t) for t in (0,24,36,48,72)}
        earth,_=scene.geometry(120,40,1)
        def lit(t,side=lambda x:True):
            return sum(bool(self.mask(frames[t],index,120)&bit)
                       for index,bit,x,y,z,col,offset,glow in earth if col is not None and side(x))
        full=lit(0)
        self.assertGreater(full,1000)
        self.assertTrue(.4<lit(24)/full<.6)
        self.assertTrue(.07<lit(36)/full<.23)
        self.assertLess(lit(48),full*.01)
        self.assertEqual(lit(24,lambda x:x<-.1),0)
        self.assertEqual(lit(72,lambda x:x>.1),0)
        self.assertGreater(lit(24,lambda x:x>.1),full*.3)
        self.assertGreater(lit(72,lambda x:x<-.1),full*.3)

    def test_fixed_horizon_and_earth_do_not_leak_background_stars(self):
        scene=MoonView();scene.frame(100,34,0)
        center=scene.earth_center;horizon=list(scene.horizon)
        scene.stars=[(.55,.33,0,1),(.1,.96,0,1),(.05,.05,0,1)]
        for t in (0,24,48,72):
            frame=scene.frame(100,34,t)
            self.assertEqual(center,scene.earth_center)
            self.assertEqual(horizon,scene.horizon)
            for y,row in enumerate(frame):
                for x,(glyph,_,_) in enumerate(row):
                    if glyph in ('+','*','·'):
                        self.assertTrue(scene.sky_visible(x,y,100,34))
            self.assertNotIn(frame[11][55][0],('+','*','·'))
            self.assertNotIn(frame[32][10][0],('+','*','·'))
        self.assertEqual(frame[1][5][0],'+')

    def test_terrain_is_cratered_and_brightens_as_earth_wanes(self):
        scene=self.scene;scene.monochrome=False
        full=scene.frame(120,40,0);new=scene.frame(120,40,48)
        def ground(frame):
            return [color%8 for row in frame[32:] for glyph,color,_ in row if glyph!=' ' and color//8==3]
        self.assertGreater(len(set(ground(new))),2)
        self.assertGreater(sum(ground(new))/len(ground(new)),sum(ground(full))/len(ground(full)))
        self.assertTrue(any(0x2800<ord(c)<=0x28ff for row in full[30:] for c,_,_ in row))

    def test_resize_zoom_and_monochrome_runs_remain_deterministic(self):
        scene=self.scene
        for mono in (False,True):
            scene.monochrome=mono
            for w,h in ((1,1),(20,8),(64,22),(120,40),(200,60)):
                for zoom in (.7,1,1.35):
                    frame=scene.frame(w,h,24,zoom)
                    self.assertEqual(len(frame),h)
                    self.assertTrue(all(len(row)==w for row in frame))
                    self.assertTrue(all(0<=color<32 for row in frame for _,color,_ in row))
            expected=scene.frame(64,22,24)
            rebuilt=[[(' ',24,False) for _ in range(64)] for _ in range(22)]
            for y,x,text,color,bold in scene.runs(64,22,24):
                for offset,char in enumerate(text):rebuilt[y][x+offset]=(char,color,bold)
            self.assertEqual(expected,rebuilt)
            self.assertEqual(expected,scene.frame(64,22,24))
            text=''.join(c for row in expected for c,_,_ in row)
            self.assertTrue(all(c in ' ·+*' or 0x2800<ord(c)<=0x28ff for c in text))
        scene.monochrome=False
        self.assertEqual(scene.frame(0,22,1),[])
        self.assertEqual(scene.frame(64,0,1),[])

    def test_motion_is_smooth_repeatable_and_geometry_is_cached(self):
        scene=self.scene;scene.monochrome=False
        first=scene.frame(120,40,8);geometry=scene.samples
        neighbor=scene.frame(120,40,8+1/30)
        self.assertIs(geometry,scene.samples)
        later=scene.frame(120,40,17)
        changes=lambda frame:sum(a!=b for row,other in zip(first,frame) for a,b in zip(row,other))
        self.assertGreater(changes(neighbor),0)
        self.assertLess(changes(neighbor),changes(later))
        scene.frame(64,22,6)
        self.assertEqual(first,scene.frame(120,40,8))

    def test_settings_append_choice_and_accept_aliases_without_a_mod(self):
        self.assertEqual(list(SCREENSAVERS)[-1],'moon-view')
        self.assertIsInstance(animation('moon-view'),MoonView)
        self.assertIn('moon-view',BASIC)
        for theme in THEMES:
            self.assertEqual(len(scene_palette('moon-view',theme)),32)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            sim=Simulation(settings_path=root/'settings.json',launch_cache_path=root/'launch.json',mods_path=root/'mods')
            for command in ('/setting 16','/setting screensaver moon view','/setting screensaver moon',
                            '/setting screensaver lunar','/setting screensaver earth from moon'):
                self.assertNotIn('Could not run',sim.command(command))
                self.assertEqual(sim.settings.screensaver,'moon-view')
                self.assertEqual(Settings(root/'settings.json').screensaver,'moon-view')
            self.assertIn('/setting screensaver moon-view',completions('/setting screensaver moo',sim))
            self.assertIn('6-16',sim.settings.text())
            self.assertFalse((root/'mods').exists())


if __name__=='__main__':
    unittest.main()
