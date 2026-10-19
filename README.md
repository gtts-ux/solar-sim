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

## Tutorial and updates

Run `sol-sim --tutorial` for the walkthrough, read [GETTING_STARTED.txt](GETTING_STARTED.txt), or use `/tutorial` inside the app. It covers setup, planets, orbits, themes, screensavers and missions. `sol-sim --version` shows your installed version.

Quit the app, then update from Terminal:

```sh
sol-sim -u
```

`solar-sim -u` and `--update` work too. The updater downloads the newest stable release ZIP from this repository, verifies its published SHA-256 checksum and checks startup before installing. It preserves settings, caches, exports, unrelated files and Git metadata. Previous app files are backed up in `update-backups/`; an installation failure restores replaced files. Start the new version with `sol-sim`. No account, Git installation, pip packages or administrator access is needed; internet and write access to the app folder are required.

The update applies to the folder your command launches. Git checkout users can use `git pull` instead; the ZIP updater changes app files without committing or changing Git history. Direct Python alternative: `python3 solar_sim.py --update` (Windows: `py -3 solar_sim.py --update`). Copies older than v1.6.0 need the latest ZIP once to gain this command. A version already current is left unchanged.

## Proxima Centauri mod

With v1.7.0 or newer, quit the app and run:

```sh
sol-sim -m"proxima centauri"
sol-sim
```

Then use `/proxima centauri` (or `/proxima centari`) inside the app. `/planet` lists Proxima d and b, `/star` opens the red dwarf, and `/orbit` displays their orbits. Try `/proxima b` and `/compare "proxima b" "proxima d"`. `/proxima exit` restores normal planets; `/dwarf` switches to dwarfs. The arrow menu has a **Mods** section.

The installer tries the separate `gtts-ux/proxima-centauri-mod` repository, then explicitly falls back to the bundled package if unavailable. `sol-sim --offline -m"proxima centauri"` installs without internet. Re-run `-m` to update the mod. Installed JSON data lives in `mods/`, is preserved by `sol-sim -u`, and is loaded without executing mod code.

These are illustrative local, star-centered orbits using published scales and periods; phases and planes are arbitrary, **not current observed positions**. Planet masses are RV minimum masses; radii are estimates. Days, atmospheres, composition and moons are unknown. Proxima c remains a candidate and is described by `/proxima c` without a simulated orbit. `/sources` in this mode gives the NASA and research references. Distances between the Solar and Proxima systems are not modeled. Alpha Centauri A/B are outside this local model.

## Interstellar mod

For the fictional system from *Interstellar* (2014), update to v1.8.0 or newer and run:

```sh
sol-sim -m"interstellar"
sol-sim
```

Inside the app, use `/interstellar`, `/planet`, `/orbit`, `/gargantua`, `/miller`, `/mann` and `/edmunds`. `/compare miller mann` shows profiles and the separation in the model; `/interstellar exit` restores normal planets. `/proxima centauri` switches to an installed Proxima mod, and `/dwarf` switches to dwarfs. The arrow menu includes Interstellar under **Mods**. In orbit mode Left/Right changes zoom; `/scale fit` spreads orbits for readability.

