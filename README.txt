SOLAR / SIM
A terminal observatory with current JPL positions and offline support
======================================================================

START / PORTABLE GITHUB COPY

Double-click "Start Solar Sim.command" in this folder. It opens Terminal
and runs the app. If Finder asks which app to use, select Terminal.

Or paste this in Terminal:

    cd /path/to/extracted/solar-sim
    python3 solar_sim.py

Requires Python 3.10 or newer, installed separately. No pip packages, account or API key needed. Current JPL data needs internet;
the offline approximation works without a connection.
On Windows the plain interface works with Python; full-screen mode
requires curses, normally included on macOS and Linux.

If double-clicking is blocked by macOS, use the Terminal command above.
For a basic terminal or screen reader:

    python3 solar_sim.py --plain

Disable colors with --no-color or the NO_COLOR environment variable.
For full-screen mode, use at least 64 columns by 22 rows. Around 120 by
40 shows a system overview, selected-body card and larger response panel.
/orbit opens the full-screen map. At 108+ columns, the solar view shows
inner and outer planets separately so all eight orbits are readable.

TERMINAL COMMANDS / macOS and Linux

Run this once from the app folder:

    python3 install_commands.py

Open a new terminal window. Both names start the same app from any folder:

    solar-sim
    sol-sim

Options work with either name, for example solar-sim --offline or
sol-sim --plain. The installer puts launchers in ~/.local/bin and adds
that directory to your zsh, bash or sh startup files. No sudo or packages
are needed. Existing shell settings and unrelated command files are kept.

Keep the app folder in place. After moving it, run the installer again
from the new folder to update both commands. Run it from the copy you
want the commands to open. Use --no-path to manage PATH yourself, or
--bin-dir /your/command/folder to choose another command directory.
Windows users can use the existing Start Solar Sim.bat launcher.

GETTING STARTED / UPDATING

    sol-sim --tutorial      Step-by-step setup and first commands
    sol-sim --version       Show the installed version
    sol-sim -u              Download and install the newest stable release

Read GETTING_STARTED.txt, or /tutorial inside the app, for the walkthrough.
Quit the app before updating, run sol-sim -u in Terminal, then start sol-sim.
solar-sim -u and --update work too. Direct Python: python3 solar_sim.py --update.
Windows: py -3 solar_sim.py --update. Internet and a writable app folder are needed.

Updates verify the published SHA-256 checksum and check the new app starts
before changing files. Settings, caches, exports, unrelated files and Git
metadata stay in place. Previous app files are saved in update-backups/;
failed installation restores replaced files. The command updates the folder
it launches. Git checkout users may prefer git pull; -u does not change Git
history. If -u is not recognized in an older copy, download the latest ZIP once.

FIRST THINGS TO TRY

    /planet
    /earth
    /sun
    /moons jupiter
    /europa
    /orbit jupiter
    /back
    /speed 0.2
    /pause
    /step 1
    /resume
    /view solar
    /compare earth titan
    /weight 70 mars
    /distance earth mars
    /day earth
    /mission list
    /mission Apollo 11 1 minute
    /info
    /help

Names are case-insensitive. /"Earth" works too. /planet earth and
/moon titan are alternate profile commands. Quotes around a multiword
alias work: /"the moon". /planets is an alias for /planet.

COMMAND REFERENCE

    /planet                 All eight planets, in solar order
    /planet NAME            Detailed planet profile
    /NAME                   Profile of any included body, e.g. /titan
    /moon NAME              Detailed moon profile
    /day [NAME]             Mean solar day and sidereal rotation
    /mission list           List ten historical flight replays
    /mission NAME DURATION  Full-screen launch-to-return animation
    /mission info NAME      Historical chronology, vehicle and references
    /mission pause          Pause a replay (/pause also works)
    /mission resume         Continue a replay (/resume also works)
    /mission seek PERCENT   Jump within playback, e.g. /mission seek 50
    /mission restart        Replay from launch with the same duration
    /mission status         Current stage, date and playback progress
    /mission stop           Stop replay; keep historical date paused
    /satellites [PLANET]     Selected spacecraft; orbit view when in orbit mode
    /iss /mro /juno          Spacecraft profile, or orbit focus in orbit mode
    /satellites mercury preview  Planned BepiColombo science orbits
    /moons [PLANET]         Included moon profiles, grouped by planet
                            In orbit mode: all included moon orbits together
                            /mooons is also accepted as an alias
    /dwarf                  Switch to the five dwarf planets
    /dwarf exit             Restore the normal eight-planet catalogue
    /search WORDS           Search names, features and composition
    /compare NAME NAME      Distance, light time, physical data and profiles
                            Quotes work: /compare "Earth" "Titan"
    /weight KG NAME         Weight force and Earth kg-scale equivalent
    /distance NAME NAME     Distance and one-way light travel time
    /random                 Random body profile

    /orbit [VIEW]           Full-screen orbits with numbered paths and legend
    /back                   Return to overview (Esc also works)
    /NAME in orbit mode     Focus that body's orbit around its parent
                            /earth shows Earth's orbit around the Sun
                            /europa shows Europa's orbit around Jupiter
                            /sun returns to the solar-system orbits
    /realtime               Follow actual UTC at 1x
    /sync                   Download JPL positions in the background
    /sync status            Progress and connection errors
    /view solar             All eight planets orbiting the Sun
    /view inner             Mercury, Venus, Earth and Mars
    /view outer             Jupiter, Saturn, Uranus and Neptune
    /view NAME              A planet and its included moons
    /focus NAME             Select a body and view its local system
    /map [VIEW]             Print a static terminal map
    /speed NUMBER           Earth days per real second; negative reverses
    /pause                  Freeze simulation time
    /resume                 Resume at the configured speed
    /step DAYS              Jump by a positive or negative number of days
    /date YYYY-MM-DD        Set simulation date in UTC
    /time YYYY/MM/DD        Set date at midnight UTC and pause
    /time YYYY/MM/DD HH:MM  Set exact UTC date/time and pause
    /time                   Current date, speed, view and pause state
    /now                    Follow current real time at 1x
    /reset                  Reset clock, speed, view and display settings
    /scale fit              Expanded spacing, all orbits easier to see
    /scale linear           True relative distances; inner orbits overlap
    /labels on|off          Show or hide orbiting-body names
    /trails on|off          Show or hide dotted orbit paths
    /export                 JSON snapshot in exports/ beside these files

    /info                   Model and data accuracy notes
    /tutorial               Getting started with sol-sim, controls and updates
    /menu                   Open full-screen arrow navigation (Tab empty or F2)
    /sources                Astronomy source links
    /help                   Command reference and keyboard shortcuts
    /clear                  Clear response panel
    /quit                   Exit; /exit also works

