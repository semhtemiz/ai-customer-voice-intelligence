"""Explicit public source inventory; local work records are never publication inputs."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES=('README.md','LICENSE','THIRD_PARTY_NOTICES.md','SECURITY.md','DOCKER.md',
            '.gitignore','.dockerignore','compose.yaml','dataset/profile.json','dataset/README.md')
BACKEND_FILES=('__init__.py','README.md','Dockerfile','docker-entrypoint.py','requirements.txt',
               'requirements-runtime.txt','pytest.ini','.env.example')
FRONTEND_FILES=('README.md','LICENSE','Dockerfile','.dockerignore','.gitignore','.env.example',
                'package.json','pnpm-lock.yaml','pnpm-workspace.yaml','tsconfig.json',
                'next.config.ts','eslint.config.mjs','postcss.config.mjs','playwright.config.ts','components.json')
BLOCKED_DIRS={'.git','.venv','node_modules','.next','__pycache__','.pytest_cache','test-results','playwright-report'}
BLOCKED_SUFFIXES={'.pyc','.db','.db-shm','.db-wal','.csv','.parquet','.pem','.key','.p12','.pfx','.tsbuildinfo'}


def files(root=ROOT):
    selected=[root/name for name in ROOT_FILES]
    selected += [root/'backend'/name for name in BACKEND_FILES]
    selected += [root/'frontend'/name for name in FRONTEND_FILES]
    for folder in ('backend/app','backend/scripts','backend/sql','backend/tests','frontend/src',
                   'frontend/public','frontend/licenses','frontend/tests','scripts','docs','.github'):
        for path in (root/folder).rglob('*'):
            if not path.is_file():continue
            relative=path.relative_to(root)
            if any(part in BLOCKED_DIRS for part in relative.parts) or path.suffix in BLOCKED_SUFFIXES:continue
            if path.name=='.DS_Store' or (path.name.startswith('.env') and path.name!='.env.example'):continue
            if path.is_symlink():raise ValueError(f'Symlink excluded from public source: {relative}')
            selected.append(path)
    selected.append(root/'screenshots/overview.png')
    for path in selected:
        if path.is_symlink():raise ValueError(f'Symlink excluded from public source: {path.relative_to(root)}')
        if not path.is_file():raise ValueError(f'Missing publication input: {path.relative_to(root)}')
    return sorted(set(selected),key=lambda path:path.relative_to(root).as_posix())
