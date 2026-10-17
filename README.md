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
/mission list
/mission Apollo 11 1 minute
/mission Artemis II 30 seconds
/mission SpaceX Demo-2 1m 30s
```

In orbit mode, a body name focuses that body's orbit. `/moons jupiter` opens all included Jupiter moon orbits. Dwarf planets have a separate catalogue.

**Five themes:** `/setting` lists Cosmic, Amber, Ocean, Forest and Mono. Use `/setting theme amber` or `/setting 2` to apply and save one immediately. The screensaver follows the theme. `/setting exit` or Esc closes the panel without stopping a mission.

**Camera controls:** Left/Right cycles **System → Close (10 km) → Body view → High orbit → Wide**. Every local zoom follows the active planet, moon or spacecraft. Body/high scales adapt to the body's radius; Wide includes its catalogued moon system. `/camera body`, `/camera wide` and `/camera system` select directly; `earth`/`moon` remain aliases. During a mission every zoom follows its spacecraft, including automatic framing, and stopping restores your previous body. Selecting `/live NUMBER` or `/live watch NUMBER` targets that launch's spacecraft; because the feed has no position telemetry, its preview clearly shows an unlocated marker instead of a fabricated trajectory or an unrelated replay. `/live exit` restores the prior target. Ctrl+B/F edits the command line; screensaver arrows change galaxy framing.

**Launch monitor:** `/live` fetches reported in-flight launches and upcoming NASA, SpaceX and ESA/European-related launches from [The Space Devs Launch Library 2](https://thespacedevs.com/llapi). The numbered list shows actual operator, source status and scheduled UTC. `/live 1` shows details; `/live watch 1` opens a supplied HTTPS webcast. Filter with `/live nasa`, `/live spacex` or `/live esa`; `/live all` restores all groups and `/live exit` returns. Arianespace/Avio/Ariane/Vega are included in the European group and retain their actual operator labels.

The monitor uses actual UTC even during a historical mission. Countdown passing zero never makes a launch "in flight" automatically. It provides status, countdowns and webcast links rather than spacecraft coordinates; the separate orbit/replay preview uses simulation data. Updates run in the background, normally at most once per 15 minutes to fit the public API quota. `/live refresh` respects that interval. Cached data retains its fetched timestamp; failures or stale data are marked unverified. Upcoming matches are selected from the next 100 global schedule entries. `/live` and `/sync` are explicit network requests even with `--offline`. In plain mode submit `/live` again to see a completed update; `-c '/live'` waits up to 30 seconds for its snapshot.

**Milky Way screensaver:** press **Enter on an empty command line** in full-screen mode. The whole interface disappears into a smoothly rotating galaxy with blue/violet spiral arms, a warm core and a subtle starfield. Press **Enter again** to return to the same view. The simulation and any mission playback pause while it is open, then resume their previous state. Esc also returns. Colors adapt to the terminal; `--no-color` stays monochrome. This artistic animation requires no extra packages and is not an astronomical galaxy model.

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
