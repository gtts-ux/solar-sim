"""Keyboard menu state and actions, independent of curses and terminal size."""
from dataclasses import dataclass
import shlex

from catalog import DWARF_PLANETS, MOONS, PLANETS, SUN, lookup
from flight_replay import FLIGHTS
from missions import SPACECRAFT, Spacecraft
from themes import SCREENSAVERS, THEMES


@dataclass(frozen=True)
class Item:
    label: str
    detail: str = ''
    commands: tuple = ()
    children: tuple = ()
    prompt: str = ''
    screensaver: bool = False
    stay: bool = False
    live_id: str = ''
    catalogue: str = ''


@dataclass
class Page:
    title: str
    items: tuple
    index: int = 0


def body_item(body):
    dwarf = body in DWARF_PLANETS or lookup(body.parent or '') in DWARF_PLANETS
    proxima = body.name.startswith('Proxima Centauri')
    interstellar = body.kind.startswith('Fictional ')
    name = shlex.quote(body.name)
    def action(label, command, detail):
        return Item(label, detail, command if isinstance(command,tuple) else (command,), catalogue='interstellar' if interstellar else 'proxima' if proxima else 'dwarf' if dwarf else 'planets')
    actions = [action('Profile', ('/back','/'+name), 'Size, mass, composition, history and references.'),
               action('Orbit view', '/orbit '+name, 'Open the numbered orbit map around this object.')]
    if not isinstance(body, Spacecraft):
        if body is not SUN:
            if body in (*PLANETS,*DWARF_PLANETS):
                actions += [action('Moons', '/moons '+name, 'List included natural moons; in orbit mode, show their orbits.')]
            actions += [action('Spacecraft', '/satellites '+name, 'List included artificial satellites around this object.')]
        actions += [action('Day length', '/day '+name, 'Mean solar day and sidereal rotation.')]
    return Item(body.name, body.kind+' / '+(body.parent or 'Solar system'), children=tuple(actions))


