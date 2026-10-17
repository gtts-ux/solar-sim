"""Keplerian motion, terminal maps, and the slash-command interface."""
from datetime import datetime, timedelta, timezone
import difflib
import json
import math
from pathlib import Path
import random
import shlex
import time

from catalog import AU_KM, BODIES, CATALOG_DATE, DWARF_PLANETS, ELEMENTS, G, MOONS, PLANETS, SUN, lookup, satellites
from ephemeris import Ephemeris
from missions import SPACECRAFT, Spacecraft, mission_profile, orbiters
from day_lengths import day_info, day_label
from flight_replay import Playback, catalogue as flight_catalogue, find_flight, flight_info, parse_request
from themes import Settings, THEMES, SCREENSAVERS
from camera import Camera, Point, render as render_camera
from live_launches import LaunchFeed, SOURCE as LAUNCH_SOURCE, countdown, launch_detail, date as launch_date, https_url

UTC = timezone.utc
EPOCH = datetime(2000, 1, 1, 12, tzinfo=UTC)
MIN_DATE = datetime(1800, 1, 1, tzinfo=UTC)
MAX_DATE = datetime(2050, 1, 1, tzinfo=UTC)
ROOT = Path(__file__).resolve().parent

HELP = """EXPLORE
  /planet                 List all eight planets (/planets also works)
  /earth  /sun  /titan     Open any planet, star or included moon
  /planet jupiter         Alternate way to open a planet
  /moons jupiter          List its included moons; /moons lists all
                          In orbit mode, show all included moon orbits (/mooons works too)
  /dwarf                  Enter the separate dwarf-planet catalogue/orbit mode
  /dwarf exit             Return to the eight normal planets
  /moon europa            Open a moon profile
  /day earth              Mean solar day and sidereal rotation; /day uses selection
  /mission list           Ten historical flights, including Apollo and SpaceX
  /mission Apollo 11 1 minute  Play launch-to-return in the requested time
  /mission Artemis II 30 seconds  Flyby replay, with no lunar landing
  /mission pause|resume|restart|stop|status  Playback controls
  /mission seek 50        Jump to 50 percent of the playback
  /mission info Apollo 11 Historical stages and references
  /satellites earth       List spacecraft; in orbit mode, show their orbits
  /iss  /mro  /juno        Spacecraft profile, or focus its orbit in orbit mode
  /satellites mercury preview  Explicit preview of planned BepiColombo orbits
  /search ocean           Search names, composition and features
  /compare earth titan    Compare physical data, distance and light travel time
  /weight 70 mars         Weight for a mass in kg, in newtons and Earth kg-equivalent
  /distance earth mars    Approximate center-to-center distance at simulation time
  /random                 Discover a random body
  /setting                Themes and ten animated screensavers; choices save
  /camera wide            Camera: system, close, body, high, wide, next, prev
  /live                   Current and upcoming NASA, ESA/European and SpaceX launches
  /live NUMBER            Launch details; /live watch NUMBER opens a webcast
  /live refresh           Refresh when allowed; /live exit returns

SIMULATE
  /orbit [solar|inner|outer|NAME]  Full-screen numbered orbit view
  /earth or /europa        In orbit mode, focus that body's orbit around its parent
  /back                   Return to the overview dashboard (Esc also works)
  /realtime               Follow the actual current UTC time at 1x
  /sync                   Download current JPL Horizons positions in background
  /sync status            Show download status and errors
  /view solar             Solar map: solar, inner, outer, or a body name
  /view jupiter           Animate a planet and its included moons
  /focus europa           Select a body and open its local system
  /map                    Print a map in plain mode
  /speed 10               Earth days per real second (negative reverses time)
  /pause  /resume          Freeze or resume motion
  /step 30                Jump forward 30 days; negative goes backward
  /date 2030-01-01        Set date in UTC (1800 through 2049)
  /time 1969/12/03 [13:45] Set and pause at this UTC date/time; default midnight
  /time                   Show date and simulation settings
  /now                    Return to current real time, at 1x
  /reset                  Restore date, speed, view and display defaults
  /scale fit              fit = spread orbit sizes; linear = true distance ratios
  /labels off             Toggle map labels: on or off
  /trails on              Toggle dotted orbit paths: on or off
  /export                 Save a JSON snapshot in this folder's exports directory

APP
  /menu                   Arrow navigation (full-screen); Tab empty or F2 also opens it
  /info                   Model, accuracy and data notes
  /sources                Astronomy reference links
  /help                   This command guide
  /clear                  Clear the response panel
  /quit                   Exit (/exit also works)

KEYS (full-screen mode)
  Outside menus, Enter on an empty command opens your screensaver; Enter returns.
  The simulation pauses during the screensaver and resumes its previous state.
  Left/Right changes the camera only in orbit view with an empty prompt.
  Ctrl+B/F moves the input cursor; Home/End still edit the command line.
  Tab completes names/commands. Ctrl+P/N recalls commands.
  Tab on empty input or F2 opens the menu: arrows choose, Enter opens, Esc backs out.
  Elsewhere, arrows on empty input open navigation; /setting opens it directly.
  While typing, Left/Right edits input. Settings: Enter applies/previews, Space previews.
  Page Up/Down scroll responses. Ctrl+U clears input. Ctrl+C or Ctrl+D exits.
  Resize the terminal at any time. A larger window shows more detail.

Examples: /saturn, /\"Earth\", /moons saturn, /view saturn, /speed 0.2
"""

