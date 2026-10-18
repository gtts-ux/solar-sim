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
SCREENSAVERS = {'milky-way':'Milky Way','earth':'Earth','saturn':'Saturn','black-hole':'Black hole',
                'mercury':'Mercury','venus':'Venus','mars':'Mars',
                'jupiter':'Jupiter','uranus':'Uranus','neptune':'Neptune',
                'moon-view':'Moon view'}

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
        self.screensaver='milky-way'
        try:
            value=json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(value,dict):
                if isinstance(value.get('theme'),str) and value['theme'] in THEMES:self.theme=value['theme']
                if isinstance(value.get('screensaver'),str) and value['screensaver'] in SCREENSAVERS:self.screensaver=value['screensaver']
        except (OSError,ValueError,TypeError):
            pass

    def _save(self,theme,screensaver):
        temporary=self.path.with_name(self.path.name+f'.{os.getpid()}.tmp')
        try:
            temporary.write_text(json.dumps({'version':2,'theme':theme,'screensaver':screensaver},indent=2)+'\n',encoding='utf-8')
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
        self.theme,self.screensaver=theme,screensaver

    def set_theme(self,name):
        name=name.lower()
        if name not in THEMES:
            raise ValueError('Choose cosmic, amber, ocean, forest or mono.')
        self._save(name,self.screensaver)

    def set_screensaver(self,name):
        name='-'.join(name.lower().replace('_',' ').replace('-',' ').split())
        name={'galaxy':'milky-way','milkyway':'milky-way','blackhole':'black-hole','mrs':'mars','urnanus':'uranus',
              'moon':'moon-view','lunar':'moon-view','earth-from-moon':'moon-view'}.get(name,name)
        if name not in SCREENSAVERS:
            raise ValueError('Choose '+', '.join(SCREENSAVERS)+'. Example: /setting screensaver jupiter')
        self._save(self.theme,name)

    def text(self):
        lines=['SETTINGS / FIVE THEMES','']
        lines += [('  > ' if key==self.theme else '    ')+f'{i}. {value[0]}  /setting theme {key}'
                  for i,(key,value) in enumerate(THEMES.items(),1)]
        lines += ['', 'SCREENSAVER / '+SCREENSAVERS[self.screensaver], '']
        lines += [('  > ' if key==self.screensaver else '    ')+f'{i}. {label}  /setting screensaver {key}'
                  for i,(key,label) in enumerate(SCREENSAVERS.items(),6)]
        return '\n'.join(lines)+(f'\n\nType 1-5 for a theme, 6-{5+len(SCREENSAVERS)} for a screensaver.\n'
             'Full screen: arrows choose; Enter applies themes or previews savers.\n'
             'Space previews the saved animation; Enter again returns.\n'
             'Preferences save for the next start. --no-color overrides colors.\n'
             'Camera arrows work only in orbit view. Ctrl+P/N: command history.\n'
             '/setting exit or Esc returns without stopping a mission.')
