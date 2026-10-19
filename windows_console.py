"""Windows-only console transport for the same Solar Sim UI used on macOS.

Uses Win32 key events and VT output, without a separately installed curses wheel.
The small curses-shaped API is limited to the operations our UI actually uses.
"""
from collections import deque
import sys
import time

COLORS=256
COLOR_PAIRS=256
COLOR_BLACK=0
COLOR_WHITE=7
A_BOLD=1<<16
A_DIM=1<<17
A_REVERSE=1<<18
KEY_LEFT=260;KEY_RIGHT=261;KEY_UP=259;KEY_DOWN=258
KEY_HOME=262;KEY_END=360;KEY_PPAGE=339;KEY_NPAGE=338
KEY_ENTER=343;KEY_BACKSPACE=263;KEY_DC=330;KEY_F2=266;KEY_RESIZE=410
_pairs={0:(7,-1)}
_screen=None
_console=None


class error(Exception):pass


def decode_key(virtual,character='',control=0):
    """Read physical arrows as navigation keys, keeping typed control characters."""
    keys={0x25:KEY_LEFT,0x27:KEY_RIGHT,0x26:KEY_UP,0x28:KEY_DOWN,
          0x24:KEY_HOME,0x23:KEY_END,0x21:KEY_PPAGE,0x22:KEY_NPAGE,
          0x2e:KEY_DC,0x08:KEY_BACKSPACE,0x71:KEY_F2}
    if virtual in keys:return keys[virtual]
    if virtual==0x0d:return '\r'
    if character and character!='\0':return character
    if control&0x0c and 0x41<=virtual<=0x5a:return chr(virtual-0x40)
    return None