ISO date-times also work, e.g. /date 2030-01-01T12:00:00Z.
Use /time 1969/12/03 for 00:00 UTC, or /time 1969/12/03 13:45 for 13:45 UTC.
/time with a date pauses at that exact minute and updates the orbit positions.
It leaves orbit mode open; during a mission it stops the replay first.
/resume continues at the configured speed. /time alone shows clock status.
Valid simulation dates are 1800-01-01 through 2049-12-31 UTC.
At a boundary, time pauses automatically. /speed 0 also holds time.
The default clock follows the real UTC time at 1x. /speed, /date and /time DATE enter
simulation time. /now, /realtime or /reset returns to the actual time.

KEYBOARD

    Enter on empty input    Full-screen animation chosen in /setting
    Enter in screensaver    Return to exactly the previous view
    Tab on empty input / F2 Open the arrow navigation menu
    Tab while typing        Complete a command or a body name
    Up / Down               Browse menu items (empty input)
    Ctrl+P / Ctrl+N         Recall this session's command history
    Left / Right            Camera only in orbit view; otherwise menu navigation
    Ctrl+B / Ctrl+F         Move input cursor
    Home / End              Start / end of input (Ctrl+A / Ctrl+E too)
    Backspace / Delete      Edit input
    Ctrl+U                  Clear input
    Ctrl+K                  Delete input after the cursor
    Ctrl+L                  Redraw the screen
    Esc                     Leave orbit view or stop a mission replay
    Page Up / Page Down     Scroll response panel
    Ctrl+C / Ctrl+D         Exit cleanly

ARROW NAVIGATION (full-screen macOS/Linux)

Open with arrows on empty input, Tab, F2 or /menu. /setting opens the
Settings section directly. Left/Right changes section;
Up/Down selects an item; Enter opens or applies it. Esc goes back one level,
then closes the menu; F2 closes it immediately. Page Up/Down scrolls lists;
Home/End selects the first/last item. Press / to return to command entry.

Sections: Views, Planets, Moons, Spacecraft, Dwarfs, Missions, Settings,
Clock and Live. A body opens actions for its profile, orbit and other data.
Dwarfs stay separate; selecting a dwarf action enters its catalogue, and a
normal planet action returns to normal planets. Moon/spacecraft lists follow
the current catalogue. Missions offer 30-second, 1-minute and 5-minute runs.
Settings offers all themes, screensavers, animation preview and camera zoom.
Date/time and comparison items prepare a command for your typed values.
Live lists cached launches; open/refresh the feed to request current data,
then reopen the menu to select a launch with arrows.

Browsing/cancelling leaves your current view and replay running. Selecting
an action has the same effect as its slash command. Theme, screensaver,
pause/resume and speed changes keep the menu open; F2 returns to your view.
Outside the menu,
Left/Right changes camera only in orbit view with empty input. Elsewhere
arrows browse; Ctrl+P/N recalls history and Left/Right edits typed input. Enter on
an empty prompt still opens your screensaver. Plain mode uses slash commands.

On a MacBook, Page Up/Down is usually Fn+Up/Down. History is in memory
only. Resizing the terminal preserves the simulation and current input.
Profile responses capture their command-time values; the live map and
clock continue updating. Run the profile or comparison again for updated
coordinates and distance. The dashboard distances and orbit markers update live.
Plain mode updates time when a command is submitted; /map prints the
current frame. Full-screen mode animates continuously.

ONE-SHOT / SCRIPT USAGE

    python3 solar_sim.py -c /planet
    python3 solar_sim.py -c /earth
    python3 solar_sim.py -c "/date 2030-01-01" -c "/distance earth mars"
    python3 solar_sim.py -c "/view jupiter" -c /map

