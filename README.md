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

Mission playback jumps to the historical launch date and reaches return in the duration you choose. Use `/pause`, `/resume`, `/mission seek 50`, `/mission restart` and `/mission stop`. **Esc** returns to the overview. **Tab** completes commands and names. Mission animation requires full-screen mode; plain mode and `-c` show text snapshots.

Included flights: Apollo 8, 11, 13 and 17; Artemis I and II; SpaceX Demo-2 and Crew-1; Inspiration4; Polaris Dawn. Each follows its own stages, including landing, flyby, abort or ISS docking where appropriate.

## Data and accuracy

The app can retrieve current planetary and moon state vectors from NASA/JPL Horizons, with labeled offline fallbacks. It includes selected major moons and spacecraft rather than every satellite. Artificial-satellite positions and mission replay routes are illustrative, not live tracking. Historical replay milestones are rounded, some transitions are approximate, and time compression varies by stage. Solar days are approximate means rather than local daylight duration.

Internet access is optional. Cache and exported snapshots are stored inside the extracted folder, so keep it somewhere you can write to. Python 3.10+ and its standard library are the only runtime requirements. Full-screen mode uses curses, normally included with macOS/Linux Python.

See [README.txt](README.txt) for the full command guide and [SOURCES.txt](SOURCES.txt) for astronomy references.

## Development and releases

```sh
python3 -m unittest -v
python3 tools/build_release.py
```

The build command creates `dist/solar-sim.zip` and a SHA-256 checksum. The package includes launchers, documentation, source and tests; it excludes Git history, local caches and exports. Extract it before running. GitHub checks cover Python 3.10 and 3.14 on Linux plus Python 3.14 on macOS and Windows. Those remote checks run after this repository is uploaded.

For publishing instructions, see [GITHUB_SETUP.md](GITHUB_SETUP.md). Publishing a GitHub release triggers a workflow that tests, builds and attaches the ZIP and checksum. No repository has been published by the local preparation step.

No project license has been selected. The maintainer can add one using GitHub's license template before offering reuse under an open-source license.