INFO = f"""SOLAR SIM / terminal observatory

Includes the Sun, 8 planets, 5 separate dwarf planets and {len(MOONS)} selected moons. All included bodies
move with simulation time. Giant-planet moon lists are deliberately selective;
the known-moon totals are separate, dated catalogue facts.

CURRENT POSITIONS / JPL HORIZONS
The default clock follows actual UTC at 1x. On interactive launch the app
downloads heliocentric J2000 ecliptic state vectors from NASA/JPL Horizons,
planets first, then moons. /sync retries; /sync status shows any failures.
Samples cover about 26 hours at 15-minute intervals. Cubic Hermite interpolation
uses the returned position and velocity vectors, with no extrapolation.
Each body shows its position source. Missing/out-of-window data uses the
offline fallback below. --offline disables automatic downloads. Cached vectors
remain usable within their window. Positions are geometric, not apparent sky
positions as observed from Earth. /speed, /date or /time DATE enters simulation time;
/realtime or /now returns to the actual current instant.

OFFLINE PLANET MODEL
NASA/JPL approximate Keplerian elements and century rates, solved with Newton's
method in 3D. Valid date window here: 1800-01-01 to 2049-12-31 UTC. The Sun is
fixed at the origin. Earth follows the Earth-Moon barycenter approximation.
UTC is used in place of dynamical time; no light-time or observer correction.

DWARF PLANETS
/dwarf switches catalogue and maps to Ceres, Pluto, Haumea, Makemake and Eris.
/dwarf exit returns to the eight normal planets. Lists, search, random picks
and completion follow the active catalogue. Offline dwarf ellipses use rounded
sizes, periods and eccentricities, with illustrative phases and orbital planes;
they are not predictions of current dwarf positions. Horizons replaces these
positions and orbit planes when data is available. Charon is included for Pluto;
the other dwarf moons currently have counts but no simulated orbits.

OFFLINE MOON MODEL
Fixed elliptical orbits use real approximate sizes, eccentricities and periods,
but illustrative starting phases and a common plane. Triton and Phoebe move
retrograde. These fallback moon positions are illustrative. Tidal evolution,
mutual gravity, precession, eclipses, spin rendering and collisions are omitted.
This is an educational orbital simulation, not an N-body gravity integration.

ARTIFICIAL SATELLITES
/satellites lists 16 selected stations and science orbiters; /satellites earth
or /satellites mars shows that planet's spacecraft in orbit mode. /iss focuses
ISS. /orbit earth and /orbit mars show included moons plus spacecraft;
/moons still shows only natural moons. This is not a census of Earth's many
thousands of satellites. Inactive objects still in orbit are labeled inactive.
Spacecraft use nominal elliptical orbits with synthetic phase/node and no live
tracking data, TLE/SGP4, drag, burns or operational forecasts. These markers do
not give the actual current position of ISS or other spacecraft. The status
catalogue was checked 2026-10-16; Juno's current operating status is unverified.
BepiColombo's MPO and Mio are UPCOMING, with Mercury capture scheduled for
2026-11-21, separation in December and science from April 2027. They never
automatically become confirmed current orbiters just because time advances.
/satellites mercury preview explicitly shows planned science ellipses.

DAY LENGTH AND HISTORICAL FLIGHTS
/day earth explains mean solar day versus sidereal rotation. Natural-body
profiles show solar-day length; these are approximate means, not daylight
hours at a location. Moon estimates use their parent planet's year.
/mission list offers ten historical launch-to-return replays. For example,
/mission Apollo 11 1 minute jumps the clock to launch and compresses the
flight into one minute. /pause, /resume and /mission seek 50 control playback.
Routes are schematic, not historical flight ephemerides. Dates use UTC,
milestones are rounded and some intermediate transitions are approximate.
Compression varies by stage to keep short events visible. Each mission
follows its own stages; lunar flybys do not acquire a landing phase.
Completion or /mission stop leaves the clock paused at the historical date.
/now returns to current time. Full-screen mode animates; plain mode and -c
provide text snapshots, with /mission status or seek to inspect progress.

THEMES, CAMERAS AND LIVE LAUNCHES
/setting lists five persistent themes: Cosmic, Amber, Ocean, Forest and Mono.
/setting theme amber applies one immediately. --no-color overrides colors.
/setting screensaver jupiter chooses a planet; all eight planets are included.
Milky Way and black-hole animations are also available; settings numbers 6-15.
Settings has immediate arrow focus; Enter applies themes or previews savers.
Space previews the saved animation; Enter again returns. Choices save locally.
In orbit view, Left/Right cycles system/close/body/high/wide cameras around the active target.
Ctrl+B/F edits input. Local camera scales use kilometers and enlarged markers;
mission geometry remains an illustration. Camera/theme changes do not stop missions.
/live explicitly fetches launch status from The Space Devs Launch Library 2.
It shows reported in-flight launches plus matches from the next 100 upcoming
global records; NASA, SpaceX and ESA/European-related launches are included.
Actual operator labels are preserved. Status, UTC countdowns and webcast links
are supplied; spacecraft positions and flight paths are not live telemetry.
The feed is independent of the simulation date, caches for 15 minutes, and
labels stale or failed updates unverified. /live refresh respects the cache.
/live watch NUMBER opens a supplied HTTPS webcast in the default browser.
settings.json and launch_cache.json stay local and are excluded from downloads.

DISPLAY
The dashboard shows distances and position sources. /orbit opens a full-screen
map; Esc or /back returns. Default 'linear' scale uses true distance ratios.
Wide solar views separate inner/outer planets, each with its own linear scale.
'fit' expands compact orbits. Numbered paths identify each body's orbit;
[number] markers show current positions. When JPL state vectors are available,
paths are osculating ellipses in the actual instantaneous orbital plane.
These approximate the current orbit, not its future perturbed trajectory.
Otherwise paths use the offline Kepler model. Body symbols are always enlarged.
The map is a top-down ecliptic projection with compact numbered markers.

DATA
Rounded mean radii and approximate masses. Density, spherical gravity and escape
speed are calculated from those values. Giant-planet gravity refers to a mean
reference radius; they have no solid surface. Temperatures are representative,
not forecasts. Moon composition/interior statements can be uncertain.
Estimated masses are marked. Sidereal rotation differs from solar day length.
Known-moon counts: Jupiter 115, Saturn 293, Uranus 29 (NASA August 2026);
Neptune 16. Catalogue checked {CATALOG_DATE}; counts can change.

Use /sources for references, or read README.txt and SOURCES.txt.
"""


def solve_kepler(mean, eccentricity):
    """Return eccentric anomaly in radians for an elliptical orbit."""
    mean = (mean + math.pi) % math.tau - math.pi
    anomaly = mean if eccentricity < .8 else math.copysign(math.pi, mean)
    for _ in range(30):
        delta = (anomaly - eccentricity * math.sin(anomaly) - mean) / (1 - eccentricity * math.cos(anomaly))
        anomaly -= delta
        if abs(delta) < 1e-12:
            break
    return anomaly


def elements_at(body, date):
    if body.kind == "Dwarf planet":
        # Sizes and periods are physical approximations; phase/plane are illustrative.
        # Actual current dwarf positions require Horizons, labeled per body.
        days = (date-EPOCH).total_seconds()/86400
        phase = sum(ord(c) for c in body.name) % 360
        return [body.orbit/AU_KM,body.eccentricity,0,phase+days*360/body.period,0,0]
    base, rates = ELEMENTS[body.name]
    centuries = (date - EPOCH).total_seconds() / (86400 * 36525)
    return [v + r * centuries for v, r in zip(base, rates)]


def planet_position(body, date, anomaly=None):
    a, e, inc, longitude, peri, node = elements_at(body, date)
    eccentric = solve_kepler(math.radians((longitude - peri) % 360), e) if anomaly is None else anomaly
    x = a * (math.cos(eccentric) - e)
    y = a * math.sqrt(1 - e * e) * math.sin(eccentric)
    w, n, i = map(math.radians, (peri - node, node, inc))
    cw, sw, cn, sn, ci, si = math.cos(w), math.sin(w), math.cos(n), math.sin(n), math.cos(i), math.sin(i)
    return tuple(v * AU_KM for v in (
        (cw * cn - sw * sn * ci) * x + (-sw * cn - cw * sn * ci) * y,
        (cw * sn + sw * cn * ci) * x + (-sw * sn + cw * cn * ci) * y,
        sw * si * x + cw * si * y))


def moon_offset(body, date, anomaly=None):
    days = (date - EPOCH).total_seconds() / 86400
    direction = -1 if body.name in ("Triton", "Phoebe") else 1
    phase = sum(ord(c) for c in body.name) * .13
    eccentric = solve_kepler(direction * days / body.period * math.tau + phase,
                             body.eccentricity) if anomaly is None else anomaly
    e = body.eccentricity
    x,y = body.orbit*(math.cos(eccentric)-e),body.orbit*math.sqrt(1-e*e)*math.sin(eccentric)
    if isinstance(body,Spacecraft):
        inc,node = math.radians(body.inclination),math.radians(body.node)
        return (math.cos(node)*x-math.sin(node)*math.cos(inc)*y,
                math.sin(node)*x+math.cos(node)*math.cos(inc)*y,math.sin(inc)*y)
    return (x,y,0.0)


def position(body, date):
    if body is SUN:
        return (0., 0., 0.)
    if body.kind not in ("Natural satellite","Artificial satellite"):
        return planet_position(body, date)
    origin = position(lookup(body.parent), date)
    return tuple(a + b for a, b in zip(origin, moon_offset(body, date)))


def number(value):
    return f"{value:,.2f}"


