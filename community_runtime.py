"""Installed public data catalogues, independently scoped to each Simulation."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shlex

from catalog import lookup
import community_mods as model
from mod_manager import ROOT, REGISTRY, ModError, bodies, installed, load
from mod_manager import disabled_mods, require_enabled, set_enabled, uninstall
from updater import version


class CommunitySupport:
    def __init__(self,*args,**kwargs):
        self._installed_cache=None
        self._builder=None
        super().__init__(*args,**kwargs)

    @property
    def builder(self):
        if self._builder is None:
            from mod_builder import ModBuilder
            self._builder=ModBuilder(self.mods_path.parent)
        return self._builder

    @property
    def community_mode(self):
        return self.mod_mode and self.mod_data is not None and self.mod_data['format']==2

    def installed_mods(self,refresh=False):
        stamp=self.mods_path.stat().st_mtime_ns if self.mods_path.is_dir() else None
        if refresh or self._installed_cache is None or self._installed_cache[0]!=stamp:
            self._installed_cache=(stamp,installed(self.mods_path))
        return self._installed_cache[1]

    @property
    def mod_key(self):
        return self.mod_id if self.community_mode else super().mod_key

    @property
    def mod_notice(self):
        return model.notice(self.mod_data) if self.community_mode else super().mod_notice

    @property
    def mod_source(self):
        return 'Community Keplerian model; author-supplied orbital elements, no live ephemeris' if self.community_mode else super().mod_source

    @property
    def mod_hint(self):
        return '/body NAME /moons NAME /mod exit | Community model' if self.community_mode else super().mod_hint

    def lookup(self,name):
        if self.community_mode:
            key=(name or '').strip().lower().strip('"\'')
            if key=='core':return self.mod_bodies[0]
            aliases={alias.lower():entry['name'] for entry in self.mod_data['bodies'] for alias in [entry['name'],*entry.get('aliases',[])]}
            return next((b for b in self.mod_bodies if b.name==aliases.get(key)),None) or lookup(name)
        if self.mod_id is not None and self.mod_id not in REGISTRY:
            return lookup(name)
        return super().lookup(name)

    def body(self,name):
        if self.community_mode:
            found=self.lookup(name)
            if found in self.mod_bodies:return found
            raise ModError('Choose a body from this community catalogue with /planet, /moons or /body NAME. /mod exit returns to Solar System objects. Distances across systems are not modeled.')
        return super().body(name)

    @property
    def primary_bodies(self):
        if self.community_mode:
            return sorted((b for b in self.mod_bodies if b.parent==self.mod_bodies[0].name),key=lambda b:b.orbit)
        return super().primary_bodies

    def children(self,body):
        if self.community_mode and body in self.mod_bodies:
            return sorted((b for b in self.mod_bodies if b.parent==body.name),key=lambda b:b.orbit)
        return super().children(body)

    def entry(self,body):
        return next(b for b in self.mod_data['bodies'] if b['name']==body.name)

    def position(self,body):
        if not self.community_mode or body not in self.mod_bodies:return super().position(body)
        if body.parent is None:return (0.,0.,0.)
        origin=self.position(self.lookup(body.parent))
        return tuple(a+b for a,b in zip(origin,model.offset(body,self.entry(body),self.date)))

    def orbit_path(self,body):
        if self.community_mode and body in self.mod_bodies:
            entry=self.entry(body)
            return lambda anomaly:model.offset(body,entry,self.date,anomaly)
        return super().orbit_path(body)

    def orbit_number(self,body,fallback):
        if self.community_mode and body.parent:
            siblings=self.children(self.lookup(body.parent))
            return siblings.index(body)+1
        return super().orbit_number(body,fallback)

    def map_system(self,view=None):
        if not self.community_mode:return super().map_system(view)
        if self.orbit_focus is not None and (view is None or view==self.view):
            return self.lookup(self.orbit_focus.parent),[self.orbit_focus]
        view=view or self.view
        if view in ('solar',self.mod_key,'inner','outer','core',self.mod_bodies[0].name.lower()):
            children=self.primary_bodies
            split=(len(children)+1)//2
            return self.mod_bodies[0],children[:split] if view=='inner' else children[split:] if view=='outer' else children
        center=self.body(view)
        children=self.children(center)
        return center,[] if self.system_filter=='spacecraft' else [b for b in children if b.kind=='Moon'] if self.system_filter=='moons' else children

    def describe(self,body):
        if self.community_mode and body in self.mod_bodies:
            return model.describe(body,self.mod_data,self.date,self.position)
        return super().describe(body)

    def text_map(self,width=88,height=25):
        if not self.community_mode:return super().text_map(width,height)
        from engine import SolarSimulation
        text=SolarSimulation.text_map(self,width,height).split('\n\nPaths:')[0]
        return text+'\n\nCommunity model: parent-relative ellipses, author-supplied elements; not a live ephemeris.\n/body NAME /moons NAME /mod exit'

    def show_mods(self):
        packages,errors=self.installed_mods(refresh=True)
        rows=['MODS / installed catalogues','']
        disabled=disabled_mods(self.mods_path)
        for package in packages:
            title=package.get('name',REGISTRY.get(package['id'],{}).get('name',package['id']))
            state='OFF' if package['id'] in disabled else 'ON'
            if self.mod_mode and self.mod_id==package['id']:state+=' / viewing'
            rows.append(f"  [{state}] {title} / v{package['version']} /mod {package['id']}")
        if not packages:rows.append('No mods installed yet.')
        if errors:
            rows+=['','INVALID PACKAGES / not loaded']+[name+': '+error for name,error in errors]
        return '\n'.join(rows)+('\n\nInstall in Terminal: sol-sim -m "username/repository" or -m "./solar-mod.json"\n'
                                    'Built-ins: sol-sim -m"proxima centauri" or -m"interstellar"\n'
                                    '/mod ID opens a catalogue; /mod exit returns.\n'
                                    '/mods enable ID | /mods disable ID | /mods uninstall ID\n'
                                    'On permits opening a system; Off keeps its installed files. Uninstall removes its installed package.\n'
                                    '/builder opens the in-app mod maker. /mod tutorial keeps the JSON creation guide.')

    def activate_mod(self,mod_id):
        require_enabled(self.mods_path,mod_id)
        if mod_id in REGISTRY:return super()._command('/'+REGISTRY[mod_id]['command'])
        data=load(self.mods_path,mod_id)
        if version((ROOT/'VERSION.txt').read_text())<version(data['app_min']):
            raise ModError('This mod needs Solar Sim '+data['app_min']+'. Run sol-sim -u first.')
        if self.mission is not None:self.stop_mission()
        self.overlay=None;self.mod_id=mod_id;self.mod_data=data;self.mod_bodies=bodies(data)
        self.mod_mode=True;self.dwarf_mode=False;self.selected=self.primary_bodies[0]
        self.orbit_focus=None;self.system_filter='all';self.preview_missions=False
        self.view=mod_id;self.camera.select('system')
        self.orbit_notice='Community orbital model / /mod exit returns to normal planets'
        return self.text_map() if self.screen=='orbit' else self.mod_notice

    def _command(self,raw):
        parts=shlex.split(raw.strip().lstrip('/'))
        cmd=parts[0].lower() if parts else '';args=parts[1:]
        if cmd=='builder':
            self.overlay=None
            return self.builder.command(args)
        if cmd=='mods':
            if args and args!=['list']:
                if len(args)!=2 or args[0].lower() not in ('enable','disable','uninstall'):
                    raise ModError('Usage: /mods, /mods enable ID, /mods disable ID or /mods uninstall ID.')
                action,mod_id=(part.lower() for part in args)
                if action=='uninstall':uninstall(self.mods_path,mod_id)
                else:set_enabled(self.mods_path,mod_id,action=='enable')
                if action!='enable' and self.mod_mode and self.mod_id==mod_id:self.leave_system()
                self._installed_cache=None
                self.overlay=None
                return mod_id+{'enable':' turned on.','disable':' turned off.','uninstall':' uninstalled.'}[action]+'\n\n'+self.show_mods()
            self.overlay=None;self.screen='dashboard';self.orbit_focus=None
            return self.show_mods()
        if cmd=='mod':
            if not args:
                self.overlay=None;self.screen='dashboard';self.orbit_focus=None
                return self.show_mods()
            if len(args)!=1:raise ModError('Usage: /mod ID, /mod exit or /mod tutorial.')
            action=args[0].lower()
            if action in ('tutorial','help'):
                self.overlay=None;self.screen='dashboard';self.orbit_focus=None
                return (ROOT/'MODDING.txt').read_text(encoding='utf-8')
            if action=='exit':
                self.overlay=None
                if self.mission is not None:self.stop_mission()
                self.leave_system()
                return self.text_map() if self.screen=='orbit' else 'SOLAR SYSTEM / normal planets restored.\n/planet  /orbit  /mods'
            return self.activate_mod(action)
        if cmd=='body':
            if not args:raise ModError('Usage: /body NAME. Use /planet or /moons for names.')
            self.overlay=None
            return self.open_body(self.body(' '.join(args)))
        if cmd=='help':
            return super()._command(raw)+'\n\nCOMMUNITY MODS\n  /mods manages installed catalogues; /mod ID opens one; /mod exit returns.\n  /mods enable ID /mods disable ID /mods uninstall ID\n  /builder opens the in-app mod maker.\n  /body NAME opens any object. /mod tutorial is the creation guide.\n  Terminal: sol-sim --mod-template solar-mod.json; sol-sim --check-mod solar-mod.json\n  Install: sol-sim -m "username/repository" or -m "./solar-mod.json"'
        if not self.community_mode:return super()._command(raw)
        # A catalogue cannot take over the simulator's command names.
        from engine import COMMANDS
        found=self.lookup(' '.join(parts))
        if found in self.mod_bodies and cmd not in COMMANDS:
            self.overlay=None
            return self.open_body(found)
        if cmd in ('planet','planets'):
            self.overlay=None
            if args:
                body=self.body(' '.join(args))
                if body not in self.primary_bodies:raise ModError('Choose a planet in this catalogue; /body NAME opens other objects.')
                return self.open_body(body)
            self.screen='dashboard';self.orbit_focus=None
            return self.mod_notice+'\n\n'+'\n'.join(f'  /body {b.name} / {b.orbit:,.0f} km / {b.period:g} days' for b in self.primary_bodies)
        if cmd in ('orbit','view','map','focus'):
            self.overlay=None;self.orbit_focus=None;self.system_filter='all'
            target=' '.join(args).lower() if args else self.mod_key
            self.orbit_notice='Community Keplerian illustration / /mod exit returns'
            if target in ('solar',self.mod_key,'inner','outer'):
                self.view=self.mod_key if target=='solar' else target
            else:
                body=self.body(target);self.selected=body;self.view=self.mod_key
                self.orbit_focus=body if body.parent else None
            if cmd!='map':self.screen='orbit'
            return self.text_map()
        if cmd=='moon':
            if not args:raise ModError('Usage: /moon NAME; /moons lists the included moons.')
            body=self.body(' '.join(args))
            if body.kind!='Moon':raise ModError('Choose an included Moon; /body NAME opens other objects.')
            return self.open_body(body)
        if cmd in ('moons','mooons','satellites','satellite'):
            self.overlay=None
            body=self.body(' '.join(args)) if args else self.selected
            spacecraft=cmd in ('satellites','satellite')
            children=[] if spacecraft else [b for b in self.children(body) if b.kind=='Moon']
            message=('No spacecraft orbits are included in this community format.' if spacecraft else
                     body.name+f': {len(children)} included moons; this catalogue is not a complete census.')
            if self.screen=='orbit':
                self.view=body.name.lower();self.orbit_focus=None;self.selected=body
                self.system_filter='spacecraft' if spacecraft else 'moons';self.orbit_notice=message
                return message+'\n\n'+self.text_map()
            self.screen='dashboard';self.orbit_focus=None
            if not args and not spacecraft:children=[b for b in self.mod_bodies if b.kind=='Moon']
            return message+'\n\n'+'\n'.join(f'  /body {b.name} / parent {b.parent} / orbit {b.orbit:,.0f} km / {b.period:g} days' for b in children)
        if cmd in ('compare','distance','day','sources','info','sync','weight'):
            self.overlay=None;self.screen='dashboard';self.orbit_focus=None
        if cmd in ('compare','distance'):
            if len(args)!=2:raise ModError('Usage: /'+cmd+' "first body" "second body"')
            a,b=map(self.body,args);distance=math.dist(self.position(a),self.position(b))
            result=(a.name.upper()+' <> '+b.name.upper()+f'\n\nSEPARATION / {self.date:%Y-%m-%d %H:%M:%S} UTC\n'
                    f'  Center-to-center distance: {distance:,.3f} km\n'
                    f'  Flat-space light travel: {distance/299792.458:,.3f} seconds\n'
                    '  Local community Keplerian geometry; not an observed distance or relativistic travel time.\n')
            return result+('\n'+self.describe(a)+'\n\n'+self.describe(b) if cmd=='compare' else '')
        if cmd=='day':
            body=self.body(' '.join(args)) if args else self.selected
            return body.name+' / DAY LENGTH\n'+(f'Author-supplied sidereal rotation: {abs(body.rotation):g} hours'+(' (retrograde)' if body.rotation<0 else '')+'.' if body.rotation else 'Sidereal rotation: unknown / unspecified.')+'\nA solar day is not inferred from community orbital elements.'
        if cmd=='weight':
            if len(args)!=2:raise ModError('Usage: /weight MASS_KG "body name"')
            mass=float(args[0]);body=self.body(args[1])
            if not math.isfinite(mass) or not 0<mass<=1e12:raise ModError('Use a finite mass greater than 0 and at most 1e12 kg.')
            if body.kind in ('Star','Black hole'):raise ModError('This central body has no planetary solid surface.')
            return f'WEIGHT / {body.name}\n\nSpherical model force: {mass*body.gravity:,.3f} N\nUses author-supplied mass/radius, including their estimates or fictional values.'
        if cmd=='sources':
            return self.mod_data['name'].upper()+' / COMMUNITY SOURCES\n\n'+('\n'.join(self.mod_data['sources']) or 'Fictional original system; no external sources supplied.')+'\n\n'+self.mod_notice
        if cmd=='info':return self.mod_notice
        if cmd=='sync':return 'Community systems use the author\'s local Keplerian elements. Solar System JPL synchronization does not provide their positions.'
        if cmd=='export':
            if args:raise ModError('Use /export without arguments.')
            folder=ROOT/'exports';folder.mkdir(exist_ok=True)
            path=folder/f'{self.mod_id}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S-%f}.json'
            data={'simulation_utc':self.date.isoformat(),'mod_id':self.mod_id,'mod_version':self.mod_data['version'],
                  'frame':self.mod_bodies[0].name+' centered','model':self.mod_source,'fictional':self.mod_data['fictional'],
                  'bodies':[{'name':b.name,'parent':b.parent,'local_position_km':self.position(b),
                             'mass_kg':b.mass,'mass_is_estimate':b.estimated_mass,'mean_radius_km':b.radius,
                             'radius_is_estimate':self.entry(b).get('estimated_radius',True),
                             'values_are_fictional':self.mod_data['fictional']} for b in self.mod_bodies]}
            path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
            return 'Snapshot saved:\n'+str(path)
        # Generic clock, settings, search, random, navigation and mission controls.
        # Skip the legacy mod command decoder, whose descriptions are catalogue-specific.
        from engine import SolarSimulation
        if cmd in ('dwarf','mission','missions','proxima','interstellar'):
            return super()._command(raw)
        return SolarSimulation._command(self,raw)