Repeat -c for sequential commands in one simulation. In this mode time
starts paused, making exports and scripted dates stable. /resume can
explicitly restart the clock. Standard input can also be piped in plain
mode. Full-screen mode does not run when output is redirected.

WHAT IS INCLUDED

    Sun
    Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune
    Earth: Moon
    Mars: Phobos, Deimos
    Jupiter: Amalthea, Io, Europa, Ganymede, Callisto
    Saturn: Mimas, Enceladus, Tethys, Dione, Rhea, Titan, Hyperion,
            Iapetus, Phoebe
    Uranus: Miranda, Ariel, Umbriel, Titania, Oberon
    Neptune: Proteus, Triton, Nereid

Separate dwarf catalogue: Ceres, Pluto, Haumea, Makemake and Eris.
Charon is included as Pluto's major moon. Other dwarf moons currently
have known counts but no simulated orbits in this catalogue.

Total: 40 natural bodies (including 26 selected moons), plus 16 spacecraft. Giant-planet known-moon
totals are larger than the selected profiles. Small irregular moons,
comets and asteroids are outside this simulation's scope.

Profiles include mass, mean radius/diameter, derived density, gravity,
escape speed, Earth comparisons, temperature, composition, atmosphere,
orbital period, orbital distances, eccentricity and rotation. Planet
profiles include axial tilt, rings and known/included moon lists.
The Sun profile uses a latitude-dependent rotation note. Hyperion has
chaotic rotation; Phoebe and Nereid have independent spin notes.

CURRENT POSITIONS AND ACCURACY

Interactive launches automatically request NASA/JPL Horizons data in a
background thread, one request at a time: eight planets, their 25 moons,
the five dwarf planets, and Charon.
No input blocks while syncing. /sync retries; /sync status reports errors.
Use --offline to disable automatic requests. One-shot -c commands avoid
automatic downloads; explicit -c /sync waits for the download to finish.

Data consists of heliocentric J2000 ecliptic geometric positions (km)
and velocities (km/s), sampled in UT every 15 minutes for about 26 hours.
Cubic Hermite interpolation evaluates current positions between samples.
Data is cached beside the app. It is never extrapolated beyond its time
window; missing or expired data uses the labeled offline model. In real
time mode the app checks for renewal, with a five-minute retry interval.
Sources are shown for each body: JPL, offline approximation or illustrative
moon orbit. A JPL moon marker uses its actual ephemeris, not an arbitrary
phase. Approximate moon positions are still explicitly labeled.

The full-screen map uses numbered colored paths and [number] markers for
current positions. Its legend identifies each body, parent distance and
source. Wide solar views separate inner/outer planets with independent
linear scales. /orbit inner, /orbit outer and /orbit jupiter zoom to
particular systems. /scale fit expands spacing; /scale linear preserves
distance ratios. Symbols are enlarged at every scale. Escape returns
to the overview. Opening a comparison also returns there.

While in orbit mode, a body name such as /earth, /titan or /"the moon"
stays in orbit mode and focuses that object's own orbit around its parent.
/planet earth and /moon europa work the same way in orbit mode. /sun
or /orbit solar returns to the whole solar system. /orbit jupiter still
shows Jupiter's full moon system. Outside orbit mode, body names open
their detailed information profiles. /compare returns to the overview.

/compare "Earth" "Moon" shows current center-to-center distance in km
and AU, one-way light time, both position sources, physical comparisons
and information about each body. /distance offers just the separation.
Distances use the same positions as the map at the printed timestamp;
light time is geometric distance / c, not an observer-corrected solution.

OFFLINE MODEL

This is an educational orbital simulation. It does not integrate N-body
gravity. Offline planets follow NASA/JPL approximate Keplerian elements with
rates, using a numerical solution of Kepler's equation and 3D ecliptic
coordinates. JPL Table 1 fits 1800-2050; this app limits dates to before
2050-01-01. The Earth-Moon barycenter is used for Earth's position.
The Sun stays at the origin; solar galactic motion is not simulated.
UTC substitutes for dynamical time. Light-time, observer position,
mutual perturbations beyond the fitted rates and relativistic effects
are not modeled. Coordinates are approximate, not telescope guidance.

Offline moons follow fixed ellipses with approximate real orbital distances,
eccentricities and periods. Starting phases and orbital planes are
illustrative, so these are not predictions of actual moon positions.
Triton and Phoebe orbit retrograde. No precession, tidal evolution,
eclipse/shadow, spin-surface or collision simulation is included.

Maps project positions from above the ecliptic. The optional fit scale
spreads orbits to improve readability; default linear scale uses distance
ratios. Bodies are always drawn as enlarged terminal symbols. /view
opens local moon systems so they remain visible. Markers are compact, with no globe graphics. Dotted trails are full orbit paths, not historical tracks. When both
body and parent JPL state vectors are available, each path is an
osculating ellipse computed from their relative position and velocity,
including the actual instantaneous orbital plane. It approximates the
current orbit; future gravitational perturbations are not integrated.