class Console:
    def __init__(self):
        import ctypes as ct
        from ctypes import wintypes as wt
        self.ct=ct;self.wt=wt
        self.api=ct.WinDLL('kernel32',use_last_error=True)
        class Coord(ct.Structure):_fields_=[('X',ct.c_short),('Y',ct.c_short)]
        class Rect(ct.Structure):_fields_=[('Left',ct.c_short),('Top',ct.c_short),('Right',ct.c_short),('Bottom',ct.c_short)]
        class Info(ct.Structure):
            _fields_=[('size',Coord),('cursor',Coord),('attributes',wt.WORD),('window',Rect),('maximum',Coord)]
        class Character(ct.Union):_fields_=[('wide',wt.WCHAR),('ascii',ct.c_char)]
        class Key(ct.Structure):
            _fields_=[('down',wt.BOOL),('repeat',wt.WORD),('virtual',wt.WORD),('scan',wt.WORD),('character',Character),('control',wt.DWORD)]
        class Event(ct.Union):_fields_=[('key',Key),('padding',ct.c_byte*16)]
        class Input(ct.Structure):_fields_=[('type',wt.WORD),('event',Event)]
        self.Info=Info;self.Input=Input
        signatures={
            'CreateFileW':([wt.LPCWSTR,wt.DWORD,wt.DWORD,ct.c_void_p,wt.DWORD,wt.DWORD,wt.HANDLE],wt.HANDLE),
            'CloseHandle':([wt.HANDLE],wt.BOOL),
            'GetConsoleMode':([wt.HANDLE,ct.POINTER(wt.DWORD)],wt.BOOL),
            'SetConsoleMode':([wt.HANDLE,wt.DWORD],wt.BOOL),
            'GetConsoleScreenBufferInfo':([wt.HANDLE,ct.POINTER(Info)],wt.BOOL),
            'WriteConsoleW':([wt.HANDLE,wt.LPCWSTR,wt.DWORD,ct.POINTER(wt.DWORD),ct.c_void_p],wt.BOOL),
            'ReadConsoleInputW':([wt.HANDLE,ct.POINTER(Input),wt.DWORD,ct.POINTER(wt.DWORD)],wt.BOOL),
            'WaitForSingleObject':([wt.HANDLE,wt.DWORD],wt.DWORD),
        }
        for name,(arguments,result) in signatures.items():
            function=getattr(self.api,name);function.argtypes=arguments;function.restype=result
        self.input=None;self.output=None;self.modes=[];self.pending=deque();self.high=''
        try:
            self.input=self.open('CONIN$');self.output=self.open('CONOUT$')
            for handle in (self.input,self.output):
                mode=wt.DWORD()
                if not self.api.GetConsoleMode(handle,ct.byref(mode)):raise error('A Windows console is required.')
                self.modes.append((handle,mode.value))
            # Disable line editing, echo, Ctrl+C interception, Quick Edit and VT
            # input: ReadConsoleInputW must receive physical key events directly.
            input_mode=(self.modes[0][1]|0x80|0x08)&~(0x01|0x02|0x04|0x40|0x200)
            if not self.api.SetConsoleMode(self.input,input_mode):raise error('Could not enable Windows keyboard input.')
            if not self.api.SetConsoleMode(self.output,(self.modes[1][1]|0x01|0x04)&~0x02):
                raise error('This console needs Windows 10 or newer for the animated interface.')
        except BaseException:
            self.close();raise

    def open(self,name):
        handle=self.api.CreateFileW(name,0xc0000000,3,None,3,0,None)
        if handle==self.ct.c_void_p(-1).value:raise error('Open Solar Sim in a Windows terminal, or use --plain.')
        return handle

    def size(self):
        info=self.Info()
        if not self.api.GetConsoleScreenBufferInfo(self.output,self.ct.byref(info)):
            raise error('Cannot read the Windows console size.')
        return info.window.Bottom-info.window.Top+1,info.window.Right-info.window.Left+1

    def write(self,text):
        # WriteConsoleW counts UTF-16 code units, rather than Python code points.
        written=self.wt.DWORD();units=len(text.encode('utf-16-le'))//2
        if text and not self.api.WriteConsoleW(self.output,text,units,self.ct.byref(written),None):
            raise error('Cannot draw the Windows console.')

    def read(self,timeout):
        if self.pending:return self.pending.popleft()
        end=None if timeout<0 else time.monotonic()+timeout/1000
        while True:
            remaining=0xffffffff if end is None else max(0,int((end-time.monotonic())*1000))
            state=self.api.WaitForSingleObject(self.input,remaining)
            if state==258:raise error('No input')
            if state!=0:raise error('Cannot read Windows keyboard input.')
            record=self.Input();count=self.wt.DWORD()
            if not self.api.ReadConsoleInputW(self.input,self.ct.byref(record),1,self.ct.byref(count)):
                raise error('Cannot read Windows keyboard input.')
            if record.type==4:return KEY_RESIZE
            if record.type!=1 or not record.event.key.down:continue
            event=record.event.key
            key=decode_key(event.virtual,event.character.wide,event.control)
            if key is None:continue
            if isinstance(key,str) and 0xd800<=ord(key)<=0xdbff:
                self.high=key;continue
            if isinstance(key,str) and self.high:
                if 0xdc00<=ord(key)<=0xdfff:key=(self.high+key).encode('utf-16-le','surrogatepass').decode('utf-16-le')
                self.high=''
            self.pending.extend([key]*(max(1,event.repeat)-1))
            return key

    def close(self):
        for handle,mode in self.modes:self.api.SetConsoleMode(handle,mode)
        self.modes=[]
        for handle in (self.input,self.output):
            if handle is not None:self.api.CloseHandle(handle)
        self.input=None;self.output=None


def style_codes(style):
    foreground,background=_pairs.get(style&0xffff,(7,-1))
    codes=['0']
    if style&A_BOLD:codes.append('1')
    if style&A_DIM:codes.append('2')
    if style&A_REVERSE:codes.append('7')
    codes+=['39'] if foreground<0 else ['38','5',str(foreground)]
    codes+=['49'] if background<0 else ['48','5',str(background)]
    return '\x1b['+';'.join(codes)+'m'


