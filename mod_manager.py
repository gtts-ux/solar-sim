"""Install and validate registered, data-only system mods. No mod code is executed."""
import json
import math
import os
from pathlib import Path
import tempfile
from urllib.error import URLError

from catalog import Body
from updater import UpdateError, fetch_bytes, version

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
    spec = REGISTRY[mod_id]
    path = Path(folder)/(mod_id+'.json')
    if not path.is_file():
        raise ModError(spec['name']+' is not installed. In your terminal run: sol-sim -m"'+spec['command']+'"\nThen open /'+spec['command']+' in the app.')
    try:
        with path.open('rb') as source:
            return validate(source.read(LIMIT+1), mod_id)
    except OSError as error:
        raise ModError('Cannot read installed mod: '+str(error)) from error


def bodies(data):
    return [Body(**entry, estimated_mass=bool(index)) for index, entry in enumerate(data['bodies'])]


def install(root, name, *, fetch=fetch_bytes, offline=False):
    root = Path(root).resolve()
    normalized = ' '.join(name.lower().replace('-', ' ').split())
    if normalized in ('proxima centauri', 'proxima centari', 'proxima centauri mod'):
        mod_id = MOD_ID
    elif normalized in ('interstellar', 'interstellar mod'):
        mod_id = 'interstellar'
    else:
        raise ModError('Unknown mod. Available: proxima centauri, interstellar. Use sol-sim -m"interstellar".')
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
    if version((root/'VERSION.txt').read_text()) < version(data['app_min']):
        raise ModError('This mod needs Solar Sim '+data['app_min']+' or newer. Run sol-sim -u first.')
    folder = root/'mods'
    target = folder/(mod_id+'.json')
    if folder.is_symlink() or target.is_symlink():
        raise ModError('The mod folder and package must not be symbolic links.')
    folder.mkdir(exist_ok=True)
    if target.exists():
        previous = load(folder, mod_id)
        if version(previous['version']) > version(data['version']):
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


def install_cli(root, name, offline=False):
    try:
        print(install(root, name, offline=offline))
        return 0
    except (ModError, OSError) as error:
        print('Mod installation failed: '+str(error))
        return 1