Mass means kilograms. Weight is gravitational force in newtons; the
weight calculator also gives an Earth-calibrated scale equivalent.
Spherical gravity, escape speed and density are derived from mass and
mean radius. Oblateness, latitude, rotation and altitude are omitted.
Giant planets and the Sun have no solid surface: their reference-radius
weight is only a mathematical comparison. Estimated moon masses carry
uncertainty into derived quantities. Proteus and Nereid are marked.

Planet radii are mean radii, not equatorial diameters from some tables.
Spin periods are sidereal; they differ from sunrise-to-sunrise days.
Negative spin values mean retrograde. Temperatures are representative
surface or atmospheric values, not time-dependent predictions.
Interior models and possible oceans are uncertain where indicated.

Moon counts checked 2026-10-16: Jupiter 115, Saturn 293, Uranus 29
(NASA August 2026 pages), Neptune 16. Discoveries and confirmations
change these totals. The offline catalogue never silently updates.
See SOURCES.txt for source links and provenance.

FILES

    Start Solar Sim.command   macOS launcher
    solar_sim.py              Terminal UI, plain mode, CLI entry point
    engine.py                 Clock, orbital math, maps, slash commands
    ephemeris.py              NASA/JPL download, cache and interpolation
    ephemeris_cache.json       Created after a successful JPL download
    catalog.py                Body data and JPL orbital coefficients
    missions.py               Spacecraft catalogue, status and mission profiles
    screensaver.py            Four animations and safe UI/clock restoration
    screensaver_scenes.py     Procedural Earth, Saturn and black hole
    themes.py                 Five themes and local preferences
    camera.py                 Shared orbit/replay camera scales
    live_launches.py          Background launch status and webcast links
    test_controls.py          Theme, camera and launch feed checks
    test_screensaver.py       Animation, preferences and view/clock checks
    flight_replay.py          Ten flight timelines, playback clock and routes
    day_lengths.py            Mean solar-day and sidereal-rotation calculations
    test_solar_sim.py         Regression tests for math and commands
    README.txt                This guide
    SOURCES.txt               Astronomy reference links
    exports/                  Created only when /export is used

RUN CHECKS

    python3 -m unittest -v test_solar_sim.py

TROUBLESHOOTING

If python3 is missing or older than 3.10, install current Python 3 from
https://www.python.org/downloads/ and reopen Terminal.
If full-screen graphics are garbled, try Terminal.app with a UTF-8
locale, enlarge the window, or use --plain. --no-color disables colors.
See README.md for macOS, Linux and Windows startup instructions.
The app reads its own settings, cache and project data. It uses NASA/JPL
Horizons for astronomy data and The Space Devs Launch Library 2 on /live.
--offline disables automatic JPL requests; /sync and /live explicitly
request network data. Cache and export files stay in
this folder. /export writes only into its exports directory. To remove the app,
delete this folder.

MOON SYSTEMS AND DWARF MODE

In orbit mode, /moons jupiter (or /mooons jupiter) opens the full system
of all included Jupiter moons. It works for every planet. The notice
states included orbits versus the known-moon total, since this catalogue
models major moons, not every small irregular satellite. Mercury and
Venus explicitly say they have no moons. /europa still focuses Europa's
own orbit; /moons jupiter expands back to the full included moon system.
Outside orbit mode, /moons continues to show the text catalogue.

/dwarf enters a separate catalogue containing Ceres, Pluto, Haumea,
Makemake and Eris. If already in orbit mode, it shows their orbits;
otherwise it lists them. Maps, lists, search, random picks, completion
and direct body commands follow the selected catalogue. Dwarfs do not
appear among the normal planets. /dwarf exit restores the eight regular
planets and the solar view. Enter /orbit after /dwarf for full-screen
orbits, or /pluto for its profile (its own orbit if already in orbit mode).

Charon is included for Pluto. /moons pluto shows its orbit and reports
that Pluto has five known moons but one included orbit. /moons ceres
says there are no moons. Haumea, Makemake and Eris report their known
moons and explain that their moon orbits are not yet in this catalogue;
they never incorrectly say those worlds have no moons.

New dwarf positions use JPL Horizons whenever data is available.
Offline dwarf sizes, periods and eccentricities are rounded physical
values, but their starting phases and orbital planes are illustrative.
They are explicitly labeled and should not be used as current-position
predictions. Haumea's radius is an approximate volume-equivalent value
for an elongated body. Makemake's mass is estimated. Pluto-Charon is
simplified to parent/child motion offline, rather than a full binary
barycentric model. Charon's offline phase/plane is illustrative too.

ARTIFICIAL SATELLITES / COMPACT MARKERS

The globe graphics have been removed. Orbit maps again use compact numbered
markers, with O for the central planet/moon and * for the Sun.

    /satellites                List the selected human-made spacecraft
    /satellites earth           ISS, Tiangong and Hubble
    /satellites mars            Seven selected Mars orbiters, including
                                inactive MAVEN with its status clearly marked
    /orbit                     Enter orbit mode, then use /satellites earth
    /iss                       Focus ISS around Earth when in orbit mode
    /mro                       Focus MRO around Mars when in orbit mode
    /orbit mars                Show Mars's moons and included spacecraft
    /moons mars                Show only Phobos and Deimos in orbit mode
    /satellites mercury        List upcoming BepiColombo MPO and Mio
    /satellites mercury preview Explicitly draw their planned science ellipses

