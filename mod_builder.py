"""Saved, editable drafts and portable publishable format-2 mod projects."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile

import community_mods as model

MAX_DRAFT=128*1024


def slug(name):
    value=re.sub('[^a-z0-9]+','-',name.lower()).strip('-')[:48].rstrip('-')
    try:return model.identifier(value)
    except ValueError:return 'my-system'


def starter(kind,name,parent=None,orbit=0,phase=0):
    mass,radius,rotation={'Star':(1.98847e30,696340,609.12),
                          'Planet':(5.9722e24,6371,24),
                          'Dwarf planet':(1.303e22,1188.3,153.3),
                          'Moon':(7.342e22,1737.4,655.7)}[kind]
    period=0 if parent is None else math.tau*math.sqrt((orbit*1000)**3/(6.67430e-11*(parent['mass']+mass)))/86400
    return dict(name=name,kind=kind,parent=None if parent is None else parent['name'],
                color={'Star':3,'Planet':4,'Dwarf planet':5,'Moon':7}[kind],mass=mass,radius=radius,
                orbit=orbit,period=period,rotation=rotation,temperature='Unspecified',composition='Unspecified',
                atmosphere='Unspecified',features='Starter model values; edit to describe your object.',
                estimated_mass=True,estimated_radius=True,eccentricity=0.,inclination=0.,node=0.,periapsis=0.,phase=phase)


def package_bytes(package):return (json.dumps(package,indent=2,ensure_ascii=False)+'\n').encode('utf-8')


def validate_draft(state):
    if not isinstance(state,dict) or set(state)!={'format','package','notes'} or type(state['format']) is not int or state['format']!=1:
        raise ValueError('Unsupported builder draft.')
    notes=state['notes']
    if not isinstance(notes,str) or len(notes)>6000 or any(not c.isprintable() and c!='\n' for c in notes):
        raise ValueError('Project notes use printable text, up to 6000 characters.')
    package=deepcopy(state['package'])
    if not isinstance(package,dict) or type(package.get('fictional')) is not bool:
        raise ValueError('Invalid draft package.')
    # An unfinished draft may have no star/planets or sources yet. Every value
    # already entered still goes through the public mod validator.
    package['fictional']=True
    if not isinstance(package.get('bodies'),list):raise ValueError('Invalid body list.')
    if not package['bodies']:package['bodies']=[starter('Star','Draft center')]
    if len(package['bodies'])==1:
        used={value.lower() for body in package['bodies'] for value in [body['name'],*body.get('aliases',[])]}
        name='Draft companion'
        while name.lower() in used:name+=' 1'
        package['bodies'].append(starter('Planet',name,package['bodies'][0],149597870.7))
    model.validate(package_bytes(package))
    return state


class ModBuilder:
    def __init__(self,root):
        self.root=Path(root);self.folder=self.root/'mod-projects';self.path=self.folder/'draft.json'
        self._state=None

    def safe_folder(self):
        if self.folder.is_symlink() or self.path.is_symlink():raise ValueError('Builder folders and drafts must not be symbolic links.')

    @property
    def state(self):
        self.safe_folder()
        if self._state is None and self.path.exists():
            with self.path.open('rb') as stream:content=stream.read(MAX_DRAFT+1)
            if len(content)>MAX_DRAFT:raise ValueError('The draft is too large.')
            try:self._state=validate_draft(json.loads(content))
            except RecursionError as failure:raise ValueError('The saved draft is nested too deeply.') from failure
        return deepcopy(self._state)

    @property
    def package(self):
        state=self.state
        if state is None:raise ValueError('Create a new mod first with /builder new "My system".')
        return state['package']

    def save(self,state):
        self.safe_folder();validate_draft(state)
        content=package_bytes(state)
        if len(content)>MAX_DRAFT:raise ValueError('The draft is too large.')
        self.folder.mkdir(exist_ok=True)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=self.folder,prefix='.draft-',suffix='.tmp',delete=False) as output:
                temporary=Path(output.name);output.write(content);output.flush();os.fsync(output.fileno())
            os.replace(temporary,self.path)
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)
        self._state=deepcopy(state)

    def new(self,name):
        model.text(name,'Mod name',64)
        self.archive()
        package=dict(format=2,id=slug(name),name=name,description='A user-created system catalogue.',version='1.0.0',
                     app_min=model.FORMAT_MIN,fictional=True,sources=[],bodies=[])
        self.save(dict(format=1,package=package,notes=''))
        return 'Created draft: '+name+'. Add a central star, then planets and their moons.'

    def archive(self):
        """Preserve the previous draft, including a damaged file, before replacing it."""
        self.safe_folder()
        if self.path.is_file():
            with self.path.open('rb') as source,tempfile.NamedTemporaryFile(dir=self.folder,prefix='saved-draft-',suffix='.json',delete=False) as backup:
                shutil.copyfileobj(source,backup)

    def body(self,index):
        try:return self.package['bodies'][int(index)-1] if int(index)>0 else self._bad_body()
        except (ValueError,IndexError,TypeError):raise ValueError('Choose an existing body number from the builder.') from None

    def _bad_body(self):raise ValueError('Choose an existing body number from the builder.')

    def add(self,kind,name,parent_name=None):
        model.body_name(name);state=self.state
        if state is None:raise ValueError('Create a mod draft first.')
        entries=state['package']['bodies']
        if len(entries)>=model.MAX_BODIES:raise ValueError('A mod can contain up to 64 bodies.')
        if kind=='Star':
            if entries:raise ValueError('Format 2 supports one central star. Edit the existing center instead.')
            body=starter(kind,name)
        elif kind in ('Planet','Dwarf planet'):
            if not entries:raise ValueError('Add the central star first.')
            count=sum(e['kind'] in ('Planet','Dwarf planet') for e in entries)
            body=starter(kind,name,entries[0],149597870.7*(1+count*.7),count*72%360)
        elif kind=='Moon':
            parent=next((entry for entry in entries if entry['name']==parent_name),None)
            if parent is None or parent['kind'] not in ('Planet','Dwarf planet','Moon'):
                raise ValueError('Choose a planet or moon as the moon parent.')
            count=sum(e['parent']==parent_name for e in entries)
            body=starter(kind,name,parent,384400*(1+count*.5),count*60%360)
        else:raise ValueError('Choose Star, Planet, Dwarf planet or Moon.')
        entries.append(body);self.save(state)
        return len(entries)

    def set(self,scope,field,value,index=None):
        state=self.state
        if state is None:raise ValueError('Create a mod draft first.')
        package=state['package']
        if scope=='project':
            if field!='notes':raise ValueError('Unknown project field.')
            state['notes']=value.replace('\\n','\n')
        else:
            target=package if scope=='mod' else package['bodies'][int(index)-1] if scope=='body' and self.body(index) else None
            allowed={'name','id','description','version','fictional','sources'} if scope=='mod' else {
                'name','kind','parent','color',*model.NUMBERS,*model.TEXTS,*model.ANGLES,'eccentricity','estimated_mass','estimated_radius','aliases'}
            field='features' if field=='notes' and scope=='body' else field
            if target is None or field not in allowed:raise ValueError('Unknown editable field.')
            if field in (*model.NUMBERS,*model.ANGLES,'eccentricity'):value=float(value)
            elif field=='color':value=int(value)
            elif field in ('fictional','estimated_mass','estimated_radius'):
                if str(value).lower() not in ('true','false'):raise ValueError('Use true or false.')
                value=str(value).lower()=='true'
            elif field in ('sources','aliases'):value=[part.strip() for part in value.split(';') if part.strip()]
            if field=='name' and scope=='body':
                before=target['name']
                for entry in package['bodies']:
                    if entry['parent']==before:entry['parent']=value
            target[field]=value
        self.save(state)
        return 'Saved '+field+'.'

    def remove(self,index):
        body=self.body(index);state=self.state;names={body['name']}
        for _ in state['package']['bodies']:
            names.update(b['name'] for b in state['package']['bodies'] if b['parent'] in names)
        state['package']['bodies']=[b for b in state['package']['bodies'] if b['name'] not in names]
        self.save(state)
        return 'Removed '+str(len(names))+' draft bodies.'

    def validate(self):
        model.validate(package_bytes(self.package))
        return 'Ready to export: '+self.package['name']+' / '+str(len(self.package['bodies']))+' bodies.'

    def projects(self):
        self.safe_folder()
        if not self.folder.exists():return []
        return [p.name for p in sorted(self.folder.iterdir()) if not p.is_symlink() and
                (p.is_dir() and (p/'solar-mod.json').is_file() or p.is_file() and p.name.startswith('saved-draft-') and p.suffix=='.json')]

    def load(self,name):
        if name not in self.projects():raise ValueError('Choose a saved draft or exported project from the builder.')
        path=self.folder/name
        source=path if path.is_file() else path/'builder-draft.json'
        if source.is_symlink():raise ValueError('Drafts must not be symbolic links.')
        if source.is_file():
            with source.open('rb') as stream:content=stream.read(MAX_DRAFT+1)
            if len(content)>MAX_DRAFT:raise ValueError('The draft is too large.')
            try:state=validate_draft(json.loads(content))
            except RecursionError as failure:raise ValueError('The saved draft is nested too deeply.') from failure
        else:
            with (path/'solar-mod.json').open('rb') as stream:content=stream.read(model.LIMIT+1)
            state=dict(format=1,package=model.validate(content),notes='')
        self.archive();self.save(state)
        return 'Loaded draft: '+state['package']['name']+'.'

    def export(self):
        self.validate();self.safe_folder();state=self.state;package=state['package']
        self.folder.mkdir(exist_ok=True)
        stem=package['id'];index=1
        while True:
            destination=self.folder/(stem if index==1 else stem+'-'+str(index))
            try:destination.mkdir();break
            except FileExistsError:index+=1
        written=[]
        try:
            files={'solar-mod.json':package_bytes(package),'builder-draft.json':package_bytes(state),
                   'README.md':self.readme(state).encode('utf-8'),
                   'README.txt':self.readme(state).encode('utf-8'),
                   'PUBLISH.txt':self.publish_text(package).encode('utf-8')}
            for name,content in files.items():
                path=destination/name
                with path.open('xb') as output:output.write(content)
                written.append(path)
        except BaseException:
            for path in written:path.unlink(missing_ok=True)
            try:destination.rmdir()
            except OSError:pass
            raise
        return destination

    @staticmethod
    def readme(state):
        p=state['package'];rows=['# '+p['name'],'',p['description'],'',
            'Version: '+p['version'],'Model: '+('Fictional' if p['fictional'] else 'Community supplied'),'',
            '## Objects','', 'Name | Type | Parent | Radius (km) | Mass (kg)',
            '--- | --- | --- | ---: | ---:']
        rows += [f"{b['name']} | {b['kind']} | {b['parent'] or 'System center'} | {b['radius']:g} | {b['mass']:g}" for b in p['bodies']]
        for body in p['bodies']:rows+=['','### '+body['name'],'',body['features']]
        if state['notes']:rows+=['','## Project notes','',state['notes']]
        rows+=['','## Install','', 'From this folder: `sol-sim -m "./solar-mod.json"`',
               'Then open `/mod '+p['id']+'` inside the app. `/mod exit` returns.',
               '', 'After publishing: `sol-sim -m "YOUR-NAME/YOUR-REPOSITORY"`',
               '', '## Model','', 'Author-supplied parent-relative Keplerian ellipses, not a live ephemeris.',
               'Starter mass/radius values are estimates unless edited and marked otherwise.']
        if p['sources']:rows+=['','## Sources','',*p['sources']]
        return '\n'.join(rows)+'\n'

    @staticmethod
    def publish_text(package):
        return ('PUBLISH '+package['name']+'\n\n'
                '1. Review solar-mod.json, descriptions, notes and source links.\n'
                '2. Validate from this folder: sol-sim --check-mod solar-mod.json\n'
                '3. Try locally: sol-sim -m "./solar-mod.json"\n'
                '   Open /mod '+package['id']+' in the app and check its orbits and moons.\n'
                '4. Create your own public GitHub repository and upload this folder\n'
                '   CONTENTS at its root. solar-mod.json must be at the repository root.\n'
                '   Choose a license if you want to specify reuse permissions.\n'
                '5. Share: sol-sim -m "YOUR-NAME/YOUR-REPOSITORY"\n\n'
                'Nothing is uploaded automatically. Reopen this project in /builder\n'
                'to edit it; exported folders are snapshots and are never overwritten.\n'
                'Keep the same id and increase version before releasing an update.\n')

    def text(self):
        state=self.state
        if state is None:return 'MOD MAKER\n\nCreate a draft, add a star, planets and moons, then export a publishable folder.\n/builder new "My system"\n/mod tutorial keeps the manual JSON workflow available.'
        p=state['package']
        return ('MOD MAKER / '+p['name']+'\n\nDraft auto-saved in '+str(self.path)+'\n'+
                '\n'.join(f"{i}. {b['name']} / {b['kind']} / parent: {b['parent'] or 'center'}" for i,b in enumerate(p['bodies'],1))+
                '\n\nArrow menu: edit details, add bodies and moons, add notes, validate or export.\n'
                '/builder add star "Star name"\n/builder add planet "Planet name"\n'
                '/builder add moon "Moon name" "Planet name"\n'
                '/builder set body 2 mass 5.972e24\n/builder set body 2 notes "Your notes"\n'
                '/builder validate  /builder export  /mod tutorial')

    def command(self,args):
        if not args:return self.text()
        if args[0]=='new' and len(args)==2:return self.new(args[1])
        if args[0]=='add' and len(args) in (3,4):
            kind={'star':'Star','planet':'Planet','dwarf':'Dwarf planet','moon':'Moon'}.get(args[1].lower())
            index=self.add(kind,args[2],args[3] if len(args)==4 else None)
            return 'Added '+self.body(index)['name']+'. Draft saved.'
        if args[0]=='set':
            if len(args)==4 and args[1] in ('mod','project'):return self.set(args[1],args[2],args[3])
            if len(args)==5 and args[1]=='body':return self.set('body',args[3],args[4],args[2])
        if args[0]=='delete' and len(args)==2:return self.remove(args[1])
        if args==['validate']:return self.validate()
        if args==['export']:
            path=self.export();return 'Mod project exported: '+str(path)+'\nIncludes solar-mod.json, README.md, README.txt, PUBLISH.txt and an editable builder draft.'
        if args[0]=='load' and len(args)==2:return self.load(args[1])
        raise ValueError('Use /builder, /builder new "Name", /builder add star/planet/moon "Name" ["Parent"], /builder set mod FIELD "Value", /builder set body NUMBER FIELD "Value", /builder delete NUMBER, /builder validate or /builder export.')
