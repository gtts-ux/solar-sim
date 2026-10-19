"""Optional local system modes, isolated from the Solar System catalogue."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shlex

from catalog import AU_KM, lookup
from mod_manager import ROOT, MOD_ID, REGISTRY, ModError, bodies, load, require_enabled
from interstellar import NOTICE as FILM_NOTICE, SOURCE as FILM_SOURCE, describe as film_profile

EPOCH = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
SOURCE = 'Illustrative Proxima orbit; measured period/scale, arbitrary phase and plane'
NOTICE = ('PROXIMA CENTAURI / separate system\n\n'
          'Confirmed planets: Proxima Centauri d and b, ordered from the star.\n'
          'Proxima c remains an unconfirmed candidate and has no simulated orbit.\n'
          'Positions and separations use illustrative phases, not a present-day ephemeris.\n'
          'Planet radii are estimates; masses are RV minimum masses.\n\n'
          '/planet lists worlds  /star opens the host star\n'
          '/proxima b or /proxima d opens a planet\n'
          '/orbit opens orbits; Left/Right zooms in orbit mode\n'
          '/compare "proxima b" "proxima d"\n'
          '/proxima exit returns to normal planets. /dwarf switches to dwarfs.')


class ProximaSupport:
    """Mixin for Simulation: no global catalogue changes, executable plugins or telemetry claims."""

    def __init__(self, *args, mods_path=None, **kwargs):
        self.mods_path = Path(mods_path) if mods_path is not None else ROOT/'mods'
        self.mod_id = None
        self.mod_data = None
        self.mod_bodies = []
        super().__init__(*args, **kwargs)

    def reset(self):
        self.mod_mode = False
        super().reset()

    @property
    def proxima_mode(self):
        return self.mod_mode and self.mod_id == MOD_ID

    @property
    def interstellar_mode(self):
        return self.mod_mode and self.mod_id == 'interstellar'

    @property
    def proxima_bodies(self):
        return self.mod_bodies if self.mod_id == MOD_ID else []

    @property
    def mod_key(self):
        return 'interstellar' if self.mod_id == 'interstellar' else 'proxima'

    @property
    def mod_notice(self):
        return FILM_NOTICE if self.interstellar_mode else NOTICE

    @property
    def mod_source(self):
        return FILM_SOURCE if self.interstellar_mode else SOURCE

    @property
    def mod_hint(self):
        return '/miller /mann /edmunds /interstellar exit | Fictional model' if self.interstellar_mode else '/proxima b /proxima d /proxima exit | Illustrative phases'

    def lookup(self, name):
        key = (name or '').lower().strip().strip('"\'')
        aliases = {'star':'Proxima Centauri', 'proxima star':'Proxima Centauri',
                   'proxima b':'Proxima Centauri b', 'proxima d':'Proxima Centauri d',
                   'pb':'Proxima Centauri b', 'pd':'Proxima Centauri d'}
        if self.mod_id == 'interstellar':
            aliases = {'blackhole':'Gargantua', 'black hole':'Gargantua',
                       'interstellar gargantua':'Gargantua',
                       **{alias:name for name in ('Miller','Mann','Edmunds') for alias in
                          (name.lower()+' planet', name.lower()+"'s planet", name.lower()+"' planet",
                           'interstellar '+name.lower(), name.lower()+"'s")}}
        if self.mod_bodies:
            aliases['core'] = self.mod_bodies[0].name
        key = aliases.get(key, key).lower()
        return next((b for b in self.mod_bodies if b.name.lower() == key), None) or lookup(name)

    def body(self, name):
        found = self.lookup(name)
        if found in self.mod_bodies:
            if not self.mod_mode:
                raise ModError('Use /'+REGISTRY[self.mod_id]['command']+' to open this separate catalogue first.')
            return found
        if self.mod_mode:
            choices = '/miller, /mann, /edmunds or /gargantua' if self.interstellar_mode else '/proxima b, /proxima d or /star'
            raise ModError('Choose '+choices+'. /'+REGISTRY[self.mod_id]['exit']+' returns to Solar System objects; /dwarf opens dwarfs. Distances across systems are not modeled.')
        return super().body(name)

    @property
    def primary_bodies(self):
        return self.mod_bodies[1:] if self.mod_mode else super().primary_bodies

    @property
    def visible_bodies(self):
        return self.mod_bodies if self.mod_mode else super().visible_bodies

    def source(self, body):
        return self.mod_source if body in self.mod_bodies else self.ephemeris.source(body, self.date)

    def children(self, body):
        return [b for b in self.mod_bodies if b.parent == body.name] if body in self.mod_bodies else super().children(body)

    def position(self, body):
        if body not in self.mod_bodies:
            return super().position(body)
        if not body.parent:
            return (0., 0., 0.)
        phase = 1.2 if body.name.endswith('d') else 3.8
        if self.interstellar_mode:
            phase = self.mod_bodies.index(body)*1.9
        angle = ((self.date-EPOCH).total_seconds()/86400/body.period*math.tau+phase) % math.tau
        return (body.orbit*math.cos(angle), body.orbit*math.sin(angle), 0.)

    def orbit_path(self, body):
        if body in self.mod_bodies:
            return lambda angle: (body.orbit*math.cos(angle), body.orbit*math.sin(angle), 0.)
        return super().orbit_path(body)

    def orbit_number(self, body, fallback):
        if body in self.mod_bodies[1:]:
            return self.mod_bodies.index(body)
        return super().orbit_number(body, fallback)

    def map_system(self, view=None):
        if not self.mod_mode:
            return super().map_system(view)
        if self.orbit_focus is not None and (view is None or view == self.view):
            return self.lookup(self.orbit_focus.parent), [self.orbit_focus]
        target = view or self.view
        if target in ('solar', self.mod_key, 'inner', 'outer', self.mod_bodies[0].name.lower(), 'core'):
            planets = self.primary_bodies
            return self.mod_bodies[0], planets[:1] if target == 'inner' else planets[1:] if target == 'outer' else planets
        return self.body(target), []

    def describe(self, body):
        if body not in self.mod_bodies:
            return super().describe(body)
        if self.interstellar_mode:
            return film_profile(body, self.date, self.position)
        planet = bool(body.parent)
        rows = [body.name.upper()+' / '+body.kind, '',
                f'  Parent               {body.parent or "Local system origin"}',
                f'  Mass                 {body.mass:.6g} kg'+(' (RV minimum; m sin i)' if planet else ' (rounded estimate)'),
                f'  Mean radius          {body.radius:,.1f} km'+(' (model estimate, not measured)' if planet else ' (rounded estimate)'),
                f'  Diameter             {2*body.radius:,.1f} km (estimate)',
                f'  Orbital radius       {body.orbit/AU_KM:.5f} AU' if planet else '  Distance from Sun    About 4.24 light-years',
                f'  Orbital period       {body.period:g} Earth days' if planet else '  Stellar rotation     About 83 Earth days',
                '  Solar day / rotation Unknown; tidal locking is possible' if planet else '  Solar day            Not applicable to a star',
                '  Moons / rings        None confirmed / unknown' if planet else '  Planets included     Proxima d, Proxima b (confirmed)',
                '  Spacecraft           None known in this system', '', 'TEMPERATURE', '  '+body.temperature,
                '', 'COMPOSITION', '  '+body.composition, '', 'ATMOSPHERE', '  '+body.atmosphere,
                '', 'NOTES', '  '+body.features, '', 'POSITION / local star-centered frame',
                f'  UTC                  {self.date:%Y-%m-%d %H:%M:%S}',
                '  X / Y / Z (km)       '+' / '.join(f'{p:,.1f}' for p in self.position(body)),
                '  '+SOURCE, '', 'Planet gravity/density are unknown; estimated radii do not establish them.',
                '/orbit  /compare "proxima b" "proxima d"  /sources  /proxima exit']
        return '\n'.join(rows)

    def open_body(self, body):
        if not self.mod_mode:
            return super().open_body(body)
        self.selected = body
        self.orbit_notice = ''
        self.system_filter = 'all'
        if self.screen == 'orbit':
            self.orbit_focus = body if body.parent else None
            self.view = self.mod_key
            return self.text_map()
        return self.describe(body)

    def text_map(self, width=88, height=25):
        text = super().text_map(width, height)
        if self.mod_mode:
            text = text.split('\n\nPaths:')[0]
            text += ('\n\nFictional model: invented layout and animation cycles, not canonical film measurements or GR orbits.\n/orbit /miller /mann /edmunds /interstellar exit' if self.interstellar_mode else
                     '\n\nProxima: circular illustrative orbits; phases and planes are arbitrary, not current observed positions.\n/orbit  /proxima b  /proxima d  /proxima exit')
        return text

    def leave_system(self):
        self.mod_mode = False
        self.dwarf_mode = False
        self.selected = lookup('earth')
        self.orbit_focus = None
        self.system_filter = 'all'
        self.view = 'solar'
        self.orbit_notice = ''
        self.camera.select('system')

    def _command(self, raw):
        parts = shlex.split(raw.strip().lstrip('/'))
        cmd = parts[0].lower() if parts else ''
        args = parts[1:]
        normalized = [p.lower() for p in args]
        if ((cmd == 'proxima' and normalized in ([], ['centauri'], ['centari'], ['exit'])) or
            (cmd == 'interstellar' and normalized in ([], ['exit']))):
            if normalized == ['exit']:
                self.overlay = None
                if self.mission is not None:
                    self.stop_mission()
                self.leave_system()
                return self.text_map() if self.screen == 'orbit' else 'SOLAR SYSTEM / normal planets restored.\n/planet  /orbit  /dwarf'
            mod_id = 'interstellar' if cmd == 'interstellar' else MOD_ID
            require_enabled(self.mods_path, mod_id)
            data = load(self.mods_path, mod_id)
            from updater import version
            if version((ROOT/'VERSION.txt').read_text()) < version(data['app_min']):
                raise ModError('This mod needs Solar Sim '+data['app_min']+'. Run sol-sim -u.')
            self.overlay = None
            if self.mission is not None:
                self.stop_mission()
            self.mod_id = mod_id
            self.mod_data = data
            self.mod_bodies = bodies(data)
            self.mod_mode = True
            self.dwarf_mode = False
            self.selected = self.mod_bodies[1] if self.interstellar_mode else self.mod_bodies[-1]
            self.orbit_focus = None
            self.system_filter = 'all'
            self.preview_missions = False
            self.view = self.mod_key
            self.camera.select('system')
            self.orbit_notice = 'Fictional film system / /interstellar exit returns to normal planets' if self.interstellar_mode else 'Illustrative phases / /proxima exit returns to the Solar System'
            return self.text_map() if self.screen == 'orbit' else self.mod_notice
        if cmd == 'help':
            return super()._command(raw)+'\n\nMODS\n  Terminal: sol-sim -m"proxima centauri" or sol-sim -m"interstellar"\n  /proxima centauri (also /proxima centari) opens the installed system.\n  /proxima exit returns to normal planets. /star, /proxima b, /proxima d.\n  /interstellar opens the fictional film system; /interstellar exit returns.\n  /gargantua /miller /mann /edmunds /compare miller mann'
        if self.mod_mode and cmd == 'dwarf':
            if normalized not in ([], ['exit']):
                raise ModError('Usage: /dwarf or /dwarf exit')
            self.leave_system()
        if self.mod_mode and cmd in ('mission','missions'):
            self.leave_system()
        if not self.mod_mode:
            return super()._command(raw)
        if cmd in ('compare','distance','day','sources','weight') or (self.proxima_mode and cmd == 'proxima' and normalized in (['c'], ['centauri','c'])):
            self.overlay = None
            self.screen = 'dashboard'
            self.orbit_focus = None
        if self.proxima_mode and cmd == 'proxima' and normalized in (['c'], ['centauri','c']):
            return 'PROXIMA CENTAURI C / unconfirmed candidate\n\nNo confirmed planetary nature; omitted from simulated orbits.\n'+self.mod_data['sources'][2]
        direct = self.lookup(' '.join(parts))
        if direct in self.mod_bodies:
            self.overlay = None
            return self.open_body(direct)
        if cmd in ('planet','planets'):
            self.overlay = None
            if args:
                body = self.body(' '.join(args))
                if not body.parent:
                    raise ModError('Choose /miller, /mann or /edmunds; /gargantua opens the black hole.' if self.interstellar_mode else 'Choose /proxima b or /proxima d; /star opens the star.')
                return self.open_body(body)
            self.screen = 'dashboard'
            return self.mod_notice+'\n\n'+'\n'.join(f'  /{b.name.lower()}  {b.orbit/AU_KM:.5f} AU  {b.period:g} '+('model days' if self.interstellar_mode else 'days') for b in self.primary_bodies)
        if cmd in ('orbit','view','focus','map'):
            self.overlay = None
            target = ' '.join(args).lower() if args else self.mod_key
            self.orbit_focus = None
            self.system_filter = 'all'
            self.orbit_notice = 'Fictional layout and periods; no GR or time-dilation solver.' if self.interstellar_mode else 'Illustrative orbital phases; not a present-day ephemeris.'
            if target in ('solar',self.mod_key,'inner','outer'):
                self.view = self.mod_key if target == 'solar' else target
            else:
                body = self.body(target)
                self.selected = body
                self.view = self.mod_key
                self.orbit_focus = body if body.parent else None
            if cmd != 'map':
                self.screen = 'orbit'
            return self.text_map()
        if cmd in ('moon','moons','mooons','satellite','satellites'):
            body = self.body(' '.join(args)) if args else self.selected
            self.overlay = None
            if not body.parent:
                return body.name+' has worlds on this map, not included moons. Use /planet or /orbit.'
            message = body.name+(': no confirmed moons; no moon orbits to display. Moon existence is unknown.' if cmd in ('moon','moons','mooons') else ': no known spacecraft in this system.')
            if self.interstellar_mode:
                message = body.name+(': moons are not specified in the film; no moon orbits included.' if cmd in ('moon','moons','mooons') else ': no spacecraft orbits included; Endurance appears in the story.')
            if self.screen == 'orbit':
                self.view = body.name.lower()
                self.orbit_focus = None
                self.selected = body
                self.system_filter = 'spacecraft' if cmd in ('satellite','satellites') else 'moons'
                self.orbit_notice = message
                return message+'\n\n'+self.text_map()
            return message
        if cmd == 'day':
            body = self.body(' '.join(args)) if args else self.selected
            if self.interstellar_mode:
                return body.name+' / DAY LENGTH\n'+('Not specified in the film; animation cycle is an invented orbital period, not a solar day. The film time-dilation ratio is not integrated.' if body.parent else 'A black hole has no planetary surface or solar day. Its spin period is not specified in this mod.')
            return body.name+' / DAY LENGTH\n'+('Solar day and sidereal rotation unknown; tidal locking is possible, not measured.' if body.parent else 'Star rotation: about 83 Earth days. Solar day: not applicable.')
        if cmd in ('compare','distance'):
            if len(args) != 2:
                raise ModError('Usage: /'+cmd+(' miller mann' if self.interstellar_mode else ' "proxima b" "proxima d"'))
            a, b = map(self.body, args)
            distance = math.dist(self.position(a), self.position(b))
            result = (f'{a.name.upper()} <> {b.name.upper()}\n\nSEPARATION / {self.date:%Y-%m-%d %H:%M:%S} UTC\n'
                      f'  Center-to-center distance: {distance:,.1f} km ({distance/AU_KM:.6g} AU)\n'
                      f'  One-way light travel time: {distance/299792.458:,.3f} seconds\n'
                      '  Illustrative local geometry; arbitrary phases, not an observed current distance.\n')
            if self.interstellar_mode:
                result = (f'{a.name.upper()} <> {b.name.upper()}\n\nSEPARATION / FICTIONAL MODEL / {self.date:%Y-%m-%d %H:%M:%S} UTC\n'
                          f'  Center-to-center distance: {distance:,.1f} km ({distance/AU_KM:.6g} AU)\n'
                          f'  Flat-space d/c illustration: {distance/299792.458:,.3f} seconds\n'
                          '  Invented schematic coordinates, not canonical distances.\n'
                          '  d/c ignores curved spacetime and is not a relativistic flight time.\n')
            if cmd == 'compare':
                result += '\n'+self.describe(a)+'\n\n'+self.describe(b)
            return result
        if cmd == 'weight':
            raise ModError('Interstellar numeric masses/radii are placeholders; a canonical surface weight is not available.' if self.interstellar_mode else 'Proxima planetary surface gravity is unknown; a measured weight cannot be calculated.')
        if cmd == 'sources':
            return REGISTRY[self.mod_id]['name'].upper()+' / sources\n\n'+'\n'.join(self.mod_data['sources'])+'\n\n'+self.mod_notice
        if cmd == 'info' and self.interstellar_mode:
            self.overlay = None
            self.screen = 'dashboard'
            return self.mod_notice
        if cmd == 'sync':
            self.overlay = None
            self.screen = 'dashboard'
            return 'Interstellar is fictional; there is no JPL ephemeris. The map uses invented layout and animation cycles.' if self.interstellar_mode else 'Proxima uses illustrative local orbits with published sizes/periods. JPL Solar System synchronization does not supply a Proxima ephemeris.'
        if cmd == 'export':
            if args:
                raise ModError('Use /export without arguments.')
            folder = ROOT/'exports'
            folder.mkdir(exist_ok=True)
            path = folder/f'{self.mod_key}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S-%f}.json'
            data = {'simulation_utc':self.date.isoformat(), 'mod_version':self.mod_data['version'],
                    'frame':self.mod_data['frame'], 'model':self.mod_source, 'fictional':self.interstellar_mode,
                    'bodies':[{'name':b.name, 'parent':b.parent, 'local_position_km':self.position(b),
                               'mass_kg':b.mass, 'mass_is_rv_minimum':bool(b.parent) and not self.interstellar_mode,
                               'values_are_fictional':self.interstellar_mode,
                               'mean_radius_km':b.radius, 'radius_is_estimate':True} for b in self.mod_bodies]}
            path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
            return 'Snapshot saved:\n'+str(path)
        return super()._command(raw)