For spacecraft motion at a convenient demonstration speed, try /speed 0.001.
/realtime returns to the real clock. /scale fit separates close orbit paths.
/satellite is also accepted as an alias for /satellites.

Included missions:
    Earth: ISS, Tiangong, Hubble
    Mars: Odyssey, MRO, MarsExpress, TGO, Hope, Tianwen1, MAVEN
    Venus: Akatsuki (inactive; mission terminated September 2025)
    Jupiter: Juno (orbiter; current operations not independently verified)
    Moon: LRO
    Ceres: Dawn (inactive, remains in orbit; requires /dwarf mode)
    Mercury: MPO and Mio (UPCOMING, not current orbiters)

This is a selected stations/science catalogue, not all thousands of Earth
satellites. It does not silently treat a flyby as an orbit: Voyager and
New Horizons are not added as planetary satellites. Cassini impacted Saturn
in 2017 and has no current orbit. Missions before their actual insertion
are not drawn as orbiters at that selected simulation date. Status values
are a catalogue snapshot checked 2026-10-16, not a live operations feed.

ESA schedules BepiColombo's joined MPO/Mio stack to enter Mercury orbit on
21 November 2026. Separation is planned for 9-10 December and science for
April 2027. The app lists both orbiters as upcoming. They are not drawn in
the current Mercury satellite view, even if a future simulation date is
selected; only an explicit preview shows the planned science ellipses.
Those ellipses are not the cruise trajectory or initial capture orbit.

Spacecraft positions are illustrative nominal ellipses with synthetic
starting phases and ascending nodes. Nominal inclination is included.
Periods are derived from those approximate ellipses. There is no live ISS
position feed, TLE/SGP4 propagation, drag, maneuvers or current mission
trajectory solution. Exact ISS visibility cannot be inferred from this
model. Old/inactive orbiters use representative past orbital parameters.

Mission profiles show approximate configuration-dependent mass/span,
agency, destination, status, nominal altitude range and source links.
Density, surface gravity and escape speed are not assigned to spacecraft
in the interface; /weight requires a natural body. Comparisons can include
spacecraft but their position/distance is explicitly illustrative. Upcoming
craft have no current comparison distance; exports give them null positions.
Planet and moon JPL ephemerides continue working as before.

DAY LENGTH

Every natural-body profile now includes its approximate mean solar day.
Use /day earth, /day mercury or /day moon for a fuller explanation.
/day with no name uses the selected body. Dwarf bodies follow the same
catalogue rule as other commands: use /dwarf before /day pluto.

A solar day is the average noon-to-noon cycle. Sidereal rotation is a spin
relative to distant stars. These can differ substantially: Mercury's solar
day is about 176 Earth days and Venus's is about 117 Earth days. The signed
spin and orbital periods determine the mean solar cycle. Moon estimates
use the parent world's year; retrograde rotation is accounted for. The
values omit eccentric-orbit, seasonal and obliquity effects. They do not
mean hours of daylight at a particular latitude. Hyperion's chaotic tumble
has no stable single period. The Sun has no solar day on itself. Spacecraft
have an orbital period rather than a planetary day.

HISTORICAL MISSION PLAYBACK

Restart the app to load this update. Run it normally, without --plain,
for animated full-screen mission playback. No downloads are required.

    /mission list
    /mission Apollo 11 1 minute
    /mission Apollo 13 30 seconds
    /mission "Artemis II" 1 minute
    /mission "SpaceX Demo-2" 1m 30s
    /mission Polaris Dawn 45 seconds

Quotes around mission names are optional. Names are case-insensitive;
Artemis 1, Artemis 2, Demo-2 and Crew-1 are accepted aliases. Omitting the
duration uses one minute. Durations support seconds, minutes and hours,
including combinations such as 1 minute 30 seconds, 1m30s or 1.5 minutes.
Choose between 1 second and 24 hours of active playback time.

Starting a mission sets the simulation clock to its historical launch UTC.
The screen shows a moving spacecraft marker, labeled Earth/Moon/ISS,
the historical UTC date, current stage, a progress bar and a timeline.
Compact markers are used; the removed planet globe graphics stay removed.
Apollo landings also show the command module remaining in lunar orbit.
Earth-only flights do not show a Moon journey.

Ten included flights:
    Apollo 11       First crewed landing, surface EVA, ascent and return
    Apollo 8        Lunar orbit and return, without landing
    Apollo 13       Accident, aborted landing, lunar flyby and recovery
    Apollo 17       Final Apollo landing, surface exploration and return
    Artemis I       Uncrewed Orion flybys and distant retrograde orbit
    Artemis II      Crewed April 2026 lunar flyby and return; no landing
    SpaceX Demo-2   Crew Dragon test flight, ISS docking and splashdown
    SpaceX Crew-1   Operational ISS crew rotation and return
    Inspiration4    Private Earth-orbit mission, without ISS docking
    Polaris Dawn    High Earth orbit, spacewalk operations and return

    /pause                    Freeze historical time and the animation
    /resume                   Continue using the remaining playback time
    /mission seek 50          Jump to 50 percent of the compressed playback
    /mission restart          Return to launch with the same duration
    /mission status           Show current stage and timing (/time also works)
    /mission info Apollo 11   Read the chronology and mission source links
    /mission stop             Stop, leaving historical time paused
    /now                      Return to today's actual time