class Screen:
    """Double-buffered cells; send only changed runs in one write per frame."""
    def __init__(self,console):
        self.console=console;self.background=0;self.delay=-1
        self.cursor=(0,0);self.position_cursor=True;self.visibility=1
        self.previous=[];self.rows=[];self.shape=(0,0);self.erase()

    def getmaxyx(self):return self.shape
    def keypad(self,enabled):pass  # Win32 already distinguishes navigation keys.
    def timeout(self,milliseconds):self.delay=milliseconds
    def leaveok(self,enabled):self.position_cursor=not enabled
    def getbkgd(self):return self.background
    def bkgd(self,value,style=0):self.background=value if isinstance(value,int) else style
    def move(self,y,x):self.cursor=(y,x)
    def noutrefresh(self):pass
    def refresh(self):self.flush()

    def erase(self):
        shape=self.console.size()
        if shape!=self.shape:self.previous=[]
        self.shape=shape
        height,width=shape
        self.rows=[[(' ',self.background)]*width for _ in range(height)]

    def clear(self):self.previous=[];self.erase()

    def addnstr(self,y,x,text,length,style=0):self.addstr(y,x,str(text)[:max(0,length)],style)

    def addstr(self,y,x,text,style=0):
        height,width=self.shape
        if y<0 or y>=height or x<0 or x>=width:raise error('Outside the screen')
        import unicodedata
        for character in str(text):
            if x>=width:break
            if unicodedata.combining(character):continue
            if ord(character)<32 or 0x7f<=ord(character)<0xa0:character=' '
            self.rows[y][x]=(character,style);x+=1
            if unicodedata.east_asian_width(character) in ('W','F') and x<width:
                self.rows[y][x]=('',style);x+=1

    def get_wch(self):return self.console.read(self.delay)

    def flush(self):
        output=[];current=None
        if not self.previous:output.append('\x1b[0m\x1b[2J')
        for y,row in enumerate(self.rows):
            old=self.previous[y] if self.previous else None
            x=0
            while x<len(row):
                if old is not None and row[x]==old[x]:x+=1;continue
                start=x;style=row[x][1];text=[]
                while x<len(row) and row[x][1]==style and (old is None or row[x]!=old[x]):
                    text.append(row[x][0]);x+=1
                output.append(f'\x1b[{y+1};{start+1}H')
                if current!=style:output.append(style_codes(style));current=style
                output.append(''.join(text))
        if self.position_cursor:
            y,x=self.cursor;output.append(f'\x1b[{y+1};{x+1}H')
        output.append('\x1b[?25h' if self.visibility else '\x1b[?25l')
        self.console.write(''.join(output))
        self.previous=[row[:] for row in self.rows]


def has_colors():return True
def start_color():pass
def use_default_colors():pass
def set_escdelay(value):pass
def init_pair(index,foreground,background):_pairs[index]=(foreground,background)
def color_pair(index):return index
def doupdate():
    if _screen is not None:_screen.flush()
def curs_set(visible):
    if _screen is not None:_screen.visibility=visible


def wrapper(function,*args,**kwargs):
    global _screen
    console=_console or Console()
    try:
        console.write('\x1b[?1049h\x1b[?25l')
        _screen=Screen(console)
        return function(_screen,*args,**kwargs)
    finally:
        try:console.write('\x1b[0m\x1b[?25h\x1b[?1049l')
        finally:
            _screen=None
            if _console is None:console.close()


def run(root,arguments):
    """Enter the unchanged macOS UI through this Windows-native transport."""
    global _console
    import os
    from pathlib import Path
    original=(sys.stdin,sys.stdout,sys.stderr,sys.argv,sys.modules.get('curses'))
    streams=[]
    try:
        _console=Console()
        # IDEs and shell wrappers can expose pipes although a real console exists.
        # Reopen the console devices so the shared app's TTY guard sees that console.
        stdin=open('CONIN$','r',encoding='utf-8');streams.append(stdin)
        stdout=open('CONOUT$','w',encoding='utf-8',buffering=1);streams.append(stdout)
        sys.stdin=stdin;sys.stdout=stdout;sys.stderr=stdout
        sys.argv=[str(Path(root)/'solar_sim.py'),*arguments]
        os.environ['TERM']='xterm-256color'
        sys.modules['curses']=sys.modules[__name__]
        import solar_sim
        return solar_sim.main()
    except error as failure:
        print('Windows full-screen interface could not start: '+str(failure),file=original[2])
        print('Open a Windows terminal and run sol-sim again. Use --plain only for scrolling text mode.',file=original[2])
        return 1
    finally:
        if _console is not None:_console.close();_console=None
        sys.stdin,sys.stdout,sys.stderr,sys.argv,previous=original
        if previous is None:sys.modules.pop('curses',None)
        else:sys.modules['curses']=previous
        for stream in streams:stream.close()
