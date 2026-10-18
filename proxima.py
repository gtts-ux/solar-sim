"""Optional local stellar-system mode, isolated from the Solar System catalogue."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shlex

from catalog import AU_KM, lookup
from mod_manager import ROOT, ModError, bodies, load

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
        self.proxima_data = None
        self.proxima_bodies = []
        super().__init__(*args, **kwargs)

    def reset(self):
        self.proxima_mode = False
        super().reset()

    def lookup(self, name):
        key = (name or '').lower().strip().strip('"\'')
        aliases = {'star':'Proxima Centauri', 'proxima star':'Proxima Centauri',
                   'proxima b':'Proxima Centauri b', 'proxima d':'Proxima Centauri d',
                   'pb':'Proxima Centauri b', 'pd':'Proxima Centauri d'}
        key = aliases.get(key, key).lower()
        return next((b for b in self.proxima_bodies if b.name.lower() == key), None) or lookup(name)

    def body(self, name):
        found = self.lookup(name)
        if found in self.proxima_bodies:
            if not self.proxima_mode:
                raise ModError('Use /proxima centauri to open the separate Proxima catalogue first.')
            return found
        if self.proxima_mode:
            raise ModError('Choose /proxima b, /proxima d or /star. /proxima exit returns to Solar System objects; /dwarf opens dwarfs. Distances across systems are not modeled.')
        return super().body(name)

    @property
    def primary_bodies(self):
        return self.proxima_bodies[1:] if self.proxima_mode else super().primary_bodies

    @property
    def visible_bodies(self):
        return self.proxima_bodies if self.proxima_mode else super().visible_bodies

    def source(self, body):
        return SOURCE if body in self.proxima_bodies else self.ephemeris.source(body, self.date)

    def children(self, body):
        return [b for b in self.proxima_bodies if b.parent == body.name] if body in self.proxima_bodies else super().children(body)

    def position(self, body):
        if body not in self.proxima_bodies:
            return super().position(body)
        if not body.parent:
            return (0., 0., 0.)
        phase = 1.2 if body.name.endswith('d') else 3.8
        angle = ((self.date-EPOCH).total_seconds()/86400/body.period*math.tau+phase) % math.tau
        return (body.orbit*math.cos(angle), body.orbit*math.sin(angle), 0.)

    def orbit_path(self, body):
        if body in self.proxima_bodies:
            return lambda angle: (body.orbit*math.cos(angle), body.orbit*math.sin(angle), 0.)
        return super().orbit_path(body)

    def orbit_number(self, body, fallback):
        if body in self.proxima_bodies[1:]:
            return self.proxima_bodies.index(body)
        return super().orbit_number(body, fallback)

    def map_system(self, view=None):
        if not self.proxima_mode:
            return super().map_system(view)
        if self.orbit_focus is not None and (view is None or view == self.view):
            return self.lookup(self.orbit_focus.parent), [self.orbit_focus]
        target = view or self.view
        if target in ('solar', 'proxima', 'inner', 'outer', 'proxima centauri', 'star'):
            planets = self.primary_bodies
            return self.proxima_bodies[0], planets[:1] if target == 'inner' else planets[1:] if target == 'outer' else planets
        return self.body(target), []

    def describe(self, body):
        if body not in self.proxima_bodies:
            return super().describe(body)
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
        if not self.proxima_mode:
            return super().open_body(body)
        self.selected = body
        self.orbit_notice = ''
        self.system_filter = 'all'
        if self.screen == 'orbit':
            self.orbit_focus = body if body.parent else None
            self.view = 'proxima'
            return self.text_map()
        return self.describe(body)

    def text_map(self, width=88, height=25):
        text = super().text_map(width, height)
        if self.proxima_mode:
            text = text.split('\n\nPaths:')[0]
            text += '\n\nProxima: circular illustrative orbits; phases and planes are arbitrary, not current observed positions.\n/orbit  /proxima b  /proxima d  /proxima exit'
        return text

    def leave_proxima(self):
        self.proxima_mode = False
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
        if cmd == 'proxima' and normalized in ([], ['centauri'], ['centari'], ['exit']):
            self.overlay = None
            if self.mission is not None:
                self.stop_mission()
            if normalized == ['exit']:
                self.leave_proxima()
                return self.text_map() if self.screen == 'orbit' else 'SOLAR SYSTEM / normal planets restored.\n/planet  /orbit  /dwarf'
            data = load(self.mods_path)
            from updater import version
            if version((ROOT/'VERSION.txt').read_text()) < version(data['app_min']):
                raise ModError('This mod needs Solar Sim '+data['app_min']+'. Run sol-sim -u.')
            self.proxima_data = data
            self.proxima_bodies = bodies(data)
            self.proxima_mode = True
            self.dwarf_mode = False
            self.selected = self.proxima_bodies[-1]
            self.orbit_focus = None
            self.system_filter = 'all'
            self.preview_missions = False
            self.view = 'proxima'
            self.camera.select('system')
            self.orbit_notice = 'Illustrative phases / /proxima exit returns to the Solar System'
            return self.text_map() if self.screen == 'orbit' else NOTICE
        if cmd == 'help':
            return super()._command(raw)+'\n\nMODS\n  Terminal: sol-sim -m"proxima centauri"\n  /proxima centauri (also /proxima centari) opens the installed system.\n  /proxima exit returns to normal planets. /star, /proxima b, /proxima d.'
        if self.proxima_mode and cmd == 'dwarf':
            if normalized not in ([], ['exit']):
                raise ModError('Usage: /dwarf or /dwarf exit')
            self.leave_proxima()
        if self.proxima_mode and cmd in ('mission','missions'):
            self.leave_proxima()
        if not self.proxima_mode:
            return super()._command(raw)
        if cmd in ('compare','distance','day','sources','weight') or (cmd == 'proxima' and normalized in (['c'], ['centauri','c'])):
            self.overlay = None
            self.screen = 'dashboard'
            self.orbit_focus = None
        if cmd == 'proxima' and normalized in (['c'], ['centauri','c']):
            return 'PROXIMA CENTAURI C / unconfirmed candidate\n\nNo confirmed planetary nature; omitted from simulated orbits.\n'+self.proxima_data['sources'][2]
        direct = self.lookup(' '.join(parts))
        if direct in self.proxima_bodies:
            self.overlay = None
            return self.open_body(direct)
        if cmd in ('planet','planets'):
            self.overlay = None
            if args:
                body = self.body(' '.join(args))
                if not body.parent:
                    raise ModError('Choose /proxima b or /proxima d; /star opens the star.')
                return self.open_body(body)
            self.screen = 'dashboard'
            return NOTICE+'\n\n'+'\n'.join(f'  /{b.name.lower()}  {b.orbit/AU_KM:.5f} AU  {b.period:g} days' for b in self.primary_bodies)
        if cmd in ('orbit','view','focus','map'):
            self.overlay = None
            target = ' '.join(args).lower() if args else 'proxima'
            self.orbit_focus = None
            self.system_filter = 'all'
            self.orbit_notice = 'Illustrative orbital phases; not a present-day ephemeris.'
            if target in ('solar','proxima','inner','outer'):
                self.view = 'proxima' if target == 'solar' else target
            else:
                body = self.body(target)
                self.selected = body
                self.view = 'proxima'
                self.orbit_focus = body if body.parent else None
            if cmd != 'map':
                self.screen = 'orbit'
            return self.text_map()
        if cmd in ('moon','moons','mooons','satellite','satellites'):
            body = self.body(' '.join(args)) if args else self.selected
            self.overlay = None
            if not body.parent:
                return 'Proxima Centauri has planets, not moons. Use /planet or /orbit.'
            message = body.name+(': no confirmed moons; no moon orbits to display. Moon existence is unknown.' if cmd in ('moon','moons','mooons') else ': no known spacecraft in this system.')
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
            return body.name+' / DAY LENGTH\n'+('Solar day and sidereal rotation unknown; tidal locking is possible, not measured.' if body.parent else 'Star rotation: about 83 Earth days. Solar day: not applicable.')
        if cmd in ('compare','distance'):
            if len(args) != 2:
                raise ModError('Usage: /'+cmd+' "proxima b" "proxima d"')
            a, b = map(self.body, args)
            distance = math.dist(self.position(a), self.position(b))
            result = (f'{a.name.upper()} <> {b.name.upper()}\n\nSEPARATION / {self.date:%Y-%m-%d %H:%M:%S} UTC\n'
                      f'  Center-to-center distance: {distance:,.1f} km ({distance/AU_KM:.6g} AU)\n'
                      f'  One-way light travel time: {distance/299792.458:,.3f} seconds\n'
                      '  Illustrative local geometry; arbitrary phases, not an observed current distance.\n')
            if cmd == 'compare':
                result += '\n'+self.describe(a)+'\n\n'+self.describe(b)
            return result
        if cmd == 'weight':
            raise ModError('Proxima planetary surface gravity is unknown; a measured weight cannot be calculated.')
        if cmd == 'sources':
            return 'PROXIMA CENTAURI / sources\n\n'+'\n'.join(self.proxima_data['sources'])+'\n\n'+NOTICE
        if cmd == 'sync':
            self.overlay = None
            self.screen = 'dashboard'
            return 'Proxima uses illustrative local orbits with published sizes/periods. JPL Solar System synchronization does not supply a Proxima ephemeris.'
        if cmd == 'export':
            if args:
                raise ModError('Use /export without arguments.')
            folder = ROOT/'exports'
            folder.mkdir(exist_ok=True)
            path = folder/f'proxima-{datetime.now(timezone.utc):%Y%m%d-%H%M%S-%f}.json'
            data = {'simulation_utc':self.date.isoformat(), 'mod_version':self.proxima_data['version'],
                    'frame':self.proxima_data['frame'], 'model':SOURCE,
                    'bodies':[{'name':b.name, 'parent':b.parent, 'local_position_km':self.position(b),
                               'mass_kg':b.mass, 'mass_is_rv_minimum':bool(b.parent),
                               'mean_radius_km':b.radius, 'radius_is_estimate':True} for b in self.proxima_bodies]}
            path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
            return 'Snapshot saved:\n'+str(path)
        return super()._command(raw)
