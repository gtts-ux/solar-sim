"""Persistent themes, camera geometry and live-provider/cache contracts."""
from datetime import datetime, timedelta, timezone
import io
import json
import math
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from camera import Camera, PRESETS, Point, render, mission_geometry
from catalog import PLANETS, MOONS, DWARF_PLANETS, SUN, lookup, satellites
from engine import Simulation
from flight_replay import FLIGHTS, Playback
from missions import SPACECRAFT, orbiters
from live_launches import API, LaunchFeed, countdown, get_json, launch_detail, parse_launch, parse_page
from solar_sim import completions
from themes import THEMES, Settings, galaxy_palette

UTC=timezone.utc
NOW=datetime(2026,10,17,12,tzinfo=UTC)


def row(name='Flight example',provider='SpaceX',identifier='flight-1',status=1,net='2026-10-18T12:00:00Z',agency=None):
    return {'id':identifier,'name':name,'net':net,'status':{'id':status,'name':'Launch in Flight' if status==6 else 'Go for Launch'},
            'launch_service_provider':{'name':provider},'mission':{'description':'Test description','agencies':[{'name':agency}] if agency else []},
            'rocket':{'configuration':{'full_name':'Falcon 9'}},'pad':{'name':'Pad 39A'},
            'vid_urls':[{'url':'https://www.youtube.com/watch?v=example'}],'program':[]}


class ThemeCameraTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.sim=Simulation(settings_path=self.root/'settings.json',launch_cache_path=self.root/'launch.json')
        self.sim.paused=True

    def test_exactly_five_distinct_themes_persist_and_reset_keeps_preference(self):
        self.assertEqual(len(THEMES),5)
        self.assertEqual(len({tuple(v[1]) for v in THEMES.values()}),5)
        self.assertIn('FIVE THEMES',self.sim.command('/setting'))
        self.sim.command('2');self.assertEqual(self.sim.settings.theme,'amber')
        for i,name in enumerate(THEMES,1):
            self.assertNotIn('Could not',self.sim.command(f'/setting {i}'))
            self.assertEqual(self.sim.settings.theme,name)
            self.assertEqual(Settings(self.root/'settings.json').theme,name)
            self.assertEqual(len(galaxy_palette(name)),32)
        self.sim.command('/setting theme ocean');self.sim.command('/reset')
        self.assertEqual(self.sim.settings.theme,'ocean')
        self.assertIn('Choose cosmic',self.sim.command('/setting theme imaginary'))
        self.assertEqual(self.sim.settings.theme,'ocean')

    def test_malformed_preference_is_safe_and_failed_save_does_not_change_theme(self):
        path=self.root/'settings.json'
        for value in ('invalid','[]','{"theme": []}','{"theme":"unknown"}'):
            path.write_text(value)
            self.assertEqual(Settings(path).theme,'cosmic')
        settings=Settings(self.root/'missing'/'settings.json')
        with self.assertRaises(OSError):settings.set_theme('amber')
        self.assertEqual(settings.theme,'cosmic')

    def test_controls_and_overlays_preserve_running_mission_and_orbit_view(self):
        self.sim.command('/orbit jupiter')
        self.sim.command('/setting');self.assertEqual(self.sim.screen,'orbit')
        self.sim.command('/setting exit');self.assertEqual(self.sim.screen,'orbit')
        self.sim.command('/mission Apollo 11 1 minute')
        replay=self.sim.mission
        for command in ('/camera next','/camera moon','/setting','/setting theme amber','/back'):
            self.sim.command(command)
            self.assertIs(self.sim.mission,replay)
            self.assertFalse(self.sim.paused)
        self.assertEqual(self.sim.screen,'mission')
        self.assertIsNone(self.sim.overlay)
        with patch.object(self.sim.launches,'request'):
            self.sim.command('/live')
        self.assertEqual(self.sim.overlay,'live')
        self.assertIs(self.sim.mission,replay)
        self.sim.command('/live exit')
        self.assertEqual(self.sim.screen,'mission')

    def test_camera_cycles_are_reversible_and_do_not_affect_clock(self):
        before=self.sim.date
        for _ in PRESETS:self.sim.camera.cycle(1)
        self.assertEqual(self.sim.camera.name,'system')
        self.sim.camera.cycle(-1);self.assertEqual(self.sim.camera.name,'wide')
        self.sim.camera.cycle(1);self.assertEqual(self.sim.camera.name,'system')
        for name,_,_ in PRESETS:
            self.assertIn('CAMERA',self.sim.command('/camera '+name))
            self.assertEqual(self.sim.camera.name,name)
        self.assertEqual(self.sim.date,before)
        self.assertIn('Camera:',self.sim.command('/camera unknown'))

    def test_camera_has_real_scale_and_close_tracks_the_chosen_point(self):
        camera=Camera();camera.select('close')
        points=[Point('Earth',0,0,4,'O'),Point('Spacecraft',1000,1000,3,'>')]
        image=render(90,24,camera,points,focus=(1000,1000))
        text='\n'.join(''.join(c[0] for c in row) for row in image)
        self.assertIn('Spacecraft',text);self.assertNotIn('O',text.splitlines()[12])
        self.assertIn('Outside view: Earth',text)
        camera.select('earth')
        image=render(90,24,camera,points)
        self.assertIn('Earth',''.join(c[0] for row in image for c in row))
        self.assertEqual(camera.extent,15000)

    def test_every_mission_stage_renders_at_every_camera_scale(self):
        for flight in FLIGHTS:
            replay=Playback(flight,60)
            for a,b in zip(replay.boundaries,replay.boundaries[1:]):
                replay.elapsed=(a+b)/2
                points,_,focus=mission_geometry(replay)
                self.assertTrue(all(math.isfinite(v) for v in focus))
                self.assertTrue(any(p.name=='Spacecraft' for p in points))
                for name,_,_ in PRESETS:
                    camera=Camera();camera.select(name)
                    frame=replay.scene(60,8,camera)
                    self.assertEqual((len(frame),len(frame[0])),(8,60))
                    marker='!' if replay.stage.visual=='abort' else '>'
                    self.assertEqual(frame[round(7/2)][round(59/2)][0],marker,
                                     (flight.name,replay.stage.name,name))

    def test_orbit_camera_uses_selected_body_and_completions_are_available(self):
        self.sim.command('/date 2026-10-17')
        self.sim.command('/iss');self.sim.command('/camera close')
        self.assertIn('ISS',''.join(c[0] for row in self.sim.camera_cells(90,24) for c in row))
        for command,result in (('/setting theme am','/setting theme amber'),('/camera mo','/camera moon'),('/live sp','/live spacex')):
            self.assertIn(result,completions(command,self.sim))

    def test_all_planets_moons_and_dwarfs_stay_centered_at_every_local_zoom(self):
        for body in [SUN,*PLANETS,*MOONS,*DWARF_PLANETS]:
            self.sim.selected=body
            self.sim.orbit_focus=None
            for name in ('close','body','high','wide'):
                self.sim.camera.select(name)
                with self.subTest(body=body.name,camera=name):
                    frame=self.sim.camera_cells(91,25)
                    self.assertEqual(frame[12][45][0],'O')
                    self.assertIn(body.name,self.sim.active_name)
                    # Changing the selection must change the origin, not the date.
                    self.assertIsNone(self.sim.mission)

    def test_catalogue_spacecraft_follow_their_own_positions_at_every_zoom(self):
        self.sim.command('/date 2026-10-17')
        for craft in SPACECRAFT:
            if craft not in orbiters(craft.parent,self.sim.date):continue
            self.sim.selected=craft
            for name in ('close','body','high','wide'):
                self.sim.camera.select(name)
                frame=self.sim.camera_cells(91,25)
                self.assertEqual(frame[12][45][0],'+',(craft.name,name))
                self.assertEqual(self.sim.active_name,craft.name)

    def test_local_scales_fit_giant_planets_and_their_outermost_moons(self):
        self.sim.camera.select('body')
        self.sim.selected=lookup('earth');earth_extent=self.sim.body_framing()[0]
        self.sim.selected=lookup('jupiter');jupiter_extent=self.sim.body_framing()[0]
        self.assertGreater(jupiter_extent,10*earth_extent)
        self.sim.camera.select('wide')
        for name in ('earth','mars','jupiter','saturn','uranus','neptune','pluto'):
            self.sim.selected=lookup(name)
            extent,_=self.sim.body_framing()
            self.assertTrue(all(extent>b.orbit*(1+b.eccentricity) for b in satellites(name)))
        self.sim.camera.select('earth');self.assertEqual(self.sim.camera.name,'body')
        self.sim.camera.select('moon');self.assertEqual(self.sim.camera.name,'wide')

    def test_mission_target_is_spacecraft_and_stopping_restores_previous_body(self):
        self.sim.command('/orbit mars')
        self.sim.command('/mission Apollo 11 1 minute')
        self.assertIn('Apollo 11',self.sim.active_name)
        self.assertNotEqual(self.sim.active_name,'Earth')
        self.sim.command('/mission seek 70')
        replay=self.sim.mission
        before=(replay.elapsed,self.sim.date)
        for _ in PRESETS:
            self.sim.camera.cycle(1)
            frame=self.sim.active_scene(91,25)
            self.assertEqual(frame[12][45][0],'>')
        self.assertEqual((replay.elapsed,self.sim.date),before)
        self.sim.command('/mission stop')
        self.assertEqual(self.sim.active_name,'Mars')

    def test_live_spacecraft_overrides_replay_without_inventing_coordinates(self):
        self.sim.command('/mission Apollo 11 1 minute')
        replay=self.sim.mission
        self.sim.launches.rows=(parse_launch(row(name='TEST live flight')),)
        with patch.object(self.sim.launches,'request'):
            self.sim.command('/live 1')
        self.assertIn('TEST live flight',self.sim.active_name)
        self.assertNotIn('Apollo',self.sim.active_name)
        for _ in PRESETS:
            self.sim.camera.cycle(1)
            frame=self.sim.active_scene(91,25)
            self.assertEqual(frame[12][45][0],'>')
            text='\n'.join(''.join(c[0] for c in r) for r in frame)
            self.assertIn('Position unavailable',text)
            self.assertIn('Falcon 9',text)
            self.assertNotIn('Earth',text)
            self.assertNotIn('Moon',text)
            self.assertNotIn('Apollo',text)
        self.assertIs(self.sim.mission,replay)
        with patch.object(self.sim.launches,'request'), patch('webbrowser.open',return_value=True):
            self.assertIn('Opened webcast',self.sim.command('/live watch 1'))
        self.assertIn('TEST live flight',self.sim.active_name)
        self.sim.command('/live exit')
        self.assertIn('Apollo 11',self.sim.active_name)
        self.assertIs(self.sim.mission,replay)


class LaunchFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'launch.json'
        self.feed=LaunchFeed(self.path)
        clock=patch('live_launches.now_utc',return_value=NOW)
        self.clock=clock.start();self.addCleanup(clock.stop)

    def sync(self,pages):
        with patch('live_launches.get_json',side_effect=pages) as request:
            self.feed.request()
            self.feed.thread.join(timeout=3)
            self.assertFalse(self.feed.busy)
        return request

    def test_provider_groups_are_based_on_actual_operator_mission_and_european_rockets(self):
        self.assertEqual(parse_launch(row()).groups,('spacex',))
        self.assertEqual(parse_launch(row(provider='ULA',agency='NASA')).groups,('nasa',))
        self.assertEqual(parse_launch(row(provider='Arianespace')).provider,'Arianespace')
        self.assertIn('esa',parse_launch(row(provider='Arianespace')).groups)
        self.assertIn('esa',parse_launch(row(provider='Other',agency='European Space Agency')).groups)
        self.assertIsNone(parse_launch(row(provider='Unrelated operator')))

    def test_schema_controls_urls_and_unknown_time_do_not_invent_a_launch(self):
        item=row(name='Bad\x1b[2J\nTitle',net='not-a-date')
        item['vid_urls']=[{'url':'javascript:bad'},{'url':'https://safe.example/live'},{'url':'https://bad.example/\ncommand'}]
        launch=parse_launch(item)
        self.assertNotIn('\x1b',launch.name)
        self.assertEqual(launch.webcasts,('https://safe.example/live',))
        self.assertEqual(countdown(launch),'Time to be announced')
        self.assertIn('NET: to be announced',launch_detail(launch))
        with self.assertRaises(ValueError):parse_page({'unexpected':[]})
        self.assertEqual(parse_page({'results':[None,[],{'id':'bad'}]})[0],[])

    def test_success_deduplicates_orders_and_never_promotes_elapsed_net_to_inflight(self):
        flying=row(identifier='active',status=6,net='2026-10-17T11:59:00Z')
        future=row(identifier='future')
        past=row(identifier='past',net='2026-10-16T12:00:00Z')
        done=row(identifier='done',status=3)
        request=self.sync([{'results':[flying],'next':None},{'results':[future,past,done,replace_dict(flying,status={'id':1,'name':'Go'})],'next':None}])
        self.assertEqual(request.call_count,2)
        self.assertIn('status=6',request.call_args_list[0].args[0])
        self.assertEqual(self.feed.rows[0].id,'active')
        self.assertEqual(len(self.feed.rows),3)
        self.assertIn('awaiting provider confirmation',countdown(next(r for r in self.feed.rows if r.id=='past')))
        self.assertIn('T+0d 00:01:00',countdown(self.feed.rows[0]))
        self.assertIn('elapsed time unavailable',countdown(parse_launch(row(status=6))))
        self.assertEqual(LaunchFeed(self.path).rows,self.feed.rows)

    def test_refresh_is_nonblocking_and_rate_budget_survives_restart(self):
        gate=threading.Event()
        def load(url):gate.wait(2);return {'results':[],'next':None}
        with patch('live_launches.get_json',side_effect=load):
            self.feed.request()
            self.assertTrue(self.feed.busy)
            self.feed.request();gate.set();self.feed.thread.join(timeout=3)
        self.assertEqual(len(self.feed.attempts),2)
        again=LaunchFeed(self.path)
        with patch('live_launches.get_json') as request:
            again.request();request.assert_not_called()
        self.assertEqual(again.next_request,NOW+timedelta(seconds=900))

    def test_failure_keeps_cache_and_429_obeys_retry_after(self):
        self.sync([{'results':[row(status=6)],'next':None},{'results':[],'next':None}])
        previous=self.feed.rows
        self.clock.return_value=NOW+timedelta(hours=1)
        error=HTTPError(API,429,'limited',{'Retry-After':'3600'},None)
        self.sync([error])
        self.assertEqual(self.feed.rows,previous)
        self.assertIn('UNVERIFIED',self.feed.label())
        self.assertEqual(self.feed.next_request,NOW+timedelta(hours=2))

    def test_inflight_pagination_is_followed_and_foreign_urls_are_rejected(self):
        next_url=API+'?status=6&limit=100&offset=100'
        request=self.sync([{'results':[row(identifier='first',status=6)],'next':next_url},
                           {'results':[row(identifier='second',status=6)],'next':None},
                           {'results':[],'next':None}])
        self.assertEqual(request.call_count,3)
        self.assertEqual(len(self.feed.rows),2)
        with self.assertRaises(ValueError):get_json('https://other.example/launches/')

    def test_http_request_matches_provider_schema_and_is_bounded(self):
        class Response(io.BytesIO):
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        with patch('live_launches.urlopen',return_value=Response(b'{"results":[],"next":null}')) as request:
            self.assertEqual(get_json(API+'?status=6')['results'],[])
        self.assertEqual(request.call_args.kwargs['timeout'],12)
        self.assertEqual(request.call_args.args[0].headers['Accept'],'application/json')

    def test_live_commands_filter_details_watch_and_do_not_stop_replay(self):
        sim=Simulation(settings_path=self.path.parent/'settings.json',launch_cache_path=self.path)
        sim.launches.rows=(parse_launch(row(identifier='1',status=6)),parse_launch(row(identifier='2',provider='ULA',agency='NASA')))
        sim.launches.updated=NOW
        sim.command('/mission Apollo 11 1 minute');replay=sim.mission
        with patch.object(sim.launches,'request'):
            result=sim.command('/live')
            self.assertIn('1 reported IN FLIGHT',result)
            self.assertIn('1. Flight example - SpaceX',result)
            self.assertIs(sim.mission,replay)
            self.assertIn('Rocket: Falcon 9',sim.command('/live 1'))
            with patch('webbrowser.open',return_value=True) as browser:
                sim.command('/live watch 1');browser.assert_called_once()
            self.assertIn('ULA',sim.command('/live nasa'))
            self.assertEqual(len(sim.live_entries),1)
            sim.command('/live exit');self.assertIs(sim.mission,replay)
        self.assertFalse(sim.paused)


def replace_dict(value,**changes):return dict(value,**changes)


if __name__=='__main__':unittest.main()