def osculating_ellipse(r, velocity, mu):
    """Ellipse in the actual orbital plane, derived from a relative state vector."""
    def cross(a,b):
        return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    radius = math.sqrt(sum(v*v for v in r))
    h = cross(r,velocity)
    hnorm = math.sqrt(sum(v*v for v in h))
    if not radius or not hnorm:
        return None
    ex = cross(velocity,h)
    eccentricity_vector = tuple(v/mu-p/radius for v,p in zip(ex,r))
    e = math.sqrt(sum(v*v for v in eccentricity_vector))
    inverse_a = 2/radius-sum(v*v for v in velocity)/mu
    if e>=1 or inverse_a<=0:
        return None
    a = 1/inverse_a
    p = tuple(v/e for v in eccentricity_vector) if e>1e-8 else tuple(v/radius for v in r)
    q = cross(tuple(v/hnorm for v in h),p)
    def point(anomaly):
        x,y = a*(math.cos(anomaly)-e),a*math.sqrt(1-e*e)*math.sin(anomaly)
        return tuple(x*px+y*qx for px,qx in zip(p,q))
    return point


def profile(body, date, position_fn=None):
    if isinstance(body,Spacecraft):
        return mission_profile(body,date,position_fn)
    lines = [f"{body.name.upper()} / {body.kind}", "", body.features, "", "PHYSICAL PROFILE"]
    values = [
        ("Length of solar day", day_label(body)),
        ("Parent", body.parent or "Milky Way (galactic orbit not simulated)"),
        ("Mass", f"{body.mass:.5g} kg" + (" (rough estimate)" if body.estimated_mass else "")),
        ("Mean radius", f"{number(body.radius)} km"),
        ("Mean diameter", f"{number(2 * body.radius)} km"),
        ("Mean density", f"{number(body.density)} kg/m^3 (derived)"),
        ("Spherical gravity", f"{body.gravity:.4g} m/s^2; {body.gravity / lookup('earth').gravity:.4g} Earth g"),
        ("Escape speed", f"{body.escape:.4g} km/s (derived)"),
        ("Mass / Earth", f"{body.mass / lookup('earth').mass:.5g} x"),
        ("Diameter / Earth", f"{body.radius / lookup('earth').radius:.5g} x"),
        ("Temperature", body.temperature),
    ]
    for label, value in values:
        lines.append(f"  {label:<20} {value}")
    lines += ["", "STRUCTURE", "  " + body.composition, "", "ATMOSPHERE", "  " + body.atmosphere]
    if body is not SUN:
        lines += ["", "ORBIT & ROTATION",
                  f"  Semi-major axis      {number(body.orbit)} km about {body.parent}",
                  f"  Orbital period       {body.period:,.5g} Earth days ({body.period / 365.25:.4g} years)",
                  f"  Eccentricity         {body.eccentricity:.5g}",
                  f"  Periapsis distance   {number(body.orbit * (1-body.eccentricity))} km from parent's center",
                  f"  Apoapsis distance    {number(body.orbit * (1+body.eccentricity))} km from parent's center"]
        if body.parent == "Sun":
            lines.append(f"  Mean Sun distance    {body.orbit / AU_KM:.5g} AU")
        if body.tilt is not None:
            lines.append(f"  Axial tilt           {body.tilt:.3g} degrees")
    if body.rotation:
        lines.append(f"  Sidereal rotation    {abs(body.rotation):,.5g} hours" + (" (retrograde)" if body.rotation < 0 else ""))
    elif body.name == "Phoebe":
        lines.append("  Sidereal rotation    ~9.3 hours; not tidally locked")
    elif body.name == "Nereid":
        lines.append("  Sidereal rotation    ~11.6 hours; not tidally locked")
    else:
        lines.append("  Rotation             Chaotic tumbling; no stable single period")
    if body.kind == "Natural satellite":
        lines.append("  Fallback moon model  Illustrative phase/plane; source shown below")
    else:
        lines += ["", f"  Rings                {body.rings}"]
        if body is not SUN:
            moons = satellites(body.name)
            lines += [f"  Known moons          {body.known_moons} (dated catalogue; see /info)",
                      f"  Included profiles    {', '.join(m.name for m in moons) or 'None'}",
                      f"  Spacecraft catalogue {', '.join(s.name for s in SPACECRAFT if s.parent==body.name) or 'None included'}; /satellites {body.name.lower()}"]
    xyz = position_fn(body) if position_fn else position(body,date)
    lines += ["", "SIMULATION POSITION / heliocentric, km", f"  UTC                  {date:%Y-%m-%d %H:%M:%S}",
              f"  X / Y / Z            {number(xyz[0])} / {number(xyz[1])} / {number(xyz[2])}",
              "", f"Try /view {body.name.lower()}   /compare {body.name.lower()} earth   /sources"]
    return "\n".join(lines)


COMMANDS = ["mission", "missions", "day", "satellites", "satellite", "dwarf", "mooons", "orbit", "back", "realtime", "sync", "planet", "planets", "moon", "moons", "search", "compare", "weight", "distance",
            "random", "view", "focus", "map", "speed", "pause", "resume", "step", "date", "time",
            "now", "reset", "scale", "labels", "trails", "export", "info", "sources", "help", "clear", "quit", "exit"]


COMMANDS = ['menu','setting','settings','camera','live'] + COMMANDS


