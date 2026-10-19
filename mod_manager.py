"""Install and validate registered, data-only system mods. No mod code is executed."""
import json
import base64
import math
import os
from pathlib import Path
import tempfile
import re
from urllib.error import URLError
from urllib.parse import urlsplit, unquote

from catalog import Body
from updater import UpdateError, fetch_bytes, version
import community_mods

MOD_ID = 'proxima-centauri'
MOD_URL = 'https://raw.githubusercontent.com/gtts-ux/proxima-centauri-mod/main/proxima-centauri.json'
LIMIT = 65536
ROOT = Path(__file__).resolve().parent
REGISTRY = {
    MOD_ID: {'name':'Proxima Centauri', 'command':'proxima centauri', 'exit':'proxima exit',
             'url':MOD_URL, 'frame':'Proxima Centauri centered; illustrative orbital phases',
             'names':('Proxima Centauri','Proxima Centauri d','Proxima Centauri b'),
             'kinds':('M dwarf star','Exoplanet')},
    'interstellar': {'name':'Interstellar', 'command':'interstellar', 'exit':'interstellar exit',
                     'url':'https://raw.githubusercontent.com/gtts-ux/interstellar-mod/main/interstellar.json',
                     'frame':'Fictional Gargantua centered; schematic film-system layout',
                     'names':('Gargantua','Miller','Mann','Edmunds'),
                     'kinds':('Fictional black hole','Fictional planet')},
}


class ModError(ValueError):
    pass


def validate(content, mod_id=MOD_ID):
    if mod_id not in REGISTRY:
        try:return community_mods.validate(content,mod_id)
        except ValueError as error:raise ModError(str(error)) from error
    try:
        spec = REGISTRY[mod_id]
        if len(content) > LIMIT:
            raise ValueError('Package exceeds 64 KiB.')
        data = json.loads(content)
        if not isinstance(data, dict) or type(data.get('format')) is not int or data.get('format') != 1 or data.get('id') != mod_id:
            raise ValueError('Unsupported mod format or identifier.')
        for field in ('version', 'app_min'):
            if not isinstance(data[field], str):
                raise ValueError('Invalid version field.')
            version(data[field])
        if data['frame'] != spec['frame']:
            raise ValueError('Unsupported coordinate frame.')
        if not isinstance(data['sources'], list) or not 1 <= len(data['sources']) <= 12:
            raise ValueError('Sources are required.')
        for source in data['sources']:
            if not isinstance(source, str) or not source.startswith('https://') or len(source) > 300 or any(ord(c) < 32 for c in source):
                raise ValueError('Invalid source URL.')
        entries = data['bodies']
        if not isinstance(entries, list) or len(entries) != len(spec['names']):
            raise ValueError('Unexpected number of system bodies.')
        names = spec['names']
        numbers = ('mass', 'radius', 'orbit', 'period', 'rotation')
        texts = ('temperature', 'composition', 'atmosphere', 'features')
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or entry.get('name') != names[index]:
                raise ValueError('Unexpected body name or order.')
            for key in numbers:
                value = entry[key]
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError('Invalid physical value: '+key)
            mass_limit = 1e40 if mod_id == 'interstellar' and not index else 1e32
            radius_limit = 1e10 if mod_id == 'interstellar' and not index else 1e8
            if not (0 < entry['mass'] < mass_limit and 0 < entry['radius'] < radius_limit):
                raise ValueError('Invalid mass or radius.')
            if index and not (0 < entry['orbit'] < 1e12 and 0 < entry['period'] < 1e7 and entry['rotation'] == 0):
                raise ValueError('Invalid planetary orbit or unknown rotation.')
            if not index and (entry['orbit'] != 0 or entry['period'] != 0 or
                              not (entry['rotation'] == 0 if mod_id == 'interstellar' else 0 < entry['rotation'] < 1e6)):
                raise ValueError('Invalid stellar orbit or rotation.')
            if entry['parent'] != (names[0] if index else None):
                raise ValueError('Invalid parent.')
            if entry['kind'] != spec['kinds'][bool(index)]:
                raise ValueError('Invalid body kind.')
            if type(entry['color']) is not int or not 1 <= entry['color'] <= 7:
                raise ValueError('Invalid body color.')
            for key in texts:
                if not isinstance(entry[key], str) or not 1 <= len(entry[key]) <= 1200 or any(ord(c) < 32 for c in entry[key]):
                    raise ValueError('Invalid descriptive text.')
            if set(entry) != {'name', 'kind', 'parent', 'color', *numbers, *texts}:
                raise ValueError('Unsupported body fields.')
        return data
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError, UpdateError, UnicodeError) as error:
        raise ModError('Invalid '+REGISTRY.get(mod_id,{}).get('name','system mod')+' package: '+str(error)) from error


