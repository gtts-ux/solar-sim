#!/usr/bin/env python3
"""Solar Sim: a dependency-free terminal observatory with JPL and offline positions."""
import argparse
import locale
import os
import sys
import textwrap

from catalog import AU_KM, BODIES, DWARF_PLANETS, MOONS, PLANETS, SUN, lookup, satellites
from engine import COMMANDS, Simulation
from missions import SPACECRAFT, Spacecraft
from day_lengths import day_label
from flight_replay import FLIGHTS

WELCOME = f"""WELCOME TO YOUR OBSERVATORY

One star. Eight planets. /dwarf opens five more worlds in a separate mode.

Type /planet to begin, /earth for a detailed profile, or /help for all commands.
Explore the giants with /moons jupiter and /view saturn.

The clock follows the actual current UTC time. /orbit opens full-screen orbits.
Use /speed 3 to accelerate, /realtime to return to now, /sync status for JPL data.
Tab completes commands; Up/Down recall history; Page Up/Down scroll results.

JPL Horizons positions download in the background; offline fallbacks are labeled.
Try /day earth or /mission Apollo 11 1 minute for a timed historical flight.
"""


def completions(line, sim=None):
    """Complete commands and bodies, retaining a slash on direct body commands."""
    if not line.startswith("/"):
        return []
    if line.startswith('/mission '):
        tail=line[len('/mission '):]
        prefix='/mission '
        if tail.startswith('info '):
            prefix+="info "
            tail=tail[5:]
        quote='"' if tail.startswith('"') else ''
        fragment=tail.strip('"').lower()
        choices=[f.name for f in FLIGHTS]
        if prefix=='/mission ':
            choices+=['list','info','pause','resume','restart','stop','status','seek']
        return [prefix+quote+choice+quote for choice in choices if choice.lower().startswith(fragment)]
    bodies = [body.name.lower() for body in (sim.visible_bodies if sim else
              [SUN,*PLANETS,*[m for m in MOONS if lookup(m.parent) in PLANETS],
               *[s for s in SPACECRAFT if s.parent!='Ceres']])]
    if " " not in line:
        return sorted({"/" + word for word in COMMANDS + bodies if ("/"+word).startswith(line.lower())})
    prefix, _, fragment = line.rpartition(" ")
    command = line.split()[0].lower()
    choices = bodies
    if command in ("/scale",):
        choices = ["fit", "linear"]
    elif command in ("/labels", "/trails"):
        choices = ["on", "off"]
    elif command in ("/view", "/map", "/focus", "/orbit"):
        choices += ["solar", "inner", "outer"]
    elif command == "/sync":
        choices = ["status"]
    elif command == "/dwarf":
        choices = ["exit"]
    elif command in ("/satellites","/satellite"):
        choices = [name for name in bodies if not isinstance(lookup(name),Spacecraft)]
        if prefix.count(" ") >= 1:
            choices = ["preview"]
    return [prefix + " " + name for name in sorted(choices) if name.startswith(fragment.lower())]


def wrap_lines(text, width):
    rows = []
    for line in text.splitlines():
        if not line:
            rows.append("")
            continue
        indent = len(line) - len(line.lstrip())
        rows.extend(textwrap.wrap(line, width=max(10,width), subsequent_indent=" "*min(indent+2,10),
                                  replace_whitespace=False, drop_whitespace=True) or [""])
    return rows


def plain_mode(sim, color):
    cyan, dim, reset = ("\033[96m", "\033[2m", "\033[0m") if color else ("", "", "")
    print(f"\n{cyan}  S O L A R  /  S I M{reset}\n{dim}  terminal observatory | real UTC clock | /help{reset}\n")
    print(WELCOME)
    try:
        import readline
        readline.set_completer_delims("\n")
        readline.set_completer(lambda line, index: (completions(line,sim)+[None])[index] if index <= len(completions(line,sim)) else None)
        if "libedit" in (readline.__doc__ or ""):
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
    except ImportError:
        pass
    while sim.running:
        try:
            raw = input(f"{cyan}solar > {reset}")
        except (EOFError, KeyboardInterrupt):
            print("\nObservatory closed. Clear skies!")
            break
        result = sim.command(raw)
        print(f"\n{result}\n")