The prefixed forms /mission pause and /mission resume also work. At the
requested runtime the spacecraft reaches splashdown and playback pauses
on the final stage. Pausing adds wall-clock time; seeking and restarting
change progress. After seeking backward from completion, use /resume.
Esc stops playback. Navigating to another view/profile or opening the
mission list/info also stops it and keeps the historical date paused.
/speed and /step require stopping a replay first. A new /mission NAME
command replaces the previous replay. /export includes replay metadata.
Tab completes mission names, including after /mission info.

Timelines use historical launch/return dates and rounded major milestones.
Some intermediate approach, coast, orbit-change and re-entry cues are
approximate; /mission info shows their descriptions. All displayed dates
are UTC, which can differ from the launch/landing site's local date.
Stage compression varies: long coasts or station stays are compressed more
strongly so launch, descent and other brief events remain visible. Seeking
50 percent means halfway through playback, not half the historical duration.
One-second replays work, but use 30 seconds or longer to read the stages.

Routes, orbital turns, spacecraft positions and body spacing are schematic,
not reconstructed mission trajectories or flight ephemerides. This is an
educational animation, without powered-flight dynamics, fuel modeling,
live tracking or trajectory integration. Mission playback has its own
clock and does not request historical spacecraft vectors from Horizons.
The normal planetary orbit view retains its existing position sources.

--plain is a text interface: it shows snapshots rather than an automatic
animation. Use /mission status after waiting to inspect elapsed progress,
or /mission seek PERCENT to inspect a stage. -c commands also print text
snapshots and exit immediately; they do not wait for a replay to finish.

    python3 solar_sim.py --offline -c '/day venus'
    python3 solar_sim.py --offline -c '/mission Apollo 11 1 minute' -c '/mission seek 47'

ANIMATED SCREENSAVERS

Open /setting to choose a screensaver and save it for the next start:

    /setting screensaver milky-way     Rotating spiral arms and warm core
    /setting screensaver earth         Shaded Earth, continents and clouds
    /setting screensaver saturn        Banded planet, shadow and tilted rings
    /setting screensaver black-hole    Dark shadow, turbulent clouds and wisps
    /setting screensaver mercury       Gray cratered terrain and bright rims
    /setting screensaver venus         Creamy golden cloud swirls
    /setting screensaver mars          Rusty terrain, dark markings, polar ice
    /setting screensaver jupiter       Banded clouds, red storm, moons and shadows
    /setting screensaver uranus        Pale cyan clouds and sideways rotation
    /setting screensaver neptune       Blue bands, dark storm, bright clouds
    /setting screensaver moon-view     Earth's phases above a cratered lunar horizon

Numbers 6-16 in the settings panel select the eleven animations; 1-5 still
choose themes. Existing numbers 6-9 keep their choices; 10-15 select
Mercury, Venus, Mars, Jupiter, Uranus and Neptune, respectively. Choice 16
selects Moon view. Spaces also work: /setting screensaver black hole.
The default is Milky Way. Existing theme preferences are preserved.

In full-screen mode, press Enter on a blank command line (spaces count as
blank). The whole interface disappears into the chosen animation against
a quiet starfield. Enter again returns to the same view, response, selection
and command history. Esc returns; Ctrl+C or Ctrl+D exits the app.
Left/Right changes animation zoom. Other keys are ignored.

The animations use a separate real-time clock and target 30 frames per
second, with Unicode braille for subcell detail and time-based rotation.
Cached geometry keeps rotation smooth; no per-frame random particles are
used. Earth has stylized geography, polar ice, drifting clouds and a blue
limb. Saturn's near rings cover the planet while its globe hides the far
rings; ring gaps and a cast shadow add depth. The black hole has a dark
center surrounded by thick, turbulent gas with soft, feathered edges.
Clouds curl at different speeds, with a brighter approaching side, a subtle
photon rim and a lensed glow. A cached procedural density volume replaces
the flat-looking disk; time-interpolated cloud shading keeps motion smooth.

256-color terminals get gradients; basic terminals get a simpler palette.
The new objects retain recognizable natural colors; the sky adapts to the
selected theme. Mono and --no-color include dot shading for texture.
The animation fits terminal resizes without interface overlays.

The simulation clock and any mission replay pause, including while the
animation initializes. Returning restores the earlier pause/resume state
without skipping mission stages.

Jupiter's screensaver also shows Io, Europa, Ganymede and Callisto orbiting
at different speeds. Moons cross the cloud face and disappear behind the
planet; their shadows follow the light direction across its curved surface,
with dark centers and soft edges. Moon sizes are enlarged, orbit distances
compressed and motion accelerated for visibility; this is an artistic
animation, not a display of current moon positions. Zoom with Left/Right.

