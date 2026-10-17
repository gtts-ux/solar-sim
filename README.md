# Solar Sim

A terminal solar-system explorer with numbered orbit maps, planet and moon profiles, dwarf planets, day lengths, spacecraft and ten historical mission animations.

## Download and start

Download **solar-sim.zip** from this repository's **Releases** page, then extract the whole ZIP. You can also use **Code → Download ZIP**. No Git installation, account or pip packages are needed to run it.

**Install [Python 3.10 or newer](https://www.python.org/downloads/) first.** Python is required and is not bundled in the download. On Windows, enable the Python installer's PATH option when offered.

| System | Start from the extracted folder | Interface |
| --- | --- | --- |
| macOS | Double-click `Start Solar Sim.command` | Full-screen animated terminal |
| Linux | Open a terminal in the folder and run `sh "Start Solar Sim.sh"` | Full-screen animated terminal when Python includes curses |
| Windows | Double-click `Start Solar Sim.bat` | Scrolling text commands and mission snapshots |

On macOS, if Finder will not launch the file, open Terminal in the extracted folder and run:

```sh
sh "Start Solar Sim.command"
```

You can always run the Python entry point directly:

```sh
python3 solar_sim.py
```

On Windows use `py -3 solar_sim.py --plain` or the included `.bat` launcher. Native Windows full-screen animation is not included; use macOS/Linux for the animated interface. No downloads or package installs happen in the launchers.

Use a terminal at least **64 columns × 22 rows**; about 120 × 40 is more comfortable. Run `python3 solar_sim.py --offline` to disable automatic JPL requests, or add `--plain` for text mode.

## Start with a short command

On macOS/Linux, run this once from the extracted app folder:

```sh
python3 install_commands.py
```

Open a **new terminal window**, then type either `solar-sim` or `sol-sim` from any directory. Both launch the same app; options such as `solar-sim --offline` and `sol-sim --plain` work too.

The installer creates user commands in `~/.local/bin` and adds that directory to zsh, bash or sh startup files. It needs no administrator access or extra packages. Existing shell settings are preserved. Keep the app folder in place; rerun the installer from its new location after moving it. `--bin-dir PATH --no-path` lets you manage the command directory and PATH yourself. Windows retains the `.bat` launcher.

## Try it

```text
/planet
/earth
/day mercury
/orbit
/moons jupiter
/iss
/compare earth titan
/dwarf
/dwarf exit
/time 1969/12/03
/time 1969/12/03 13:45
/mission list
/mission Apollo 11 1 minute
/mission Artemis II 30 seconds
/mission SpaceX Demo-2 1m 30s
```

In orbit mode, a body name focuses that body's orbit. `/moons jupiter` opens all included Jupiter moon orbits. Dwarf planets have a separate catalogue.

**Arrow navigation:** press **an arrow on an empty prompt**, **Tab**, **F2**, or type `/menu`. `/setting` opens the Settings menu directly. Use **Left/Right** to switch sections, **Up/Down** to select, and **Enter** to open. **Esc** goes back one level, then closes the menu; F2 closes it immediately. Browse planets, moons, spacecraft, dwarfs, historical missions, settings, clock controls and cached live launches. Choose a body, then its profile, orbit or other action. Theme and screensaver choices save immediately; the menu shows the saved choice. Page Up/Down and Home/End move through long lists. Browsing or cancelling preserves your view, camera and replay; actions take effect when you press Enter. Date entry and comparisons open a command ready for your values. The menu requires the full-screen macOS/Linux interface. Left/Right changes camera only in orbit view with empty input. Elsewhere arrows browse. Ctrl+P/N recalls history, Left/Right edits typed text, and Tab completes commands. In Settings, Enter applies themes or saves and previews screensavers; Space previews the saved animation.

**Set the clock:** `/time 1969/12/03 13:45` sets the simulation to exactly **1969-12-03 13:45 UTC** and pauses there. Omit the time for midnight. Orbit positions update and orbit mode stays open; setting a date during a mission ends that replay. `/resume` continues at the configured speed, `/now` returns to real time, and `/time` alone shows status. Supported years: 1800–2049.

**Five themes:** `/setting` lists Cosmic, Amber, Ocean, Forest and Mono. Use `/setting theme amber` or `/setting 2` to apply and save one immediately. The starfield follows the theme; Earth and Saturn retain their natural colors. `/setting exit` or Esc closes the panel without stopping a mission.

**Camera controls:** in orbit view, Left/Right on an empty prompt cycles **System → Close (10 km) → Body view → High orbit → Wide**. Every local zoom follows the active planet, moon or spacecraft. Body/high scales adapt to the body's radius; Wide includes its catalogued moon system. `/camera body`, `/camera wide` and `/camera system` select directly; `earth`/`moon` remain aliases. During a mission every zoom follows its spacecraft, including automatic framing, and stopping restores your previous body. Selecting `/live NUMBER` or `/live watch NUMBER` targets that launch's spacecraft; because the feed has no position telemetry, its preview clearly shows an unlocated marker instead of a fabricated trajectory or an unrelated replay. `/live exit` restores the prior target. Ctrl+B/F edits the command line; screensaver arrows change animation framing without changing the orbit camera. During missions or live views, use `/camera` to select zoom directly.

**Launch monitor:** `/live` fetches reported in-flight launches and upcoming NASA, SpaceX and ESA/European-related launches from [The Space Devs Launch Library 2](https://thespacedevs.com/llapi). The numbered list shows actual operator, source status and scheduled UTC. `/live 1` shows details; `/live watch 1` opens a supplied HTTPS webcast. Filter with `/live nasa`, `/live spacex` or `/live esa`; `/live all` restores all groups and `/live exit` returns. Arianespace/Avio/Ariane/Vega are included in the European group and retain their actual operator labels.

The monitor uses actual UTC even during a historical mission. Countdown passing zero never makes a launch "in flight" automatically. It provides status, countdowns and webcast links rather than spacecraft coordinates; the separate orbit/replay preview uses simulation data. Updates run in the background, normally at most once per 15 minutes to fit the public API quota. `/live refresh` respects that interval. Cached data retains its fetched timestamp; failures or stale data are marked unverified. Upcoming matches are selected from the next 100 global schedule entries. `/live` and `/sync` are explicit network requests even with `--offline`. In plain mode submit `/live` again to see a completed update; `-c '/live'` waits up to 30 seconds for its snapshot.

**Ten screensavers:** open `/setting` and choose **any of the eight planets**, **Milky Way** or **Black hole** (numbers **6–15**). Numbers 6–9 keep their original choices; 10–15 select Mercury, Venus, Mars, Jupiter, Uranus and Neptune. Use `/setting screensaver jupiter` (or any planet name), `/setting screensaver saturn`, `/setting screensaver black-hole` or `/setting screensaver milky-way`. Your choice saves locally. In Settings, choose **Screensavers**, use **Up/Down** to select, and press **Enter** to save and preview; **Space** previews the saved choice. **Enter again** or Esc returns. Outside menus, **Enter on an empty command line** also starts the saved animation. Mercury has cratered terrain, Venus has golden cloud swirls, Mars has rusty terrain and polar ice, Jupiter has belts and a red storm, Uranus spins sideways with pale cyan bands, and Neptune has blue bands, bright clouds and a dark storm. Earth rotates with stylized continents and drifting clouds, Saturn has shaded bands and tilted rings with proper overlap, and the black hole has thick, turbulent gas clouds with soft edges, curling wisps, uneven brightness, bent light and a dark center. Rotation uses elapsed time with cached geometry and targets 30 fps. Left/Right changes animation zoom. The simulation and mission pause while it is open. Colors adapt to the terminal; Mono and `--no-color` use dot shading. Planetary spin is accelerated for viewing; the textures are stylized. These artistic visualizations require no images, downloads or extra packages.

**Jupiter moon transits:** Io, Europa, Ganymede and Callisto pass in front of Jupiter and disappear behind it. Their shadows move across the curved cloud face with dark centers and soft edges. Moons are enlarged, orbit distances compressed and motion accelerated to make the animation visible in a terminal; their positions are illustrative. Choose `/setting screensaver jupiter`, then press Enter on an empty prompt.

Mission playback jumps to the historical launch date and reaches return in the duration you choose. Use `/pause`, `/resume`, `/mission seek 50`, `/mission restart` and `/mission stop`. **Esc** returns to the overview. **Tab** completes commands and names. Mission animation requires full-screen mode; plain mode and `-c` show text snapshots.

Included flights: Apollo 8, 11, 13 and 17; Artemis I and II; SpaceX Demo-2 and Crew-1; Inspiration4; Polaris Dawn. Each follows its own stages, including landing, flyby, abort or ISS docking where appropriate.

## Data and accuracy

The app can retrieve current planetary and moon state vectors from NASA/JPL Horizons, with labeled offline fallbacks. It includes selected major moons and spacecraft rather than every satellite. Artificial-satellite positions and mission replay routes are illustrative, not live tracking. Historical replay milestones are rounded, some transitions are approximate, and time compression varies by stage. Solar days are approximate means rather than local daylight duration.

Internet access is optional. Cache and exported snapshots are stored inside the extracted folder, so keep it somewhere you can write to. Python 3.10+ and its standard library are the only runtime requirements. Full-screen mode uses curses, normally included with macOS/Linux Python.

Local `settings.json` and `launch_cache.json` files are ignored by Git and omitted from downloads.

See [README.txt](README.txt) for the full command guide and [SOURCES.txt](SOURCES.txt) for astronomy references.

## Development and releases

```sh
python3 -m unittest -v
python3 tools/build_release.py
```

The build command creates `dist/solar-sim.zip` and a SHA-256 checksum. The package includes launchers, documentation, source and tests; it excludes Git history, local caches and exports. Extract it before running. GitHub checks cover Python 3.10 and 3.14 on Linux plus Python 3.14 on macOS and Windows. Those remote checks run after this repository is uploaded.

For publishing instructions, see [GITHUB_SETUP.md](GITHUB_SETUP.md). Pushing a version change on `main` triggers a workflow that tests, builds and publishes the release ZIP and checksum. The workflow can also run manually or attach assets to a release published through GitHub.

No project license has been selected. The maintainer can add one using GitHub's license template before offering reuse under an open-source license.