def load(folder, mod_id=MOD_ID):
    if mod_id not in REGISTRY:
        try:community_mods.identifier(mod_id)
        except ValueError as error:raise ModError(str(error)) from error
    spec = REGISTRY.get(mod_id,{'name':mod_id,'command':'mod '+mod_id})
    path = Path(folder)/(mod_id+'.json')
    if not path.is_file():
        raise ModError(spec['name']+' is not installed. In your terminal run: sol-sim -m"'+spec['command']+'"\nThen open /'+spec['command']+' in the app.')
    try:
        with path.open('rb') as source:
            return validate(source.read(LIMIT+1), mod_id)
    except OSError as error:
        raise ModError('Cannot read installed mod: '+str(error)) from error


def bodies(data):
    if data['format']==2:return community_mods.bodies(data)
    return [Body(**entry, estimated_mass=bool(index)) for index, entry in enumerate(data['bodies'])]


def install(root, name, *, fetch=fetch_bytes, offline=False):
    root = Path(root).resolve()
    normalized = ' '.join(name.lower().replace('-', ' ').split())
    if normalized in ('proxima centauri', 'proxima centari', 'proxima centauri mod'):
        mod_id = MOD_ID
    elif normalized in ('interstellar', 'interstellar mod'):
        mod_id = 'interstellar'
    else:
        return install_community(root,name,fetch=fetch,offline=offline)
    spec = REGISTRY[mod_id]
    source = 'bundled package (offline)'
    content = None
    if not offline:
        try:
            content = fetch(spec['url'], LIMIT)
            source = spec['name']+' mod repository'
        except (OSError, URLError, UpdateError):
            source = 'bundled package (mod repository unavailable)'
    if content is None:
        with (root/'mod_catalogue'/f'{mod_id}.json').open('rb') as bundled:
            content = bundled.read(LIMIT+1)
    data = validate(content, mod_id)
    return store_package(root,data,content,source,spec)


def store_package(root,data,content,source,spec):
    mod_id=data['id']
    if version((root/'VERSION.txt').read_text()) < version(data['app_min']):
        raise ModError('This mod needs Solar Sim '+data['app_min']+' or newer. Run sol-sim -u first.')
    folder = root/'mods'
    target = folder/(mod_id+'.json')
    if folder.is_symlink() or target.is_symlink():
        raise ModError('The mod folder and package must not be symbolic links.')
    folder.mkdir(exist_ok=True)
    if target.exists():
        try:previous = load(folder, mod_id)
        except ModError:previous = None  # Explicit installation can repair an invalid local package.
        if previous is not None and version(previous['version']) > version(data['version']):
            return 'Kept installed '+spec['name']+' '+previous['version']+'; the available package is older.\nOpen /'+spec['command']+' in the app.'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix='.'+mod_id+'-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    alias = ' (or /proxima centari)' if mod_id == MOD_ID else ''
    return ('Installed '+spec['name']+' '+data['version']+' / '+source+'\n'
            'Start sol-sim, then type /'+spec['command']+alias+'.\n'
            '/'+spec['exit']+' returns to the Solar System. Re-run -m to update the mod.')


def parse_package(content):
    try:
        if len(content)>LIMIT:raise ValueError('Package exceeds 64 KiB.')
        data=json.loads(content)
        if not isinstance(data,dict) or not isinstance(data.get('id'),str):raise ValueError('Package needs a string id.')
        return validate(content,data['id'])
    except (ValueError,TypeError,UnicodeError,RecursionError) as error:
        raise ModError(str(error)) from error


def repository(value):
    """A public GitHub owner/repo; the contents API selects its default branch."""
    match=re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9][A-Za-z0-9_.-]{0,99})',value)
    return match.group(1)+'/'+match.group(2).removesuffix('.git') if match else None