Planet textures and feature placement are stylized. Their visual spin is
accelerated for viewing, independently of the simulation date and actual
planetary day lengths. The black hole is not a relativity solver.
Screensavers are available in the full-screen interface, not --plain or
one-shot -c output. No packages, images or downloads are needed.

THEMES, CAMERAS AND LIVE LAUNCHES

/setting lists Cosmic, Amber, Ocean, Forest and Mono. /setting theme amber
or /setting 2 applies and saves a theme immediately in settings.json.
It colors the interface and screensaver. --no-color and NO_COLOR override
colors. /setting exit or Esc returns without stopping a mission.

Left/Right changes camera only in orbit view with an empty prompt:
System (automatic overview), Close (10 km), Body view, High orbit, Wide.
Every local zoom centers the active planet, moon or spacecraft. Body and
High orbit scales grow with the selected body's radius; Wide includes its
outermost catalogued moon. The actual kilometer scale appears on screen.
/camera close, /camera body, /camera high, /camera wide or /camera system
selects directly. Old /camera earth and /camera moon remain aliases for
Body view and Wide; neither forces the target back to Earth.

During /mission the spacecraft is the active target at every zoom,
including automatic framing; stopping restores the previous selected body.
Selecting /live NUMBER or /live watch NUMBER makes that launch's spacecraft
the target. The feed has no position telemetry, so its preview shows an
unlocated spacecraft marker and "Position unavailable", not an invented
trajectory or an unrelated mission replay. /live exit restores the previous
target. Replay geometry is schematic; catalogue spacecraft orbits are
illustrative. Markers are enlarged, dotted limbs are size references.
Arrows on empty input browse the app outside orbit view. /setting opens
the arrow picker directly: choose Themes or Screensavers, Enter opens it,
Up/Down selects, and Enter applies a theme or saves/previews a screensaver.
Space previews the saved screensaver. Numeric shortcuts remain available.
Ctrl+P/N recalls history. Left/Right or Ctrl+B/F edits typed input.
During missions/live views, use /camera to select zoom directly.
Screensaver arrows zoom only the animation and preserve the orbit camera.

/live requests actual launch status from The Space Devs Launch Library 2.
Reported in-flight launches appear first, followed by matches from the
next 100 upcoming global records. NASA, SpaceX and ESA/European-related
launches are included; Arianespace/Avio/Ariane/Vega retain their actual
operator labels. In-flight results follow pagination separately.

    /live                   Open the numbered launch list
    /live 1                 Launch details, rocket, pad, NET and webcast links
    /live watch 1           Open a supplied HTTPS webcast in your browser
    /live spacex            Filter to SpaceX-related launches
    /live nasa              Filter to NASA-related launches
    /live esa               Filter to ESA/European-related launches
    /live all               Restore all included groups
    /live refresh           Refresh when the cache permits
    /live status            Cached data/progress without a new request
    /live exit              Restore the previous view

The feed uses actual UTC even during historical playback. Countdown zero
never fabricates liftoff: it says awaiting provider confirmation. The
monitor provides status, countdowns and links, not spacecraft telemetry
or live flight trajectories. The orbit/replay preview is separate.

The free provider budget is 15 requests/hour/IP. The app normally caches
for 15 minutes, with a rolling request budget and Retry-After handling.
/live refresh respects that interval. It shows fetched UTC and next refresh
time. Failed or stale updates retain cache and are labeled unverified.
No sample launches are substituted. launch_cache.json stores local data.

Live data needs internet. /live, like /sync, explicitly requests network
data even with --offline. The provider is not contacted until /live is
requested. Plain mode prints snapshots: submit /live again after the
background fetch finishes. -c '/live' waits up to 30 seconds for a snapshot.
settings.json and launch_cache.json are excluded from Git and ZIP builds.

PROXIMA CENTAURI MOD / v1.7.0
=============================

Install from Terminal after quitting the app:

    sol-sim -m"proxima centauri"
    sol-sim

Inside Solar Sim:

    /proxima centauri
    /planet
    /orbit
    /proxima b
    /compare "proxima b" "proxima d"
    /proxima exit

/proxima centari is also accepted. /star opens Proxima Centauri. The arrow
menu has a Mods section. /dwarf switches directly to the dwarf catalogue.
/proxima exit returns to normal planets. Each app copy installs its own mod.

The package includes the star and confirmed planets d and b. Proxima c is an
unconfirmed candidate (use /proxima c), excluded from orbits. This is a local
star-centered system with published sizes and periods, but arbitrary orbital
phases and planes, not observed current positions. Comparisons use this local
illustrative geometry; distances to Solar System objects are not modeled.
Radii are estimates, masses are RV minimum masses; planetary day lengths,
atmospheres, composition, rings and moon existence are unknown. There are no
confirmed moons or spacecraft included. Alpha Centauri A/B are not modeled.

The installer tries gtts-ux/proxima-centauri-mod, falling back to the bundled
package if unavailable; its message identifies the source. Use this to install
without a network request:

    sol-sim --offline -m"proxima centauri"

Only validated JSON data is loaded; no mod code runs. Installed data is in
mods/proxima-centauri.json. Re-run -m to update; sol-sim -u preserves mods/.
To uninstall, use /mods uninstall proxima-centauri. /sources in Proxima
mode lists references; see GETTING_STARTED.txt for the updated tutorial.