class Navigation:
    sections = ('Views', 'Planets', 'Moons', 'Spacecraft', 'Dwarfs', 'Missions', 'Settings', 'Clock', 'Live', 'Mods')

    def __init__(self):
        self.opened = False
        self.section = 0
        self.indices = [0]*len(self.sections)
        self.pages = []
        self.feedback = ''

    def toggle(self):
        self.opened = not self.opened
        self.feedback = ''

    def open_settings(self,sim,group=None):
        """Give /setting immediate arrow focus, including typed/numeric choices."""
        self.change_section(self.sections.index('Settings')-self.section)
        self.opened=True
        self.index=0
        if group in ('theme','screensaver'):
            self.index=0 if group=='theme' else 1
            self.activate(sim)
            choices=list(THEMES) if group=='theme' else list(SCREENSAVERS)
            self.index=choices.index(sim.settings.theme if group=='theme' else sim.settings.screensaver)

    @property
    def title(self):
        return self.pages[-1].title if self.pages else self.sections[self.section]

    @property
    def index(self):
        return self.pages[-1].index if self.pages else self.indices[self.section]

    @index.setter
    def index(self, value):
        if self.pages:
            self.pages[-1].index = value
        else:
            self.indices[self.section] = value

    def items(self, sim):
        if self.pages:
            return self.pages[-1].items
        section = self.sections[self.section]
        if section == 'Views':
            return (Item('Overview', 'Return to the dashboard; ends a running replay.', ('/back',)),
                    Item('Solar system orbits', 'All planets in the current catalogue.', ('/orbit',)),
                    Item('Inner orbits', 'Focus the inner solar system.', ('/orbit inner',)),
                    Item('Outer orbits', 'Focus the outer solar system.', ('/orbit outer',)),
                    Item('Selected object orbit', 'Follow '+sim.selected.name+'.', ('/orbit '+shlex.quote(sim.selected.name),)),
                    Item('Screensaver', 'Preview your animation; Enter returns.', screensaver=True),
                    Item('Compare objects...', 'Enter two object names after /compare.', prompt='/compare '),
                    Item('Help', 'Full command and keyboard guide.', ('/help',)),
                    Item('Getting started', 'Tutorial for sol-sim, controls and updating.', ('/tutorial',)),
                    Item('About the simulation', 'Data sources and model accuracy.', ('/info',)),
                    Item('Export snapshot', 'Save the current simulation to exports/.', ('/export',)),
                    Item('Quit', 'Close the observatory.', ('/quit',)))
        if section == 'Mods':
            return (Item('Proxima Centauri', 'Install in terminal: sol-sim -m"proxima centauri". Enter opens an installed mod.', ('/proxima centauri',)),
                    Item('Interstellar', 'Gargantua and the film worlds. Install: sol-sim -m"interstellar".', ('/interstellar',)),
                    Item('Return to Solar System', 'Leave the optional system catalogue.', ('/interstellar exit' if sim.interstellar_mode else '/proxima exit',)))
        if section in ('Planets', 'Moons', 'Spacecraft', 'Dwarfs'):
            bodies = {'Planets': tuple(sim.mod_bodies) if sim.mod_mode else (SUN,*PLANETS), 'Moons': tuple(b for b in MOONS if b in sim.visible_bodies),
                      'Spacecraft': tuple(b for b in SPACECRAFT if b in sim.visible_bodies), 'Dwarfs': DWARF_PLANETS}[section]
            entries = tuple(body_item(body) for body in bodies)
            if section == 'Dwarfs':
                entries += (Item('Return to normal planets', 'Leave the separate dwarf catalogue.', ('/dwarf exit',)),)
            return entries
        if section == 'Missions':
            controls = tuple(Item(label, 'Control the loaded historical replay.', ('/mission '+action,))
                             for label,action in (('Pause replay','pause'),('Resume replay','resume'),
                                                  ('Restart replay','restart'),('Stop replay','stop'))) if sim.mission else ()
            flights = tuple(Item(f.name, f.vehicle+' / '+f.operator, children=(
                Item('Replay in 30 seconds', f.summary, ('/mission '+shlex.quote(f.name)+' 30 seconds',)),
                Item('Replay in 1 minute', f.summary, ('/mission '+shlex.quote(f.name)+' 1 minute',)),
                Item('Replay in 5 minutes', f.summary, ('/mission '+shlex.quote(f.name)+' 5 minutes',)),
                Item('Flight information', 'Historical stages and references.', ('/mission info '+shlex.quote(f.name),)))) for f in FLIGHTS)
            return controls+flights
        if section == 'Settings':
            return (Item('Themes', 'Current: '+THEMES[sim.settings.theme][0], children=tuple(
                        Item(label, 'Apply and save this theme.', ('/setting theme '+key,), stay=True)
                        for key,(label,*_) in THEMES.items())),
                    Item('Screensavers', 'Current: '+SCREENSAVERS[sim.settings.screensaver], children=tuple(
                        Item(label, 'Choose and save this animation.', ('/setting screensaver '+key,), stay=True)
                        for key,label in SCREENSAVERS.items())),
                    Item('Preview screensaver', 'Preview your saved choice; Enter returns.', screensaver=True),
                    Item('Camera zoom', 'Choose a camera around the active object.', children=tuple(
                        Item(label, 'Apply this camera and return to the current view.', ('/camera '+name,))
                        for name,label in (('system','System'),('close','Close'),('body','Body view'),('high','High orbit'),('wide','Wide')))))
        if section == 'Clock':
            return (Item('Pause', 'Freeze the simulation or historical replay.', ('/pause',), stay=True),
                    Item('Resume', 'Continue at the configured rate.', ('/resume',), stay=True),
                    Item('Real time', 'Return to the actual UTC time at 1x; ends a replay.', ('/now',)),
                    Item('Set exact date/time...', 'Type YYYY/MM/DD and optionally HH:MM (UTC).', prompt='/time '),
                    Item('1 day per second', 'Simulation speed; stop a replay before changing speed.', ('/speed 1',), stay=True),
                    Item('10 days per second', 'Simulation speed; stop a replay before changing speed.', ('/speed 10',), stay=True),
                    Item('Reverse: 1 day per second', 'Simulation speed; stop a replay before changing speed.', ('/speed -1',), stay=True))
        entries = [Item('Open / refresh launch feed', 'Request launch status in the background.', ('/live refresh',)),
                   Item('All operators', 'NASA, ESA/European and SpaceX launches.', ('/live all',)),
                   Item('SpaceX', 'Filter the launch feed.', ('/live spacex',)),
                   Item('NASA', 'Filter the launch feed.', ('/live nasa',)),
                   Item('ESA / European', 'Filter the launch feed.', ('/live esa',))]
        entries += [Item(launch.name, launch.provider+' / Enter for details.', live_id=launch.id) for launch in sim.live_entries]
        return tuple(entries)

    def current(self, sim):
        entries = self.items(sim)
        self.index = min(max(0,self.index),max(0,len(entries)-1))
        return entries[self.index] if entries else None

    def move(self, amount, sim):
        self.current(sim)
        self.index = min(max(0,self.index+amount),max(0,len(self.items(sim))-1))
        self.feedback = ''

    def change_section(self, amount):
        self.section = (self.section+amount)%len(self.sections)
        self.pages.clear()
        self.feedback = ''

    def back(self):
        self.feedback = ''
        if self.pages:
            self.pages.pop()
        else:
            self.opened = False

    def activate(self, sim):
        item = self.current(sim)
        if item and item.children:
            self.pages.append(Page(item.label,item.children))
            self.feedback = ''
            return None
        return item

    def execute(self, item, sim):
        commands = item.commands
        if '/back' in commands:
            # Overview/profile actions leave the overlay and the underlying view.
            sim.overlay = None
        if item.catalogue == 'proxima' and not sim.proxima_mode:
            commands = ('/proxima centauri',)+commands
        elif item.catalogue == 'interstellar' and not sim.interstellar_mode:
            commands = ('/interstellar',)+commands
        elif item.catalogue == 'planets' and sim.mod_mode:
            commands = ('/interstellar exit' if sim.interstellar_mode else '/proxima exit',)+commands
        elif item.catalogue == 'dwarf' and sim.mod_mode:
            commands = ('/dwarf',)+commands
        elif item.catalogue and item.catalogue not in ('proxima','interstellar') and (item.catalogue=='dwarf') != sim.dwarf_mode:
            commands = ('/dwarf' if item.catalogue=='dwarf' else '/dwarf exit',)+commands
        if item.live_id:
            matches = [i for i,launch in enumerate(sim.live_entries,1) if launch.id==item.live_id]
            if not matches:
                self.feedback = 'Launch is no longer in this feed. Choose another launch.'
                return self.feedback
            commands = ('/live '+str(matches[0]),)
        response = ''
        for command in commands:
            response = sim.command(command)
            if response.startswith(('Could not run command:', 'File operation failed:')):
                self.feedback = response.splitlines()[0]
                return response
        self.feedback = 'Applied: '+item.label
        self.opened = item.stay
        return response
