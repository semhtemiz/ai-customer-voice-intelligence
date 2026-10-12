"""Scan public inventory without printing secret values; optionally verify Git staging."""
import re
import subprocess
from pathlib import Path

try:
    from scripts.public_source import ROOT,files
except ModuleNotFoundError:
    from public_source import ROOT,files

PATTERNS=(
    re.compile(r'(?i)nvapi-[A-Za-z0-9_-]{20,}'),
    re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{20,}'),
    re.compile(r'AKIA[A-Z0-9]{16}'),
    re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}'),
    re.compile(r'github_pat_[A-Za-z0-9_]{20,}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\'),
    re.compile(r"""(?m)^[ \t]*(?:NVIDIA_API_KEY|OPENAI_API_KEY|GITHUB_TOKEN|AWS_SECRET_ACCESS_KEY)[ \t]*=[ \t]*["']?[A-Za-z0-9_/+=.-]{16,}"""),
)
BINARY_SUFFIXES={'.png','.ico'}


def scan(selected, root=ROOT):
    findings=[]
    for path in selected:
        if path.suffix in BINARY_SUFFIXES:continue
        text=path.read_text(encoding='utf-8')
        for index,pattern in enumerate(PATTERNS):
            if pattern.search(text):findings.append((path.relative_to(root).as_posix(),index))
    return findings


def main():
    selected=files();findings=scan(selected)
    if findings:
        for path,rule in findings:print(f'BLOCKED: {path} (rule {rule})')
        raise SystemExit(1)
    # If this is the public Git checkout, check the whole tracked inventory too.
    probe=subprocess.run(['git','rev-parse','--show-toplevel'],cwd=ROOT,capture_output=True,text=True)
    if probe.returncode==0 and Path(probe.stdout.strip()).resolve()==ROOT:
        listing=subprocess.run(['git','ls-files','-z','--stage'],cwd=ROOT,capture_output=True,text=True,check=True)
        allowed={path.relative_to(ROOT).as_posix() for path in selected}
        for entry in listing.stdout.split('\0'):
            if not entry:continue
            info,name=entry.split('\t',1)
            if info.startswith('160000') or name not in allowed:
                raise SystemExit('Unexpected tracked file or embedded repository: '+name)
    print(f'PASS: {len(selected)} public files; no matched credentials, private paths or forbidden publication inputs.')

if __name__=='__main__':main()