def download_community(source,fetch):
    repo=repository(source)
    url=None
    if source.startswith('https://'):
        try:
            parsed=urlsplit(source)
            port=parsed.port
        except ValueError as error:
            raise ModError('Invalid GitHub HTTPS URL: '+str(error)) from error
        if parsed.username or parsed.password or port not in (None,443) or parsed.query or parsed.fragment:
            raise ModError('Use a plain public GitHub repository or raw JSON HTTPS URL.')
        parts=parsed.path.strip('/').split('/')
        if parsed.hostname=='github.com' and len(parts)==2:
            repo=repository('/'.join(parts))
        elif parsed.hostname=='github.com' and len(parts)>=5 and parts[2]=='blob' and repository('/'.join(parts[:2])):
            url='https://raw.githubusercontent.com/'+'/'.join(parts[:2]+parts[3:])
        elif parsed.hostname=='raw.githubusercontent.com' and len(parts)>=4 and repository('/'.join(parts[:2])):
            url=source
        else:
            raise ModError('Share owner/repo, a github.com/.../blob/... JSON link or a raw.githubusercontent.com JSON link. Other downloads can be installed as local files.')
    if url is not None:
        if not unquote(urlsplit(url).path).lower().endswith('.json'):raise ModError('The download link must point to a .json file.')
        return fetch(url,LIMIT)
    if repo:
        url='https://api.github.com/repos/'+repo+'/contents/solar-mod.json'
        try:
            raw=fetch(url,LIMIT*2)
            if len(raw)>LIMIT*2:raise ValueError('Repository metadata exceeds 128 KiB.')
            metadata=json.loads(raw)
            if not isinstance(metadata,dict) or metadata.get('type')!='file' or metadata.get('encoding')!='base64':
                raise ValueError('Expected a JSON file, not a directory.')
            if type(metadata.get('size')) is not int or not 0<metadata['size']<=LIMIT:
                raise ValueError('Package exceeds 64 KiB or is empty.')
            encoded=metadata.get('content')
            if not isinstance(encoded,str) or len(encoded)>LIMIT*2:raise ValueError('Missing package content.')
            content=base64.b64decode(encoded.replace('\n',''),validate=True)
            if len(content)!=metadata['size'] or len(content)>LIMIT:raise ValueError('Package size mismatch.')
            return content
        except (ValueError,TypeError,UnicodeError,RecursionError) as error:
            raise ModError('Cannot read repository solar-mod.json: '+str(error)) from error
    raise ModError('Unknown mod. Use proxima centauri, interstellar, a local .json file, or GitHub owner/repo. Read sol-sim --mod-tutorial.')


def install_community(root,source,*,fetch=fetch_bytes,offline=False):
    source=source.strip()
    if not source or len(source)>2048:raise ModError('Choose a local JSON file or public GitHub mod repository.')
    local=not source.startswith(('https://','http://')) and (source.lower().endswith('.json') or source.startswith(('./','../','/','~')))
    if local:
        path=Path(source).expanduser()
        if not path.is_file():raise ModError('Unknown mod or missing JSON file: '+source)
        with path.open('rb') as file:content=file.read(LIMIT+1)
        label='local JSON file'
    else:
        if offline:raise ModError('This mod source needs internet. Download its JSON first, then install that local file with --offline -m PATH.')
        try:content=download_community(source,fetch)
        except (OSError,URLError,UpdateError) as error:
            raise ModError('Cannot download mod: '+str(error)+'\nRepository installs require solar-mod.json at the repository root; use a direct file link for other paths.') from error
        label='public GitHub package'
    data=parse_package(content)
    if data['format']==1:
        spec=REGISTRY[data['id']]
    else:
        spec={'name':data['name'],'command':'mod '+data['id'],'exit':'mod exit'}
    result=store_package(root,data,content,label,spec)
    return result+'\nCommunity updates: repeat the same original file/repository install command.'


def installed(folder):
    valid=[];errors=[]
    folder=Path(folder)
    if not folder.is_dir():return valid,errors
    for path in sorted(folder.glob('*.json')):
        try:
            data=load(folder,path.stem)
            valid.append(data)
        except (ModError,OSError,ValueError) as error:
            errors.append((path.name,str(error)))
    return valid,errors


def check_cli(source):
    try:
        with Path(source).expanduser().open('rb') as file:data=parse_package(file.read(LIMIT+1))
        print('Valid mod: '+data.get('name',REGISTRY.get(data['id'],{}).get('name',data['id']))+
              ' / '+data['id']+' / v'+data['version']+' / '+str(len(data['bodies']))+' bodies')
        print('Requires Solar Sim '+data['app_min']+' or newer. Nothing was installed.')
        return 0
    except (OSError,ModError) as error:
        print('Mod validation failed: '+str(error));return 1


def template_cli(root,destination):
    try:
        path=Path(destination).expanduser()
        if path.suffix.lower()!='.json':raise ModError('Choose a .json filename, for example solar-mod.json.')
        content=(Path(root)/'solar-mod.json').read_bytes()
        with path.open('xb') as output:output.write(content)
        print('Created mod template: '+str(path.resolve())+'\nEdit it, then run: sol-sim --check-mod "'+str(path)+'"\nRead sol-sim --mod-tutorial for the full walkthrough.')
        return 0
    except (OSError,ModError) as error:
        print('Could not create template: '+str(error));return 1


def install_cli(root, name, offline=False):
    try:
        print(install(root, name, offline=offline))
        return 0
    except (ModError, OSError) as error:
        print('Mod installation failed: '+str(error))
        return 1
