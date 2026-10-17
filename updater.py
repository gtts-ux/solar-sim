"""Install the newest published Solar Sim ZIP, preserving local data and a backup."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid
import zipfile

REPO='gtts-ux/solar-sim'
LATEST=f'https://api.github.com/repos/{REPO}/releases/latest'
MANIFEST='RELEASE_MANIFEST.json'
MAX_DOWNLOAD=32*1024*1024
MAX_EXPANDED=64*1024*1024
PROTECTED={'settings.json','launch_cache.json','ephemeris_cache.json','exports','update-backups',
           '.git','.venv','venv','__pycache__','.solar-sim-update.lock'}
ESSENTIAL={'solar_sim.py','engine.py','VERSION.txt','updater.py','GETTING_STARTED.txt','install_commands.py','Start Solar Sim.sh'}


class UpdateError(Exception):
    pass


def version(text):
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',text.strip())
    if not match:raise UpdateError('Invalid release version: '+text[:60])
    return tuple(map(int,match.groups()))


def trusted_url(url):
    parsed=urlsplit(url)
    host=parsed.hostname or ''
    if (parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443)
        or not (host in ('api.github.com','github.com') or host.endswith('.githubusercontent.com'))):
        raise UpdateError('The release download redirected outside GitHub HTTPS.')


class GitHubRedirects(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        trusted_url(newurl)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def fetch_bytes(url,limit):
    trusted_url(url)
    request=Request(url,headers={'User-Agent':'SolarSim-Updater','Accept':'application/vnd.github+json' if url==LATEST else 'application/octet-stream'})
    if url==LATEST:request.add_header('X-GitHub-Api-Version','2022-11-28')
    with build_opener(GitHubRedirects()).open(request,timeout=20) as response:
        trusted_url(response.geturl())
        if int(response.headers.get('Content-Length') or 0)>limit:
            raise UpdateError('The release download is larger than expected.')
        content=response.read(limit+1)
    if len(content)>limit:raise UpdateError('The release download is larger than expected.')
    return content


def safe_name(name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name:
        raise UpdateError('The release contains an invalid file path.')
    parts=name.split('/')
    if any(p in ('','.','..') or p.endswith((' ','.')) or any(ord(c)<32 for c in p) for p in parts):
        raise UpdateError('The release contains an invalid file path.')
    top=parts[0].casefold()
    if top in PROTECTED or (top.startswith('.') and top not in ('.github','.gitignore','.gitattributes')):
        raise UpdateError('The release tries to replace local data: '+name)
    # Reserved Windows device paths must not be materialized on any platform.
    reserved={'con','prn','aux','nul',*[f'com{i}' for i in range(1,10)],*[f'lpt{i}' for i in range(1,10)]}
    if any(p.split('.')[0].casefold() in reserved for p in parts):
        raise UpdateError('The release contains a reserved file path.')
    return PurePosixPath(name)


def unpack(content,stage,expected_version):
    with zipfile.ZipFile(io.BytesIO(content)) as package:
        members=package.infolist()
        if len(members)>512 or sum(m.file_size for m in members)>MAX_EXPANDED:
            raise UpdateError('The unpacked release is larger than expected.')
        entries={};seen=set()
        for member in members:
            if not member.filename.startswith('solar-sim/'):
                raise UpdateError('The ZIP must contain a solar-sim folder.')
            name=member.filename[len('solar-sim/'):]
            if not name and member.is_dir():continue
            name=name.rstrip('/') if member.is_dir() else name
            safe_name(name)
            folded=name.casefold()
            kind=stat.S_IFMT(member.external_attr>>16)
            if (folded in seen or kind not in (0,stat.S_IFREG,stat.S_IFDIR) or member.flag_bits&1
                or member.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)):
                raise UpdateError('The release contains duplicate, linked or unsupported files.')
            seen.add(folded)
            if not member.is_dir():entries[name]=member
        if MANIFEST not in entries:raise UpdateError('This release does not support automatic updates. Download the latest ZIP manually.')
        if entries[MANIFEST].file_size>128*1024:raise UpdateError('The release manifest is too large.')
        manifest=json.loads(package.read(entries[MANIFEST]))
        if not isinstance(manifest,dict) or manifest.get('format')!=1 or manifest.get('version')!=expected_version:
            raise UpdateError('The release manifest does not match the requested version.')
        files=manifest.get('files')
        minimum=manifest.get('python_min')
        if not isinstance(minimum,list) or len(minimum)!=2 or any(type(n) is not int or n<0 for n in minimum):
            raise UpdateError('The release has an invalid Python requirement.')
        if tuple(minimum)>sys.version_info[:2]:raise UpdateError(f'Install Python {minimum[0]}.{minimum[1]} or newer before updating.')
        if not isinstance(files,list) or not all(isinstance(n,str) for n in files) or len(set(files))!=len(files):
            raise UpdateError('The release has an invalid file list.')
        if set(files)!=set(entries) or not ESSENTIAL<=set(files):
            raise UpdateError('The release is missing required app files or contains unlisted files.')
        for name in files:
            destination=stage.joinpath(*safe_name(name).parts)
            destination.parent.mkdir(parents=True,exist_ok=True)
            data=package.read(entries[name])
            if name.endswith('.py'):compile(data,name,'exec')
            destination.write_bytes(data)
            destination.chmod(0o755 if entries[name].external_attr>>16 & 0o111 else 0o644)
        if (stage/'VERSION.txt').read_text().strip()!=expected_version:
            raise UpdateError('VERSION.txt does not match the release version.')
    probe=subprocess.run([sys.executable,'-B',str(stage/'solar_sim.py'),'--version'],cwd=stage,
                         capture_output=True,text=True,timeout=20)
    if probe.returncode or probe.stdout.strip()!='Solar Sim '+expected_version:
        raise UpdateError('The downloaded app failed its startup check. Your app files were left unchanged.')
    return files


def target_path(root,name):
    path=root
    for part in safe_name(name).parts:
        path=path/part
        if path.is_symlink():raise UpdateError('Cannot update through a symbolic link: '+name)
        if path!=root/name and path.exists() and not path.is_dir():
            raise UpdateError('A file blocks the update directory: '+name)
    if path.exists() and not path.is_file():raise UpdateError('A directory blocks the update file: '+name)
    return path


def install(stage,root,files,current,new_version):
    # Preflight every destination before making a backup or changing any file.
    destinations={name:target_path(root,name) for name in files}
    backups=root/'update-backups'
    if backups.is_symlink():raise UpdateError('The update-backups directory must not be a symbolic link.')
    label=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    backup=backups/(current+'-'+label)
    backup.mkdir(parents=True)
    existing=[]
    for name,target in destinations.items():
        if target.exists():
            saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,saved);existing.append(name)
    (backup/'.restore.json').write_text(json.dumps({'from':current,'to':new_version,'previous_files':existing,'installed_files':files},indent=2)+'\n')
    applied=[]
    try:
        for name in sorted(files,key=lambda n:(n=='VERSION.txt',n)):
            target=destinations[name]
            target.parent.mkdir(parents=True,exist_ok=True)
            os.replace(stage/name,target)
            applied.append(name)
    except BaseException:
        failed=[]
        for name in reversed(applied):
            try:
                if name in existing:os.replace(backup/name,destinations[name])
                else:destinations[name].unlink(missing_ok=True)
            except OSError:failed.append(name)
        if failed:raise UpdateError('Update interrupted; restore previous files from '+str(backup)) from None
        raise
    return backup


def run_update(root,fetch=fetch_bytes,report=print):
    root=Path(root).resolve()
    lock=root/'.solar-sim-update.lock'
    try:handle=lock.open('x')
    except FileExistsError:
        raise UpdateError('Another update may be running. If it was interrupted, remove '+str(lock)+' and try again.') from None
    try:
        with handle:handle.write(str(os.getpid()))
        current=(root/'VERSION.txt').read_text().strip()
        current_number=version(current)
        report('Checking the latest Solar Sim release...')
        release=json.loads(fetch(LATEST,2*1024*1024))
        if not isinstance(release,dict) or release.get('draft') or release.get('prerelease'):
            raise UpdateError('No stable published release is available.')
        tag=release.get('tag_name')
        if not isinstance(tag,str):raise UpdateError('GitHub returned an invalid release version.')
        latest_number=version(tag);latest=tag.lstrip('v')
        if latest_number<=current_number:
            report(f'Already up to date: Solar Sim {current}.' if latest_number==current_number else
                   f'Solar Sim {current} is newer than the latest published release ({latest}); left unchanged.')
            return None
        assets=release.get('assets')
        if not isinstance(assets,list):raise UpdateError('This release has no download assets.')
        def asset(name):
            matches=[a for a in assets if isinstance(a,dict) and a.get('name')==name and a.get('state')=='uploaded']
            if len(matches)!=1:raise UpdateError('The release is missing '+name+'. Try again after publishing finishes.')
            result=matches[0]
            if result.get('browser_download_url')!=f'https://github.com/{REPO}/releases/download/{tag}/{name}':
                raise UpdateError('The release download URL does not match the Solar Sim repository.')
            return result
        archive=asset('solar-sim.zip');checksum=asset('solar-sim.zip.sha256')
        report(f'Downloading Solar Sim {latest}...')
        check=fetch(checksum['browser_download_url'],4096).decode('ascii').strip()
        match=re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?solar-sim\.zip',check)
        if not match:raise UpdateError('The published checksum is invalid.')
        digest=match[1].lower()
        if archive.get('digest') not in (None,'sha256:'+digest):raise UpdateError('GitHub and the checksum file disagree. No app files changed.')
        content=fetch(archive['browser_download_url'],MAX_DOWNLOAD)
        if hashlib.sha256(content).hexdigest()!=digest:raise UpdateError('Download checksum failed. No app files changed; try sol-sim -u again.')
        with tempfile.TemporaryDirectory(prefix='.solar-sim-stage-',dir=root) as temp:
            stage=Path(temp)
            report('Verifying files and checking startup...')
            files=unpack(content,stage,latest)
            report('Installing update...')
            backup=install(stage,root,files,current,latest)
        report(f'Updated Solar Sim {current} -> {latest}. Settings, caches and exports were preserved.')
        report('Previous app files: '+str(backup))
        report('Start the new version with sol-sim.')
        return backup
    finally:lock.unlink(missing_ok=True)


def update_cli(root):
    try:
        run_update(root)
        return 0
    except HTTPError as error:
        if error.code in (403,429):message='GitHub rate limit reached. Wait a few minutes and retry.'
        elif error.code==404:message='No downloadable release is available yet.'
        else:message=f'GitHub returned HTTP {error.code}. Try again later.'
    except (URLError,TimeoutError) as error:
        message='Could not reach GitHub. Check your internet connection and retry. '+str(error)
    except (UpdateError,OSError,ValueError,UnicodeError,zipfile.BadZipFile,SyntaxError,subprocess.SubprocessError) as error:
        message=str(error)
    except KeyboardInterrupt:
        message='Update cancelled.'
    print('Could not update Solar Sim: '+message,file=sys.stderr)
    return 1