INTERSTELLAR MOD / v1.8.0
=========================

In Terminal (outside the app):

    sol-sim -m"interstellar"
    sol-sim

Inside Solar Sim:

    /interstellar
    /planet
    /orbit
    /scale fit
    /miller
    /mann
    /edmunds
    /gargantua
    /compare miller mann
    /interstellar exit

The Mods arrow menu includes Interstellar. Orbit-mode Left/Right zooms around
the selected body. /interstellar exit restores normal planets; /dwarf switches
to dwarfs; /proxima centauri opens an installed Proxima mod. Each catalogue
keeps its own coordinates; cross-system distances are not modeled.

This is a fictional film-inspired schematic. Planet masses, radii, orbital
radii and animation periods are invented placeholders, labeled in profiles
and exports. The model groups the three worlds around Gargantua for browsing,
without claiming a physical host-star arrangement. UTC animates the model;
Kerr orbits, time dilation, lensing and accretion physics are not integrated.
Miller's film time-dilation ratio is a story note. Distance/c is only a flat-
space illustration, not a relativistic travel time. Days, moons and detailed
atmospheric measurements are left unspecified. Screensavers are independent.

Repository: https://github.com/gtts-ux/interstellar-mod
The installer uses that repository, with a clearly identified bundled fallback.
Use sol-sim --offline -m"interstellar" to skip the network. Installed data lives
in mods/interstellar.json and survives sol-sim -u. Re-run -m to update it.
/sources in this mode lists the film and scientific background. See also the
updated GETTING_STARTED.txt tutorial.

MOON VIEW SCREENSAVER / v1.9.0
==============================

    /setting screensaver moon-view

Or choose Moon view under /setting > Screensavers (number 16). Enter saves
and previews it; Enter again returns. Outside the menu, Enter on an empty
prompt starts your saved animation. Left/Right adjusts animation zoom.

Stand on a stylized lunar surface with craters and a mountain horizon as
Earth rotates above it. Sunlight sweeps across continents and clouds through
full, half, crescent and new Earth over a smooth 96-second phase cycle.
Earth stays in one position above the horizon; the foreground changes light.
It works in color or monochrome and comes with the base app, without a mod.
Aliases: /setting screensaver moon, lunar, or earth from moon.

The terrain, Earth's apparent size, rotation and phase timing are artistic
and accelerated for viewing; this is not a prediction for the simulation date.
No images, additional packages or network connection are required. Settings
choices 1-15 keep their previous meanings. Existing preferences are preserved.

CREATE AND SHARE COMMUNITY MODS / v1.10.0
========================================

Anyone can publish a separate system catalogue without changing Solar Sim's
code or being added to a central registry. From a new project folder:

    sol-sim --mod-template solar-mod.json

Edit that file in a plain-text editor, then validate and install it:

    sol-sim --check-mod solar-mod.json
    sol-sim --offline -m "./solar-mod.json"

Inside the app, /mods lists installed packages. The unchanged example opens
with /mod aurora-system. Try /body Azure, /moons Azure and /body Lumen in
orbit mode. /mod exit restores normal planets. Installed community systems
also appear under Mods in the arrow menu.

To share a mod, put solar-mod.json at the root of your own public GitHub
repository. Anyone can install it with:

    sol-sim -m "YOUR-NAME/YOUR-REPOSITORY"

The default branch is used. Direct GitHub JSON links and local JSON files
work too. Repeating the original install command updates a package; older
versions do not downgrade newer installed data. App updates preserve mods/.
For a live public example: sol-sim -m "gtts-ux/solar-sim" installs Aurora data.

The complete beginner tutorial is MODDING.txt. Read it with:

    sol-sim --mod-tutorial

Or use /mod tutorial in the app. It explains every field, unit, orbit angle,
parent relationship, validation message, version update and removal step.
Format 2 supports one central star/black hole, planets, dwarfs and moons;
64 bodies and 64 KiB maximum. Mods are validated data; no repository code is
executed. Custom Python, mission/screen-saver code and multiple central stars
are outside this format. Keep original mod projects outside the app folder.

MODS MANAGER / v1.11.0
=====================

Type /mods to open the Mods section with immediate arrow focus, like
/setting. Use Up/Down to select a mod, Enter for its actions, and Escape
to go back. Left/Right switches menu sections. Each installed mod shows
ON/OFF, version and whether you are viewing it.

Open system views an enabled catalogue. Turn off keeps it installed but
blocks its activation commands; Turn on makes it available again.
Uninstall removes only its installed JSON package and switch preference.
Your source projects and other mods are kept. Invalid packages can also
be removed here. If you turn off or uninstall the viewed system, you
return to the Solar System.

Commands work too (use the mod ID listed by /mods):
    /mods enable proxima-centauri
    /mods disable proxima-centauri
    /mods uninstall proxima-centauri

States are saved in mods/.state.json separately for each app copy.
App updates preserve them. Updating an installed mod keeps its switch
state; reinstalling after uninstall starts ON. Only one catalogue is
viewed at a time; ON means available, not combined with other systems.
Install/reinstall in Terminal: sol-sim -m "proxima centauri"