class Simulation:
    def __init__(self, online=False, settings_path=None, launch_cache_path=None):
        self.ephemeris = Ephemeris(online=online)
        self.settings=Settings(settings_path or ROOT/'settings.json')
        self.launches=LaunchFeed(launch_cache_path or ROOT/'launch_cache.json')
        self.reset()

    def reset(self):
        self.camera=Camera()
        self.overlay=None
        self.live_filter='all'
        self.live_selection=None
        self.mission = None
        self.date = datetime.now(UTC)
        self.speed = 1 / 86400
        self.clock_mode = "realtime"
        self.screen = "dashboard"
        self.orbit_focus = None
        self.system_filter = "all"
        self.preview_missions = False
        self.dwarf_mode = False
        self.orbit_notice = ""
        self.paused = False
        self.view = "solar"
        self.selected = lookup("earth")
        self.scale = "linear"
        self.labels = True
        self.trails = True
        self.running = True
        self.last_tick = time.monotonic()

    def tick(self):
        now = time.monotonic()
        elapsed = now - self.last_tick
        self.last_tick = now
        if self.mission is not None:
            if not self.paused:
                self.mission.advance(elapsed)
            self.date=self.mission.date
            if self.mission.complete:
                self.paused=True
            return
        if not self.paused:
            self.set_date(datetime.now(UTC) if self.clock_mode == "realtime" else
                          self.date + timedelta(days=elapsed * self.speed), clamp=True)
        if self.clock_mode == "realtime":
            self.ephemeris.ensure(self.date)

    def set_date(self, date, clamp=False):
        if not MIN_DATE <= date < MAX_DATE:
            if not clamp:
                raise ValueError("Choose a date from 1800-01-01 through 2049-12-31.")
            date = min(max(date, MIN_DATE), MAX_DATE - timedelta(seconds=1))
            self.paused = True
        self.date = date
        if not clamp:
            self.mission = None
            self.clock_mode = "simulation"
        self.last_tick = time.monotonic()

    def stop_mission(self):
        if self.mission is not None:
            self.date=self.mission.date
            self.mission=None
            self.clock_mode='simulation'
            self.speed=0
            self.paused=True
        self.screen='dashboard'
        self.last_tick=time.monotonic()

    def position(self, body):
        precise = self.ephemeris.position(body,self.date)
        if precise is not None:
            return precise
        if body.kind in ("Natural satellite","Artificial satellite"):
            return tuple(a+b for a,b in zip(self.position(lookup(body.parent)),moon_offset(body,self.date)))
        return position(body,self.date)

    def describe(self, body):
        return profile(body,self.date,self.position) + "\nPosition source: " + self.ephemeris.source(body,self.date)

    def open_body(self, body):
        self.orbit_notice = ""
        self.preview_missions = False
        self.selected = body
        if isinstance(body,Spacecraft) and (body.planned or body.insertion>self.date.strftime('%Y-%m-%d')):
            self.screen = "dashboard"
            self.orbit_focus = None
            return self.describe(body)
        if self.screen == "orbit":
            self.system_filter = "all"
            self.preview_missions = False
            self.orbit_focus = body if body.parent else None
            self.view = (body.parent if body.kind in ("Natural satellite","Artificial satellite") else body.name).lower() if body.parent else "solar"
            return self.text_map()
        return self.describe(body)

    def orbit_path(self, body):
        parent = lookup(body.parent)
        state = [self.ephemeris.position(body,self.date), self.ephemeris.position(parent,self.date),
                 self.ephemeris.velocity(body,self.date), self.ephemeris.velocity(parent,self.date)]
        if all(v is not None for v in state):
            r = tuple(a-b for a,b in zip(state[0],state[1]))
            velocity = tuple(a-b for a,b in zip(state[2],state[3]))
            path = osculating_ellipse(r,velocity,G*(parent.mass+body.mass)/1e9)
            if path is not None:
                return path
        if parent is SUN:
            return lambda anomaly: planet_position(body,self.date,anomaly)
        return lambda anomaly: moon_offset(body,self.date,anomaly)

    def position_rows(self):
        center,bodies = self.map_system()
        origin = self.position(center)
        return [(index+1,body,math.dist(self.position(body),origin),
                 self.ephemeris.source(body,self.date)) for index,body in enumerate(bodies)]

    @property
    def primary_bodies(self):
        return DWARF_PLANETS if self.dwarf_mode else PLANETS

    @property
    def visible_bodies(self):
        natural = [SUN,*self.primary_bodies,*[m for m in MOONS if lookup(m.parent) in self.primary_bodies]]
        return [*natural,*[s for s in SPACECRAFT if lookup(s.parent) in natural]]

    def orbit_number(self, body, fallback):
        primary = DWARF_PLANETS if body in DWARF_PLANETS else PLANETS
        return primary.index(body)+1 if body in primary else fallback

    def body(self, name):
        body = lookup(name)
        if body is None:
            close = difflib.get_close_matches(name.lower(), list(BODIES), n=3, cutoff=.45)
            raise ValueError(f"Unknown body: {name}." + (" Try " + ", ".join('/' + n for n in close) + "." if close else " Use /planet or /moons."))
        if body not in self.visible_bodies:
            raise ValueError(f"{body.name} is in the other catalogue. Use " + ("/dwarf exit" if self.dwarf_mode else "/dwarf") + " first.")
        return body

    def status(self):
        if self.mission is not None:
            return self.mission.status(self.paused)
        rate = "REAL TIME / 1x" if self.clock_mode == "realtime" else f"SIMULATION / {self.speed:g} days/s"
        return f"{self.date:%Y-%m-%d %H:%M:%S} UTC | {'PAUSED' if self.paused else 'RUNNING'} | {rate} | {self.view} | {self.scale} scale"

    def command(self, raw):
        self.tick()
        try:
            return self._command(raw)
        except (ValueError, OverflowError) as error:
            if self.mission is not None:
                self.paused=True
            self.screen = "dashboard"
            self.preview_missions = False
            return f"Could not run command: {error}\nUse /help for syntax."
        except OSError as error:
            if self.mission is not None:
                self.paused=True
            self.screen = "dashboard"
            self.preview_missions = False
            return f"File operation failed: {error}"

    def _command(self, raw):
        if self.overlay in ('settings','live') and raw.strip().isdigit():
            raw=('/setting ' if self.overlay=='settings' else '/live ')+raw.strip()
        parts = shlex.split(raw.strip().lstrip("/"))
        if not parts:
            return "Type /planet to explore or /help for all commands."
        cmd, args = parts[0].lower(), parts[1:]
        if cmd=='menu':
            if args:
                raise ValueError('Usage: /menu')
            return ('ARROW NAVIGATION\n\nIn full-screen mode, /menu, F2 or Tab on empty input opens the menu.\n'
                    'Left/Right switches sections; Up/Down chooses; Enter opens; Esc goes back.\n'
                    'The arrow menu needs a macOS/Linux curses terminal. Plain mode uses slash commands; /help lists them.')
        if cmd in ('setting','settings'):
            if len(args)==1 and args[0].lower()=='exit':
                self.overlay=None
                return self.status()
            if args and args[0].lower() in ('screensaver','saver'):
                if len(args)>1:self.settings.set_screensaver(' '.join(args[1:]))
                else:self.overlay='settings'
            elif len(args)==1 and args[0].isdigit():
                setting_number=int(args[0])
                if 1<=setting_number<=len(THEMES):self.settings.set_theme(list(THEMES)[setting_number-1])
                elif 6<=setting_number<6+len(SCREENSAVERS):self.settings.set_screensaver(list(SCREENSAVERS)[setting_number-6])
                else:raise ValueError(f'Choose a settings number from 1 to {5+len(SCREENSAVERS)}.')
            elif args:
                choice=args[1].lower() if len(args)==2 and args[0].lower()=='theme' else args[0].lower() if len(args)==1 else ''
                if choice in ('1','2','3','4','5'):choice=list(THEMES)[int(choice)-1]
                self.settings.set_theme(choice)
            else:self.overlay='settings'
            return self.settings.text()
        if cmd=='camera':
            if len(args)>1:raise ValueError('Usage: /camera wide or /camera next')
            if args:
                name=args[0].lower()
                if name in ('next','prev'):self.camera.cycle(1 if name=='next' else -1)
                else:self.camera.select(name)
            return 'CAMERA / '+self.camera_label+'\nFollowing: '+self.active_name+'\n\nIn orbit view only, Left/Right changes zoom when the prompt is empty.\nElsewhere arrows navigate; /camera selects zoom directly in any view.\nBody/high/wide scales adapt to the selected body and its moons.\nMission geometry remains schematic; live launches have no position telemetry.\n/camera system restores automatic framing. earth/moon remain aliases for body/wide.'
        if cmd=='live':
            if len(args)==1 and args[0].lower()=='exit':
                self.overlay=None
                return self.status()
            self.overlay='live'
            if len(args)==1 and args[0].lower()=='status':return self.live_text()
            self.launches.request()
            if args and args[0].lower() in ('all','spacex','nasa','esa') and len(args)==1:
                self.live_filter=args[0].lower();self.live_selection=None
            elif args and args[0].lower()=='refresh' and len(args)==1:
                pass
            elif args:
                watch=args[0].lower()=='watch'
                launch_number=args[1] if watch and len(args)==2 else args[0] if len(args)==1 else ''
                entries=self.live_entries
                if not launch_number.isdigit() or not 1<=int(launch_number)<=len(entries):
                    return 'Choose a number from /live after the feed finishes loading.\n'+self.live_text()
                launch=entries[int(launch_number)-1]
                self.live_selection=launch.id
                if watch:
                    url=next((https_url(link) for link in launch.webcasts if https_url(link)),'')
                    if not url:return 'No webcast link has been announced for this launch.'
                    import webbrowser
                    opened=webbrowser.open(url)
                    return ('Opened webcast: ' if opened else 'Open this webcast link: ')+url
            else:self.live_selection=None
            return self.live_text()
        if cmd=='back' and self.overlay:
            self.overlay=None
            return self.status()
        if cmd=='time' and args:
            usage='Usage: /time YYYY/MM/DD [HH:MM], for example /time 1969/12/03 13:45 (UTC).'
            if len(args) not in (1,2):
                raise ValueError(usage)
            try:
                date=datetime.strptime(' '.join(args),'%Y/%m/%d %H:%M' if len(args)==2 else '%Y/%m/%d').replace(tzinfo=UTC)
            except ValueError:
                raise ValueError('Invalid date or time. '+usage) from None
            was_mission=self.mission is not None
            self.set_date(date)
            self.paused=True
            self.overlay=None
            if was_mission:
                self.screen='dashboard'
            return 'SIMULATION CLOCK\n\n'+self.status()+'\n\nPaused at the requested instant. /resume continues at the configured speed; /now returns to real time.'
        if cmd not in ('pause','resume','time','export'):
            self.overlay=None
        if cmd in ("mission","missions"):
            if not args or args==["list"] or cmd=="missions":
                self.stop_mission()
                return flight_catalogue()
            action=args[0].lower()
            if action=='info':
                item=find_flight(' '.join(args[1:]))
                self.stop_mission()
                return flight_info(item)
            if action in ('pause','resume','restart','stop','status','seek'):
                if self.mission is None:
                    raise ValueError('No flight replay is loaded. Try /mission Apollo 11 1 minute.')
                if action=='stop':
                    self.stop_mission()
                    return 'Mission playback stopped. Clock paused at its current historical date. /now returns to real time.'
                if action=='pause':
                    self.paused=True
                elif action=='resume':
                    if self.mission.complete:
                        return 'Mission complete. Use /mission restart to replay it.'
                    self.paused=False
                elif action=='restart':
                    self.mission.elapsed=0
                    self.paused=False
                elif action=='seek':
                    if len(args)!=2:
                        raise ValueError('Usage: /mission seek 50')
                    self.mission.seek(float(args[1]))
                    if self.mission.complete:
                        self.paused=True
                self.date=self.mission.date
                self.screen='mission'
                self.last_tick=time.monotonic()
                return self.mission.status(self.paused)
            item,duration=parse_request(args)
            playback=Playback(item,duration)
            self.mission=playback
            self.clock_mode='mission'
            self.screen='mission'
            self.paused=False
            self.date=item.start
            self.dwarf_mode=False
            self.view='solar'
            self.orbit_focus=None
            self.preview_missions=False
            self.last_tick=time.monotonic()
            return playback.status()
        if self.mission is not None:
            if cmd=='time':
                return self.mission.status(self.paused)
            if cmd=='pause':
                self.paused=True
                return self.mission.status(True)
            if cmd=='resume':
                if self.mission.complete:
                    return 'Mission complete. /mission restart replays the flight.'
                self.paused=False
                return self.mission.status(False)
            if cmd in ('speed','step'):
                raise ValueError('Mission duration controls playback speed. Use /mission stop first or start a new timed replay.')
            if cmd not in ('export','quit','exit'):
                self.stop_mission()
        if cmd=='day':
            body=self.body(' '.join(args)) if args else self.selected
            self.screen='dashboard'
            return day_info(body)
        if cmd == "mooons":
            cmd = "moons"
        if cmd == "satellite":
            cmd = "satellites"
        if cmd == "dwarf":
            self.orbit_notice = ""
            if args not in ([],["exit"]):
                raise ValueError("Usage: /dwarf or /dwarf exit")
            self.dwarf_mode = not args
            self.orbit_focus = None
            self.system_filter = "all"
            self.preview_missions = False
            self.view = "solar"
            self.selected = self.primary_bodies[0] if self.dwarf_mode else lookup("earth")
            title = "DWARF PLANETS / separate catalogue" if self.dwarf_mode else "PLANETS / normal catalogue restored"
            listing = title+"\n\n"+"\n".join(f"  /{b.name.lower():<10} {b.orbit/AU_KM:>7.2f} AU   {b.known_moons} known moons" for b in self.primary_bodies)
            listing += "\n\n/dwarf exit returns to normal planets." if self.dwarf_mode else "\n\n/dwarf opens the separate dwarf catalogue."
            return self.text_map() if self.screen == "orbit" else listing
        if lookup(" ".join(parts)):
            body = self.body(" ".join(parts))
            return self.open_body(body)
        if cmd in ("satellites","planet","planets","moon","moons","search","compare","distance","weight","random","info","help","sources","sync"):
            if not (self.screen == "orbit" and cmd in ("planet","planets","moon","moons","satellites") and args):
                self.screen = "dashboard"
                self.orbit_focus = None
                self.preview_missions = False
        if cmd in ("quit", "exit"):
            self.running = False
            return "Observatory closed. Clear skies!"
        if cmd == "help":
            return HELP
        if cmd == "info":
            return INFO
        if cmd == "sources":
            return (ROOT / "SOURCES.txt").read_text(encoding="utf-8")
        if cmd == "clear":
            return ""
        if cmd == "back":
            self.orbit_notice = ""
            self.screen = "dashboard"
            self.orbit_focus = None
            self.preview_missions = False
            return "OVERVIEW / /orbit opens the full-screen orbit display."
        if cmd == "sync":
            if args == ["status"]:
                return self.ephemeris.details()
            if args:
                raise ValueError("Usage: /sync or /sync status")
            self.ephemeris.ensure(self.date,force=True)
            return "JPL HORIZONS / syncing in the background\n\nPlanets load first, followed by moons. /sync status shows progress.\nOffline positions stay visibly labeled until the corresponding data arrives."
        if cmd in ("planet", "planets"):
            if args:
                body = self.body(" ".join(args))
                if body not in self.primary_bodies:
                    raise ValueError("Choose a planet in the current catalogue. /dwarf changes catalogue.")
                return self.open_body(body)
            return ("DWARF PLANETS" if self.dwarf_mode else "PLANETS") + " / ordered from the Sun\n\n" + "\n".join(
                f"  /{p.name.lower():<10} {p.kind:<20} {p.orbit / AU_KM:>6.2f} AU   {p.known_moons:>3} known moons" for p in self.primary_bodies
            ) + ("\n\nOpen /pluto or /ceres. /dwarf exit restores normal planets." if self.dwarf_mode else
                 "\n\nOpen a profile with /earth or /jupiter. The Sun: /sun. Moon totals are dated; /info.")
        if cmd == "moon":
            if not args:
                raise ValueError("Usage: /moon europa. Use /moons for the list.")
            body = self.body(" ".join(args))
            if body.kind != "Natural satellite":
                raise ValueError("Choose a moon, for example /moon titan.")
            return self.open_body(body)
        if cmd == "satellites":
            preview = bool(args and args[-1].lower()=="preview")
            names = args[:-1] if preview else args
            if preview and not names:
                raise ValueError("Usage: /satellites mercury preview")
            parents = [self.body(" ".join(names))] if names else [p for p in self.visible_bodies if not isinstance(p,Spacecraft) and p is not SUN]
            if any(isinstance(p,Spacecraft) or p is SUN for p in parents):
                raise ValueError("Choose a planet or moon, for example /satellites earth.")
            lines = ["SPACECRAFT / selected major missions, not a complete Earth satellite census", "",
                     "Orbit markers use illustrative nominal ellipses, NOT live spacecraft tracking.", ""]
            for parent in parents:
                missions = [s for s in SPACECRAFT if s.parent==parent.name]
                if not names and not missions:
                    continue
                lines.append(parent.name.upper())
                if not missions:
                    lines.append("  No current spacecraft orbiters in this catalogue.")
                    if parent.name == "Saturn":
                        lines.append("  Cassini ended with impact in September 2017; no present orbit is drawn.")
                    elif parent.name in ("Uranus","Neptune","Pluto"):
                        lines.append("  Flyby spacecraft are not orbiters and are not drawn as satellites.")
                for item in missions:
                    status = item.status if item.insertion<=self.date.strftime('%Y-%m-%d') or item.planned else "Not yet in orbit at the selected simulation date"
                    lines.append(f"  /{item.name.lower():<12} {status}")
                lines.append("")
            if self.screen == "orbit" and names:
                parent = parents[0]
                self.selected = parent
                self.orbit_focus = None
                self.view = parent.name.lower()
                self.system_filter = "spacecraft"
                self.preview_missions = preview
                count = len(orbiters(parent.name,self.date,preview))
                if preview:
                    self.orbit_notice = f"PLANNED PREVIEW: {parent.name} / {count} nominal orbits; not current positions"
                elif count:
                    self.orbit_notice = f"{parent.name}: {count} selected spacecraft / nominal illustrative orbits"
                else:
                    upcoming = [s for s in SPACECRAFT if s.parent==parent.name and s.planned]
                    self.orbit_notice = (f"{parent.name}: no confirmed current orbiters. BepiColombo capture planned 2026-11-21; /satellites mercury preview" if upcoming else
                                         f"{parent.name}: no current spacecraft orbiters in this catalogue.")
                return "\n".join(lines)+"\n"+self.text_map()
            return "\n".join(lines)+"\nTry /orbit then /satellites earth or /iss. /satellites mercury preview shows only planned ellipses."
        if cmd == "moons":
            parents = [self.body(" ".join(args))] if args else [p for p in self.primary_bodies if p.known_moons]
            if self.screen == "orbit" and args:
                parent = parents[0]
                if parent not in self.primary_bodies:
                    raise ValueError("Choose a planet, for example /moons jupiter.")
                children = satellites(parent.name)
                self.selected = parent
                self.orbit_focus = None
                self.system_filter = "moons"
                self.preview_missions = False
                self.view = parent.name.lower()
                if children:
                    self.orbit_notice = f"{parent.name}: {len(children)} included moon orbits / {parent.known_moons} known moons"
                elif parent.known_moons:
                    self.orbit_notice = f"{parent.name} has {parent.known_moons} known moons; none have orbits in this catalogue."
                else:
                    self.orbit_notice = f"{parent.name} has no moons."
                return self.orbit_notice+"\n\n"+self.text_map()
            result = ["MOON CATALOGUE / included profiles, not a complete census", ""]
            for parent in parents:
                children = satellites(parent.name)
                if parent.kind == "Natural satellite":
                    raise ValueError("Choose a planet, for example /moons saturn.")
                result += [f"{parent.name.upper()} / {parent.known_moons} known moons; {len(children)} included"]
                result += [f"  /{m.name.lower():<12} diameter {2*m.radius:>8,.1f} km   orbit {m.period:>9.4g} d   mass {m.mass:.3g} kg" for m in children]
                if not children:
                    result.append("  No moon profiles. The Sun is orbited by planets, not moons." if parent is SUN else
                                  f"  {parent.known_moons} known moons; no orbits included in this catalogue." if parent.known_moons else "  No moons.")
                result.append("")
            result.append("Open /charon for a moon profile. Try /moons pluto." if self.dwarf_mode else
                          "Open any profile: /europa, /titan, /triton. Try /view jupiter.")
            return "\n".join(result)
        if cmd == "search":
            if not args:
                raise ValueError("Usage: /search ocean")
            query = " ".join(args).lower()
            hits = [b for b in self.visible_bodies if query in " ".join((b.name, b.kind, b.parent or "", b.composition, b.atmosphere, b.features)).lower()]
            return f"SEARCH / {query}\n\n" + ("\n".join(f"  /{b.name.lower():<12} {b.kind} / {b.parent or 'star'}" for b in hits) or "No matches. Try ice, ocean, nitrogen or volcanic.")
        if cmd == "random":
            self.selected = random.choice(self.visible_bodies)
            return self.describe(self.selected)
        if cmd in ("compare", "distance"):
            if len(args) != 2:
                raise ValueError(f"Usage: /{cmd} earth mars")
            a, b = map(self.body, args)
            if any(isinstance(s,Spacecraft) and (s.planned or s.insertion>self.date.strftime('%Y-%m-%d')) for s in (a,b)):
                raise ValueError("This spacecraft is not a confirmed orbiter at this time; no present distance is available. Open its profile instead.")
            distance = math.dist(self.position(a),self.position(b))
            light_seconds = distance / 299792.458
            separation = (f"SEPARATION / {self.date:%Y-%m-%d %H:%M:%S} UTC\n"
                          f"  Center-to-center distance: {number(distance)} km ({distance/AU_KM:.6g} AU)\n"
                          f"  One-way light travel time: {light_seconds:,.3f} seconds ({light_seconds/60:,.3f} minutes)\n"
                          f"  {a.name}: {self.ephemeris.source(a,self.date)}\n"
                          f"  {b.name}: {self.ephemeris.source(b,self.date)}\n"
                          "  Geometric distance at this instant; light-time is distance / c.")
            if cmd == "distance":
                return f"{a.name.upper()} <> {b.name.upper()}\n\n" + separation
            rows = [("Mass (kg)", f"{a.mass:.5g}", f"{b.mass:.5g}"),
                    ("Diameter/span (km)", number(2*a.radius), number(2*b.radius)),
                    ("Density (kg/m^3)", "n/a" if isinstance(a,Spacecraft) else number(a.density), "n/a" if isinstance(b,Spacecraft) else number(b.density)),
                    ("Gravity (m/s^2)", "n/a" if isinstance(a,Spacecraft) else f"{a.gravity:.4g}", "n/a" if isinstance(b,Spacecraft) else f"{b.gravity:.4g}"),
                    ("Escape (km/s)", "n/a" if isinstance(a,Spacecraft) else f"{a.escape:.4g}", "n/a" if isinstance(b,Spacecraft) else f"{b.escape:.4g}"),
                    ("Orbit (days)", f"{a.period:,.5g}" if a.period else "n/a", f"{b.period:,.5g}" if b.period else "n/a"),
                    ("Known moons", str(a.known_moons) if a in PLANETS+DWARF_PLANETS else "n/a", str(b.known_moons) if b in PLANETS+DWARF_PLANETS else "n/a")]
            return f"COMPARE / {a.name.upper()} <> {b.name.upper()}\n\n" + separation + f"\n\n{'Property':<22}{a.name:>19}{b.name:>19}\n" + "\n".join(f"{k:<22}{x:>19}{y:>19}" for k,x,y in rows) + f"\n\n{a.name} has {a.mass/b.mass:.5g} times the mass and {a.radius/b.radius:.5g} times the diameter of {b.name}.\nGravity is a spherical estimate; uncertain masses carry into derived values.\n\n{a.name.upper()} / {a.kind}\n  Temperature: {a.temperature}\n  Composition: {a.composition}\n  Atmosphere: {a.atmosphere}\n  Features: {a.features}\n\n{b.name.upper()} / {b.kind}\n  Temperature: {b.temperature}\n  Composition: {b.composition}\n  Atmosphere: {b.atmosphere}\n  Features: {b.features}"
        if cmd == "weight":
            if len(args) != 2:
                raise ValueError("Usage: /weight 70 mars (mass in kilograms)")
            mass = float(args[0])
            if not math.isfinite(mass) or mass <= 0 or mass > 1e12:
                raise ValueError("Mass must be a finite positive number up to 1e12 kg.")
            body = self.body(args[1])
            if isinstance(body,Spacecraft):
                raise ValueError("Spacecraft have no model surface gravity. Choose a planet or moon for /weight.")
            force = mass * body.gravity
            result = (f"WEIGHT / {body.name}\n\n  Your mass remains {mass:g} kg.\n  Weight force: {number(force)} N\n"
                      f"  Earth-scale equivalent: {number(force / lookup('earth').gravity)} kg\n  Gravity: {body.gravity:.4g} m/s^2 (spherical estimate)")
            if body.kind in ("Gas giant", "Ice giant", "G2 V star"):
                result += "\n\n  Reference-radius calculation only: this body has no solid surface to stand on."
            if body.estimated_mass:
                result += "\n  This body's mass is estimated, so this result is uncertain."
            return result
        if cmd in ("view", "focus", "map", "orbit"):
            self.orbit_notice = ""
            if cmd != "map" or args:
                self.orbit_focus = None
                self.system_filter = "all"
                self.preview_missions = False
            target = " ".join(args).lower() if args else (self.view if cmd == "map" else "solar")
            if target in ("solar", "inner", "outer"):
                self.view = target
            else:
                body = self.body(target)
                self.selected = body
                if isinstance(body,Spacecraft):
                    if body.planned or body.insertion>self.date.strftime('%Y-%m-%d'):
                        return self.open_body(body)
                    self.orbit_focus = body
                self.view = body.parent.lower() if body.kind in ("Natural satellite","Artificial satellite") else ("solar" if body is SUN else body.name.lower())
            if cmd == "map":
                return self.text_map()
            self.screen = "orbit"
            return self.text_map() if cmd == "orbit" else f"ORBIT VIEW / {self.view}\n\n{self.status()}\n\nFull-screen orbit view opened. Esc or /back returns to the overview."
        if cmd in ("time", "pause", "resume", "now", "realtime", "reset", "speed", "step", "date"):
            if cmd == "pause":
                self.paused = True
            elif cmd == "resume":
                self.paused = False
            elif cmd == "reset":
                self.reset()
            elif cmd in ("now", "realtime"):
                self.set_date(datetime.now(UTC))
                self.clock_mode = "realtime"
                self.speed = 1 / 86400
                self.paused = False
            elif cmd in ("speed", "step", "date"):
                if len(args) != 1:
                    raise ValueError(f"Usage: /{cmd} " + ("2030-01-01" if cmd == "date" else "10"))
                if cmd == "date":
                    date = datetime.fromisoformat(args[0].replace("Z", "+00:00"))
                    self.set_date(date.replace(tzinfo=UTC) if date.tzinfo is None else date.astimezone(UTC))
                else:
                    value = float(args[0])
                    if not math.isfinite(value) or abs(value) > 1e6:
                        raise ValueError("Use a finite number from -1000000 to 1000000.")
                    if cmd == "step":
                        self.set_date(self.date + timedelta(days=value))
                    else:
                        self.speed = value
                        self.clock_mode = "simulation"
            return "SIMULATION CLOCK\n\n" + self.status() + "\n\nAt the date limits the simulation pauses automatically. /resume continues."
        if cmd == "scale":
            if args not in (["fit"], ["linear"]):
                raise ValueError("Usage: /scale fit or /scale linear")
            self.scale = args[0]
            return f"Map scale: {self.scale}. Symbols are enlarged in both modes."
        if cmd in ("labels", "trails"):
            if args not in (["on"], ["off"]):
                raise ValueError(f"Usage: /{cmd} on or /{cmd} off")
            setattr(self, cmd, args[0] == "on")
            return f"Map {cmd}: {args[0]}."
        if cmd == "export":
            if args:
                raise ValueError("Use /export without arguments. Snapshots go in exports/.")
            folder = ROOT / "exports"
            folder.mkdir(exist_ok=True)
            path = folder / f"solar-{datetime.now(UTC):%Y%m%d-%H%M%S-%f}.json"
            data = {"simulation_utc": self.date.isoformat(), "speed_days_per_second": self.speed,
                    "paused": self.paused, "view": self.view, "catalogue_checked": CATALOG_DATE,
                    "model": "JPL Horizons where cached and in range; otherwise Keplerian planets / illustrative moons and spacecraft; planned or not-yet-arrived spacecraft positions are null",
                    "bodies": [{"name": b.name, "parent": b.parent, "mass_kg": b.mass,
                                "kind": b.kind, "mission_status": getattr(b,'status',None),
                                "planned": getattr(b,'planned',False),
                                "mass_is_estimate": b.estimated_mass, "mean_radius_km": b.radius,
                                "position_source": self.ephemeris.source(b,self.date),
                                "heliocentric_position_km": None if isinstance(b,Spacecraft) and (b.planned or b.insertion>self.date.strftime('%Y-%m-%d')) else self.position(b)} for b in BODIES.values()]}
            if self.mission is not None:
                data['flight_replay']={'name':self.mission.flight.name,'stage':self.mission.stage.name,
                                      'elapsed_seconds':self.mission.elapsed,'duration_seconds':self.mission.duration,
                                      'complete':self.mission.complete,'geometry':'schematic; not a flight ephemeris'}
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            return f"Snapshot saved:\n{path}"
        close = difflib.get_close_matches(cmd, COMMANDS + list(BODIES), n=3, cutoff=.45)
        raise ValueError(f"Unknown command /{cmd}." + (" Try " + ", ".join('/' + n for n in close) + "." if close else ""))

    def map_system(self, view=None):
        if self.orbit_focus is not None and (view is None or view == self.view):
            return lookup(self.orbit_focus.parent), [self.orbit_focus]
        view = view or self.view
        if view in ("solar", "inner", "outer"):
            split = 1 if self.dwarf_mode else 4
            bodies = self.primary_bodies[:split] if view == "inner" else self.primary_bodies[split:] if view == "outer" else self.primary_bodies
            return SUN, bodies
        center = self.body(view)
        moons = satellites(center.name) if self.system_filter != "spacecraft" else []
        spacecraft = orbiters(center.name,self.date,self.preview_missions) if self.system_filter != "moons" else []
        return center, [*moons,*spacecraft]

    def map_cells(self, width, height, view=None):
        """Map cells contain (character, curses color, bold), ready for either renderer."""
        if self.camera.name!='system':return self.camera_cells(width,height)
        width, height = max(12, width), max(6, height)
        cells = [[(" ", 7, False) for _ in range(width)] for _ in range(height)]
        center, bodies = self.map_system(view)
        cx, cy = (width-1) / 2, (height-1) / 2
        # Approximate terminal glyph aspect ratio: one row is ~two columns high.
        radius = min((width-16) / 2, height-3)
        radius = max(2, radius)
        max_orbit = max((b.orbit*(1+b.eccentricity) for b in bodies), default=1)

        def put(x, y, text, color=7, bold=False):
            x, y = round(x), round(y)
            if 0 <= y < height:
                for offset, char in enumerate(text):
                    if 0 <= x + offset < width:
                        cells[y][x+offset] = (char, color, bold)

        def project(body, xyz, index):
            x,y,_ = xyz
            r = math.hypot(x,y)
            factor = radius / max_orbit
            if self.scale == "fit" and r:
                slot = radius * (.17 + .83 * (index+1) / max(1,len(bodies)))
                factor = slot / body.orbit
            return cx + x * factor, cy - y * factor * .5

        palette = (7,3,4,1,5,2,6,4,7)
        def identity(body,index):
            key = self.orbit_number(body,index+1)-1 if center is SUN else index
            return str(key+1),palette[key % len(palette)]

        if self.trails:
            for index, body in enumerate(bodies):
                marker,color = identity(body,index)
                orbit_point = self.orbit_path(body)
                for sample in range(240):
                    anomaly = sample / 240 * math.tau
                    xyz = orbit_point(anomaly)
                    x,y = project(body, xyz, index)
                    put(x, y, marker if sample % 60 == 0 else ".", color)
        # Stable faint stars, outside the orbital paths where possible.
        for x,y in ((2,1),(width-5,2),(5,height-3),(width-3,height-2)):
            if cells[y][x][0] == " ":
                put(x,y,"+",8)
        points = []
        for index, body in enumerate(bodies):
            xyz = self.position(body)
            if center is not SUN:
                xyz = tuple(a-b for a,b in zip(xyz,self.position(center)))
            x,y = project(body, xyz, index)
            points.append((x,y,body))
        if self.labels:
            reserved = {(round(x)+dx,round(y)) for x,y,_ in points for dx in (-1,0,1)} | {(round(cx),round(cy))}
            occupied = set(reserved)
            for index,(x,y,body) in enumerate(points):
                marker,color = identity(body,index)
                label = body.name
                for dx,dy in ((3,0),(3,-1),(3,1),(-len(label)-3,0),(-len(label)//2,2)):
                    lx,ly = round(x)+dx,round(y)+dy
                    area = {(lx+k,ly) for k in range(len(label))}
                    if 0<=ly<height and lx>=0 and lx+len(label)<width and not occupied.intersection(area):
                        put(lx,ly,label,color,True)
                        occupied.update(area)
                        break
        for index,(x,y,body) in enumerate(points):
            marker,color = identity(body,index)
            put(x-1,y,"["+marker+"]",color,True)
        put(cx,cy,"*" if center is SUN else "O",center.color,True)
        if not bodies:
            if self.system_filter == "spacecraft":
                message = "No confirmed current spacecraft orbiters in this catalogue."
            else:
                message = f"{center.name} has no moons." if not center.known_moons else f"{center.known_moons} known moons; no orbits included."
            put(max(0,cx-len(message)/2),min(height-1,cy+2),message,3,True)
        return cells

    @property
    def live_entries(self):
        rows,_,_,_=self.launches.snapshot()
        return tuple(r for r in rows if self.live_filter=='all' or self.live_filter in r.groups)

    def live_text(self):
        entries=self.live_entries
        selected=next((r for r in entries if r.id==self.live_selection),None)
        lines=['LIVE LAUNCH MONITOR / actual UTC, independent of simulation date',self.launches.label(),'']
        if selected:
            lines += [launch_detail(selected),'','/live returns to the list. /live watch NUMBER opens a supplied webcast.']
        else:
            active=sum(r.in_flight for r in entries)
            lines += [f'{active} reported IN FLIGHT / {len(entries)-active} scheduled or on hold',
                      'Upcoming matches are selected from the next 100 global launches.','']
            if not entries:
                lines.append('No matching launches in the fetched data.' if self.launches.updated else 'Waiting for the launch feed; /live status shows progress.')
            for i,launch in enumerate(entries,1):
                state='IN FLIGHT' if launch.in_flight else launch.status
                net=launch_date(launch.net)
                when=f'{net:%Y-%m-%d %H:%M} UTC' if net else 'Date TBD'
                lines += [f'{i}. {launch.name} - {launch.provider}',f'   [{state}] {when} / {countdown(launch)}']
            lines += ['',f'Source: {LAUNCH_SOURCE}',
                      '/live NUMBER details  /live watch NUMBER webcast  /live refresh',
                      '/live spacex | nasa | esa | all filters  /live exit returns',
                      'ESA includes European Ariane/Vega providers; actual operator is shown.',
                      'Status/countdown/webcast links only; no live spacecraft trajectory.']
        return '\n'.join(lines)

    @property
    def selected_launch(self):
        if self.overlay!='live':return None
        return next((r for r in self.live_entries if r.id==self.live_selection),None)

    @property
    def active_name(self):
        launch=self.selected_launch
        if launch:return launch.name+' / '+launch.rocket
        if self.mission:return self.mission.flight.vehicle+' / '+self.mission.flight.name
        return (self.orbit_focus or self.selected).name

    def body_framing(self):
        body=self.orbit_focus or self.selected
        radius=body.radius
        if isinstance(body,Spacecraft):radius=lookup(body.parent).radius
        children=[*satellites(body.name),*orbiters(body.name,self.date)]
        reach=max((b.orbit*(1+b.eccentricity) for b in children),default=0.)
        # A moon or catalogue spacecraft gets enough context to see its primary.
        if body.kind in ('Natural satellite','Artificial satellite'):
            reach=max(reach,body.orbit*(1+body.eccentricity))
        return self.camera.framing(radius,reach)

    @property
    def camera_label(self):
        if self.selected_launch:
            return self.camera.framing()[1].split(' / ')[0]+' / position unavailable'
        if self.mission:return self.camera.framing()[1]
        return self.body_framing()[1]

    def active_scene(self,width,height):
        if self.selected_launch or self.mission or self.camera.name!='system':
            return self.camera_cells(width,height)
        return self.map_cells(width,height)

    def camera_cells(self,width,height):
        launch=self.selected_launch
        if launch:
            # The feed provides launch status, not coordinates. This is an unlocated
            # identity marker, never a fabricated orbit or a different flight replay.
            width,height=max(12,width),max(6,height)
            cells=[[(' ',7,False) for _ in range(width)] for _ in range(height)]
            def put(y,x,text,color=7):
                for i,char in enumerate(text[:max(0,width-x)]):cells[y][x+i]=(char,color,True)
            put(0,1,self.camera_label,6)
            put(1,1,'Selected spacecraft',3)
            put(round((height-1)/2),round((width-1)/2),'>',3)
            put(min(height-3,round((height-1)/2)+1),1,launch.rocket,3)
            put(height-2,1,'Position unavailable',8)
            put(height-1,1,'No live position telemetry',8)
            return cells
        if self.mission:return self.mission.scene(width,height,self.camera)
        target=self.orbit_focus or self.selected
        reference=self.position(target)
        children=[*satellites(target.name),*orbiters(target.name,self.date)]
        parent=lookup(target.parent) if target.parent else None
        neighbors=([parent,*satellites(parent.name),*orbiters(parent.name,self.date)]
                   if parent and target.kind in ('Natural satellite','Artificial satellite') else [parent] if parent else [])
        # Target last, with its physical radius, regardless of the current map's system.
        unique={b.name:b for b in [*neighbors,*children,target] if b is not None}
        points=[];paths=[]
        for body in unique.values():
            if isinstance(body,Spacecraft) and (body.planned or body.insertion>self.date.strftime('%Y-%m-%d')):continue
            xyz=self.position(body)
            relative=tuple(a-b for a,b in zip(xyz,reference))
            points.append(Point(body.name,relative[0],relative[1],body.color,
                                '+' if isinstance(body,Spacecraft) else 'O' if body is target else 'o',
                                0 if isinstance(body,Spacecraft) else body.radius))
            if body is not SUN and self.trails:
                path=self.orbit_path(body)
                primary=self.position(lookup(body.parent))
                paths.append([(p[0]+primary[0]-reference[0],p[1]+primary[1]-reference[1])
                              for p in (path(i*math.tau/240) for i in range(241))])
        extent,label=self.body_framing()
        return render_camera(width,height,self.camera,points,paths,(0.,0.),extent,label)

    def text_map(self, width=88, height=25):
        cells = self.map_cells(width, height)
        if self.camera.name!='system':
            return ('CAMERA / '+self.camera_label+'\nFollowing: '+self.active_name+'\n'+self.status()+'\n\n'+
                    '\n'.join(''.join(c[0] for c in row) for row in cells)+
                    '\n\nTarget-centered kilometer scale; markers are enlarged. Positions use the simulation date.\n'
                    'Spacecraft are illustrative. /camera system restores numbered orbit maps.')
        legend = "\n".join(f"  [{self.orbit_number(b,index)}] {b.name:<12} {distance:>18,.0f} km from parent / {source}" for index,b,distance,source in self.position_rows())
        return f"ORBIT MAP / {self.view} / {self.scale} spacing / enlarged markers\n{self.status()}\n\n" + "\n".join("".join(c[0] for c in row) for row in cells) + "\n\nNUMBERED ORBITS / brackets mark current positions\n" + legend + "\n\nPaths: current-state osculating ellipses when JPL is available; offline ellipses otherwise. /orbit inner /orbit jupiter /back"