def tui(screen, sim, no_color=False):
    import curses
    screen.keypad(True)
    screen.timeout(60)
    try:
        curses.set_escdelay(25)
    except AttributeError:
        pass
    colors = False
    if not no_color and curses.has_colors():
        curses.start_color()
        try:
            curses.use_default_colors()
            background = -1
        except curses.error:
            background = curses.COLOR_BLACK
        for index in range(1,8):
            curses.init_pair(index, index, background)
        curses.init_pair(8, curses.COLOR_WHITE, background)
        colors = True

    def attr(color=7, bold=False):
        style = curses.color_pair(color) if colors else 0
        if color == 8:
            style |= curses.A_DIM
        if bold:
            style |= curses.A_BOLD
        return style

    def write(y,x,text,color=7,bold=False):
        h,w = screen.getmaxyx()
        if 0 <= y < h and 0 <= x < w-1:
            try:
                screen.addnstr(y,x,str(text),w-x-1,attr(color,bold))
            except curses.error:
                pass

    def rule(y,label=""):
        _,w = screen.getmaxyx()
        write(y,1,"─"*(w-3),8)
        if label:
            write(y,3," " + label + " ",6,True)

    def draw_orbits(h,w):
        rows = sim.position_rows()
        legend_rows = (len(rows)+1)//2
        legend_start = h-5-max(1,legend_rows)
        map_height = max(6,legend_start-6)
        title = (sim.orbit_focus.name + " AROUND " + sim.orbit_focus.parent).upper() if sim.orbit_focus else sim.view.upper()
        if sim.dwarf_mode:
            title = "DWARFS / " + title
        write(3,2,"ORBIT / " + title,6,True)
        if sim.orbit_focus is None:
            write(3,27,"[number] = body / numbers on paths identify orbits",8)
        panes = [(2,w-4,sim.view)]
        if sim.view == "solar" and w >= 108:
            pane_width = (w-6)//2
            panes = [(2,pane_width,"inner"),(pane_width+4,pane_width,"outer")]
        for x,width,view in panes:
            pane_title = ("CERES" if view=="inner" else "OUTER DWARFS") if sim.dwarf_mode and view in ("inner","outer") else ("INNER PLANETS" if view=="inner" else "OUTER PLANETS" if view=="outer" else sim.view.upper())
            write(4,x,pane_title+f" / {sim.scale} scale",6,True)
            cells = sim.map_cells(width,map_height,view=view)
            for y,row in enumerate(cells):
                for dx,(char,color,bold) in enumerate(row):
                    if char != " ":
                        write(5+y,x+dx,char,color,bold)
        palette = (7,3,4,1,5,2,6,4,7)
        for index,(_,body,distance,source) in enumerate(rows):
            column = index//max(1,legend_rows)
            y = legend_start+index%max(1,legend_rows)
            x = 2+column*(w//2)
            marker = sim.orbit_number(body,index+1)
            distance_text = f"{distance/AU_KM:.3f} AU" if body.parent == "Sun" else f"{distance:,.0f} km"
            source_text = "JPL" if source.startswith("JPL") else "approx"
            write(y,x,f"[{marker}] {body.name:<10} {distance_text:>13} {source_text}",palette[(marker-1)%len(palette)],True)
        hint = "/dwarf exit normal planets · /satellites ceres · /moons pluto" if sim.dwarf_mode else "/iss focus ISS · /satellites mars spacecraft · /moons jupiter moons · Esc overview"
        write(h-5,2,sim.orbit_notice or hint,3 if sim.orbit_notice else 8)

    def draw_mission(h,w):
        replay=sim.mission
        stage=replay.stage
        status='COMPLETE' if replay.complete else 'PAUSED' if sim.paused else 'PLAYING'
        write(3,2,'MISSION / '+replay.flight.name.upper(),6,True)
        write(3,max(34,w-30),f'{status}  {replay.elapsed:.1f}/{replay.duration:g}s',3,True)
        write(4,2,replay.flight.vehicle+' / '+replay.flight.operator,8)
        write(5,2,f'STAGE {replay.index+1}/{len(replay.flight.stages)} / '+stage.name.upper(),3,True)
        write(6,2,stage.note,7)
        bar_width=max(8,w-22)
        done=min(bar_width,round(bar_width*replay.elapsed/replay.duration))
        write(7,2,'['+'='*done+'-'*(bar_width-done)+']',6)
        write(7,bar_width+6,f'{100*replay.elapsed/replay.duration:5.1f}%',7)
        scene_height=max(6,min(14,h-23))
        for y,row in enumerate(replay.scene(w-4,scene_height)):
            for x,(char,color,bold) in enumerate(row):
                if char!=' ':
                    write(9+y,2+x,char,color,bold)
        start=10+scene_height
        available=max(0,h-7-start)
        first=max(0,min(replay.index-2,len(replay.flight.stages)-available))
        for offset,event in enumerate(replay.flight.stages[first:first+available]):
            i=first+offset
            marker='>' if i==replay.index else '+' if i<replay.index else ' '
            write(start+offset,3,f'{marker} {event.date:%m-%d %H:%M}  {event.name}',3 if i==replay.index else 8,i==replay.index)
        write(h-7,2,'> spacecraft   O Earth   o Moon   c command module   + ISS',8)
        write(h-6,2,'Schematic route; rounded/approximate cues; stage timing adjusted to keep events visible.',8)
        write(h-5,2,'/pause /resume · /mission seek 50 · /mission restart · Esc /mission stop',8)

    response = WELCOME
    command = ""
    cursor = 0
    history = []
    history_index = 0
    draft = ""
    scroll = 0
    while sim.running:
        sim.tick()
        screen.erase()
        h,w = screen.getmaxyx()
        if h < 22 or w < 64:
            write(0,1,"SOLAR / SIM",6,True)
            write(2,1,"Resize to at least 64 columns x 22 rows.")
            write(3,1,"Or restart with: python3 solar_sim.py --plain",8)
            write(h-2,1,"> " + command)
            response_height = 1
            wrapped = [response]
            try:
                curses.curs_set(0)
            except curses.error:
                pass
        else:
            write(0,2,"S O L A R  /  S I M",6,True)
            write(0,27,"TERMINAL OBSERVATORY",8)
            state = "PAUSED" if sim.paused else "FLIGHT" if sim.mission else "NOW" if sim.clock_mode == "realtime" else "SIM"
            write(0,max(50,w-19),f"● {state}   /help",3 if sim.paused else 2,True)
            write(1,2,f"{sim.date:%Y-%m-%d %H:%M:%S} UTC",7)
            rate = "REAL TIME / 1x" if sim.clock_mode == "realtime" else f"{sim.speed:g} days/sec"
            write(1,30,f"Historical replay / {sim.mission.flight.name}" if sim.mission else f"{rate}  ·  {sim.ephemeris.message}",8)
            rule(2)

            # Overview replaces the former miniature orbit map.
            map_end = min(24,max(11,h//2 + 1))
            split = w-34 if w >= 108 else w
            center, bodies = sim.map_system()
            write(3,2,f"{center.name.upper()} / {'DWARF ' if sim.dwarf_mode else ''}LIVE SYSTEM OVERVIEW",6,True)
            write(5,3,"BODY          DISTANCE FROM PARENT       POSITION SOURCE",8)
            for index,(_,body,distance,source) in enumerate(sim.position_rows()[:max(1,map_end-8)]):
                short_source = "JPL Horizons" if source.startswith("JPL") else "approximate" if body in PLANETS else "illustrative"
                write(7+index,3,f"{body.name:<12} {distance:>17,.0f} km   {short_source}",body.color)
            if split != w:
                for y in range(3,map_end):
                    write(y,split,"│",8)
                b = sim.selected
                write(3,split+2,"SELECTED / " + b.name.upper(),b.color,True)
                if isinstance(b,Spacecraft):
                    card = [b.kind,"",f"Parent     {b.parent}",f"Agency     {b.agency}",
                            f"Mass       ~{b.mass:,.0f} kg",f"Span       ~{b.radius*2000:g} m",
                            "", "Nominal illustrative orbit", "Not live spacecraft tracking"]
                else:
                    card = [b.kind, "", f"Diameter   {2*b.radius:,.1f} km", f"Mass       {b.mass:.4g} kg",
                            f"Gravity    {b.gravity:.3g} m/s²", f"Parent     {b.parent or '—'}",
                            'Solar day  '+day_label(b)]
                if b.kind not in ("Natural satellite","Artificial satellite") and b is not lookup("sun"):
                    card += [f"Moons      {b.known_moons} known", f"Profiles   {len(satellites(b.name))} included"]
                elif b.period:
                    card += [f"Orbit      {b.period:.4g} days"]
                card += ["", f"/{b.name.lower()}", f"/view {b.name.lower()}"]
                for i,line in enumerate(card[:map_end-5]):
                    write(5+i,split+2,line,8 if line.startswith("/") else 7)
            write(map_end-1,2,"/orbit full-screen orbits · /compare earth mars · /sync status",8)
            rule(map_end,"RESPONSE")
            response_height = h-map_end-6
            wrapped = wrap_lines(response,w-6)
            scroll = min(max(0,scroll),max(0,len(wrapped)-response_height))
            for i,line in enumerate(wrapped[scroll:scroll+response_height]):
                title = bool(line and not line.startswith(" ") and line.upper() == line)
                write(map_end+1+i,3,line,6 if title else 7,title)
            if len(wrapped) > response_height:
                write(h-5,3,f"{scroll+1}–{min(scroll+response_height,len(wrapped))} of {len(wrapped)} lines · Page Up / Page Down",8)
            else:
                write(h-5,3,"/planet   /earth   /moons saturn   /compare earth mars   /help",8)
            if sim.screen == "orbit":
                # Give all space above the prompt to orbits and their legend.
                for y in range(3,h-4):
                    write(y,0," "*(w-1))
                draw_orbits(h,w)
            elif sim.screen == 'mission' and sim.mission is not None:
                for y in range(3,h-4):
                    write(y,0,' '*(w-1))
                draw_mission(h,w)
            rule(h-4)
            write(h-3,2,"›",6,True)
            available = w-8
            start = max(0,cursor-available+1)
            write(h-3,4,command[start:start+available])
            if not command:
                write(h-3,4,"Type a slash command…",8)
            write(h-2,2,"TAB complete  ↑↓ history  PgUp/PgDn scroll  Esc overview  Ctrl+C exit",8)
            try:
                curses.curs_set(1)
                screen.move(h-3,4+cursor-start)
            except curses.error:
                pass
        screen.noutrefresh()
        curses.doupdate()
        try:
            key = screen.get_wch()
        except curses.error:
            continue
        if key in ("\x03","\x04"):
            sim.running = False
        elif key == "\x1b":
            sim.stop_mission()
            sim.screen = "dashboard"
            sim.orbit_focus = None
            sim.preview_missions = False
        elif key in ("\n","\r",curses.KEY_ENTER):
            if command.strip():
                history.append(command)
                history = history[-300:]
                response = sim.command(command)
                scroll = 0
            command, cursor, draft = "",0,""
            history_index = len(history)
        elif key in (curses.KEY_BACKSPACE,"\x7f","\b"):
            if cursor:
                command = command[:cursor-1]+command[cursor:]
                cursor -= 1
        elif key == curses.KEY_DC:
            command = command[:cursor]+command[cursor+1:]
        elif key == curses.KEY_LEFT:
            cursor = max(0,cursor-1)
        elif key == curses.KEY_RIGHT:
            cursor = min(len(command),cursor+1)
        elif key in (curses.KEY_HOME,"\x01"):
            cursor = 0
        elif key in (curses.KEY_END,"\x05"):
            cursor = len(command)
        elif key == "\x15":
            command,cursor = "",0
        elif key == "\x0c":
            screen.clear()
        elif key == "\x0b":
            command = command[:cursor]
        elif key == curses.KEY_UP:
            if history:
                if history_index == len(history):
                    draft = command
                history_index = max(0,history_index-1)
                command = history[history_index]
                cursor = len(command)
        elif key == curses.KEY_DOWN:
            history_index = min(len(history),history_index+1)
            command = history[history_index] if history_index < len(history) else draft
            cursor = len(command)
        elif key == curses.KEY_PPAGE:
            scroll = max(0,scroll-max(1,response_height-1))
        elif key == curses.KEY_NPAGE:
            scroll = min(max(0,len(wrapped)-response_height),scroll+max(1,response_height-1))
        elif key == "\t":
            matches = completions(command[:cursor],sim)
            if matches:
                prefix = os.path.commonprefix(matches)
                command = prefix + command[cursor:]
                cursor = len(prefix)
                if len(matches) > 1:
                    response = "COMPLETIONS\n\n"+"\n".join("  "+item for item in matches)
                    scroll = 0
        elif isinstance(key,str) and key.isprintable() and len(command) < 1000:
            command = command[:cursor]+key+command[cursor:]
            cursor += len(key)


def main():
    parser = argparse.ArgumentParser(description="Solar Sim / terminal observatory with JPL positions and offline support")
    parser.add_argument("--plain",action="store_true",help="Use a scrolling line-command interface")
    parser.add_argument("--no-color",action="store_true",help="Disable terminal colors")
    parser.add_argument("--offline",action="store_true",help="Disable automatic JPL downloads; use cached or approximate positions")
    parser.add_argument("-c","--command",action="append",help="Execute a slash command and exit; may be repeated")
    args = parser.parse_args()
    sim = Simulation(online=not args.offline and not args.command)
    if args.command:
        sim.paused = True
        for command in args.command:
            print(sim.command(command))
            if command.strip() == "/sync" and sim.ephemeris.thread is not None:
                sim.ephemeris.thread.join()
                print(sim.ephemeris.details())
            if not sim.running:
                break
        return 0
    no_color = args.no_color or "NO_COLOR" in os.environ
    if args.plain or not sys.stdin.isatty() or not sys.stdout.isatty() or os.environ.get("TERM") in (None,"dumb"):
        plain_mode(sim,not no_color and sys.stdout.isatty())
        return 0
    locale.setlocale(locale.LC_ALL,"")
    try:
        import curses
    except ImportError:
        print("Full-screen mode is unavailable in this Python. Starting plain mode.")
        plain_mode(sim,not no_color)
        return 0
    try:
        curses.wrapper(lambda screen: tui(screen,sim,no_color))
    except KeyboardInterrupt:
        pass
    except curses.error as error:
        print(f"Terminal could not start full-screen mode ({error}). Starting plain mode.")
        plain_mode(sim,not no_color)
    print("Observatory closed. Clear skies!")
    sim.ephemeris.cancel.set()
    return 0


if __name__ == "__main__":
    sys.exit(main())
