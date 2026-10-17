"""Five terminal themes and a small, persistent local preference file."""
import json
import os
from pathlib import Path

THEMES = {
    'cosmic': ('Cosmic', (203,120,221,75,141,81,255,244), (1,2,3,4,5,6,7,7)),
    'amber': ('Amber', (166,178,221,172,214,220,230,137), (1,3,3,3,1,3,7,3)),
    'ocean': ('Ocean', (75,86,153,33,111,51,195,66), (4,6,7,4,6,6,7,4)),
    'forest': ('Forest', (173,114,186,65,150,120,230,71), (1,2,3,2,3,2,7,2)),
    'mono': ('Mono', (250,250,255,244,250,255,255,240), (7,7,7,7,7,7,7,7)),
}
COSMIC = (17,18,24,25,32,39,75,117,17,53,54,55,61,99,141,189,
          52,94,130,172,214,221,229,230,235,238,242,245,250,253,255,231)


def galaxy_palette(theme):
    gray=(235,238,242,245,250,253,255,231)
    if theme=='amber':
        return (52,94,130,172,178,214,221,229)*2+(94,130,172,178,214,221,229,230)+gray
    if theme=='ocean':
        return (17,18,24,25,32,39,75,117)+(17,23,24,30,37,44,80,123)+(23,30,37,44,80,123,159,195)+gray
    if theme=='forest':
        return (22,28,29,35,71,77,114,157)+(22,58,64,100,106,142,186,229)+(58,94,100,136,178,220,229,230)+gray
    return gray*4 if theme=='mono' else COSMIC


class Settings:
    def __init__(self,path):
        self.path=Path(path)
        self.theme='cosmic'
        try:
            value=json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(value,dict) and value.get('theme') in THEMES:
                self.theme=value['theme']
        except (OSError,ValueError,TypeError):
            pass

    def set_theme(self,name):
        name=name.lower()
        if name not in THEMES:
            raise ValueError('Choose cosmic, amber, ocean, forest or mono.')
        temporary=self.path.with_name(self.path.name+f'.{os.getpid()}.tmp')
        try:
            temporary.write_text(json.dumps({'version':1,'theme':name},indent=2)+'\n',encoding='utf-8')
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
        self.theme=name

    def text(self):
        lines=['SETTINGS / FIVE THEMES','']
        lines += [('  > ' if key==self.theme else '    ')+f'{i}. {value[0]}  /setting theme {key}'
                  for i,(key,value) in enumerate(THEMES.items(),1)]
        return '\n'.join(lines)+('\n\nType 1-5 here, or use /setting theme amber or /setting 2.\n'
             'Saved on this computer for the next start. --no-color overrides colors.\n'
             'Left/Right: camera. Ctrl+B/F: edit input. /camera system: original view.\n'
             '/setting exit or Esc returns without stopping a mission.')