The package lives in [interstellar-mod](https://github.com/gtts-ux/interstellar-mod). The installer uses that repository first, with an identified bundled fallback; `--offline -m"interstellar"` installs without internet. Installed mods remain separate and survive app updates.

This is a **fictional schematic**, with film-inspired descriptions and explicitly invented planetary masses, radii, distances and animation cycles. The three worlds share a Gargantua-centered drawing frame; this does not establish their physical host-star arrangements. UTC controls animation; the map does not solve Kerr orbits, lensing or time dilation. The flat-space distance/c illustration is not a relativistic travel time. Unknown days, moons and atmospheric measurements are left unspecified. Screensaver selections are independent of this mod. `/sources` links the film and scientific background.

## Create and share mods

Anyone can publish a system catalogue without changing Solar Sim's code or joining a registry. Version **1.10.0+** installs community JSON from a local file, a public **GitHub owner/repository**, or a direct GitHub JSON link. Mods can add their own central star or black hole, planets, dwarfs and moons in a separate catalogue.

Read the complete [mod-making tutorial](MODDING.txt), use `sol-sim --mod-tutorial` in Terminal, or `/mod tutorial` in the app. From a new project folder:

```sh
sol-sim --mod-template solar-mod.json
# Edit the generated JSON in a plain-text editor.
sol-sim --check-mod solar-mod.json
sol-sim --offline -m "./solar-mod.json"
```

Then start the app and use `/mods`, `/mod aurora-system`, `/body Azure`, `/moons Azure`, `/orbit` and `/mod exit`. Change the template's `id` and other fields for your own system. The [editable example](solar-mod.json) includes two planets and a moon, with parent-relative eccentric and inclined orbits. Installed catalogues appear in the arrow menu under **Mods**. Type `/mods` to open the manager directly: use Up/Down and Enter to select a mod, then **Open system**, **Turn on/off** or **Uninstall**. Escape goes back. Off keeps files installed; switches persist across restarts and app updates. Turning off or uninstalling the viewed system returns to the Solar System. Commands: `/mods enable ID`, `/mods disable ID`, `/mods uninstall ID`.

To share, upload **solar-mod.json** to the **root of your own public GitHub repository** and give people `sol-sim -m "YOUR-NAME/YOUR-REPOSITORY"`. The installer uses that repository's default branch, copies only validated JSON and never executes repository code. No app pull request or manual registration is required. To try a working public example, `sol-sim -m "gtts-ux/solar-sim"` installs this repository's Aurora sample data catalogue.

For updates, increase the package version and repeat the original install command. Older packages do not downgrade a newer installed mod. App updates preserve `mods/`. The guide documents all fields, units, validation errors and removal. This format supports up to 64 bodies in a 64 KiB file; it adds data systems rather than custom Python plugins, images, screensavers or multi-star dynamics. Orbital positions use the author's local Keplerian elements, not automatic live ephemerides.

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

**Eleven screensavers:** open `/setting` and choose **any of the eight planets**, **Milky Way**, **Black hole** or **Moon view** (numbers **6–16**). Numbers 6–15 retain their existing choices; **16** selects Moon view. Use `/setting screensaver moon-view`, `/setting screensaver jupiter` (or any planet name), `/setting screensaver saturn`, `/setting screensaver black-hole` or `/setting screensaver milky-way`. Your choice saves locally. In Settings, choose **Screensavers**, use **Up/Down** to select, and press **Enter** to save and preview; **Space** previews the saved choice. **Enter again** or Esc returns. Outside menus, **Enter on an empty command line** also starts the saved animation. Mercury has cratered terrain, Venus has golden cloud swirls, Mars has rusty terrain and polar ice, Jupiter has belts and a red storm, Uranus spins sideways with pale cyan bands, and Neptune has blue bands, bright clouds and a dark storm. Earth rotates with stylized continents and drifting clouds, Saturn has shaded bands and tilted rings with proper overlap, and the black hole has thick, turbulent gas clouds with soft edges, curling wisps, uneven brightness, bent light and a dark center. Rotation uses elapsed time with cached geometry and targets 30 fps. Left/Right changes animation zoom. The simulation and mission pause while it is open. Colors adapt to the terminal; Mono and `--no-color` use dot shading. Planetary spin is accelerated for viewing; the textures are stylized. These artistic visualizations require no images, downloads or extra packages.

**Moon view:** watch a rotating blue Earth with continents and clouds above a cratered lunar horizon. Earth stays fixed in the sky as sunlight sweeps through full, half, crescent and new Earth over a smooth **96-second cycle**. The foreground changes illumination, with a faint earthlight effect during lunar night. Earth size, terrain and timing are composed for viewing; this is an artistic animation rather than a dated sky prediction. Select `/setting screensaver moon-view` (aliases `moon`, `lunar`, `earth from moon`) or settings choice **16**. It is built into the base app and needs no mod or network connection.

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
