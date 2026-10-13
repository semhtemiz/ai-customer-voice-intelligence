"""Build an audited, clean GitHub source snapshot and ZIP without local Git history."""
import hashlib
import json
import shutil
from datetime import datetime,timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile

try:
    from scripts.public_source import ROOT,files
    from scripts.check_public_security import scan
except ModuleNotFoundError:
    from public_source import ROOT,files
    from check_public_security import scan


def main():
    selected=files()
    findings=scan(selected)
    if findings:raise ValueError('Publication blocked: credential/private-path scan failed; values are not printed')
    output=ROOT/'release';output.mkdir(exist_ok=True)
    destination=output/'github-public'
    # Never move or replace an active publication checkout or its Git history.
    if (destination/'.git').exists():
        destination=output/'github-public-export'
    if destination.exists():
        backup=output/('github-public-backup-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f'))
        destination.rename(backup)
    destination.mkdir()
    manifest=[]
    archive=output/'customer-voice-source.zip'
    with ZipFile(archive,'w',ZIP_DEFLATED) as zipped:
        for path in selected:
            relative=path.relative_to(ROOT);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
            zipped.write(path,relative.as_posix())
            manifest.append({'path':relative.as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
    (output/'manifest.json').write_text(json.dumps({'archive':archive.name,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':manifest},indent=2)+'\n')
    print(f'{len(selected)} audited public files; credentials, raw data, local reports/plans and nested Git history excluded.')
    print(destination)
    print(archive)

if __name__=='__main__':main()
