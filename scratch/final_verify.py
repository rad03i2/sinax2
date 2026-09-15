"""
SINAX GitHub Mirror - Full Verification Script
Compares local eligible project files vs git tracked files vs origin/main
"""
import os
import subprocess
import sys

EXCLUDED_DIRS = {'.git', '.venv', 'venv', 'env', 'ENV', 'build', 'dist',
                 '__pycache__', 'logs', 'temp', 'tmp', '.pytest_cache',
                 '.mypy_cache', '.ruff_cache', 'htmlcov', '.cache'}
EXCLUDED_EXTS = {'.pyc', '.pyo', '.pyd', '.log', '.coverage'}


def scan_local():
    local_files = []
    local_dirs = set()
    for root, dirs, files in os.walk('.'):
        parts = root.replace('\\', '/').lstrip('./').split('/')
        if any(p in EXCLUDED_DIRS for p in parts):
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for d in dirs:
            local_dirs.add(d)
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXCLUDED_EXTS:
                continue
            rel = os.path.normpath(os.path.join(root, f)).replace('\\', '/').lstrip('./')
            local_files.append(rel)
    return local_files, local_dirs


def get_git_tracked():
    out = subprocess.check_output(['git', 'ls-files'], text=True, encoding='utf-8')
    return [f.strip().replace('\\', '/') for f in out.strip().split('\n') if f.strip()]


def get_untracked():
    out = subprocess.check_output(
        ['git', 'ls-files', '--others', '--exclude-standard'], text=True, encoding='utf-8')
    return [f.strip().replace('\\', '/') for f in out.strip().split('\n') if f.strip()]


def get_origin_main_files():
    # get list of files on origin/main via git ls-tree
    out = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', 'origin/main'], text=True, encoding='utf-8')
    return [f.strip().replace('\\', '/') for f in out.strip().split('\n') if f.strip()]


def count_by_ext(files, exts):
    return sum(1 for f in files if os.path.splitext(f)[1].lower() in exts)


def count_by_path(files, prefix):
    return sum(1 for f in files if f.startswith(prefix))


def git_status_clean():
    out = subprocess.check_output(['git', 'status', '--short'], text=True, encoding='utf-8')
    return out.strip() == '', out.strip()


def main():
    print("=" * 60)
    print("SINAX PYTHON — FINAL GITHUB MIRROR VERIFICATION")
    print("=" * 60)
    print()

    local_files, local_dirs = scan_local()
    git_files = get_git_tracked()
    origin_files = get_origin_main_files()
    untracked = get_untracked()

    local_set = set(local_files)
    git_set = set(git_files)
    origin_set = set(origin_files)

    diff_local_git = sorted(local_set - git_set)
    diff_git_local = sorted(git_set - local_set)
    diff_local_origin = sorted(local_set - origin_set)

    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    origin_sha = subprocess.check_output(['git', 'rev-parse', 'origin/main'], text=True).strip()

    is_clean, status_out = git_status_clean()

    print(f"Local eligible files:          {len(local_files)}")
    print(f"Git tracked files:             {len(git_files)}")
    print(f"Files on origin/main:          {len(origin_files)}")
    print(f"Difference Local vs Git:       {len(diff_local_git)} local-only, {len(diff_git_local)} git-only")
    print(f"Difference Local vs origin:    {len(diff_local_origin)}")
    print()
    print(f"git status:                    {'CLEAN' if is_clean else 'DIRTY'}")
    if not is_clean:
        print(f"  -> {status_out}")
    print(f"HEAD:                          {head}")
    print(f"origin/main:                   {origin_sha}")
    print(f"HEAD == origin/main:           {'YES' if head == origin_sha else 'NO'}")
    print()

    # Untracked important files (filter out obvious junk)
    ignore_untracked_prefixes = ['.venv/', 'build/', 'dist/', '__pycache__/', 'logs/']
    important_untracked = [
        f for f in untracked
        if not any(f.startswith(p) for p in ignore_untracked_prefixes)
    ]
    print(f"Untracked important files:     {len(important_untracked)}")
    for f in important_untracked[:20]:
        print(f"  ! {f}")
    print()

    # Local only (not in git)
    print(f"Local-only files (not in git): {len(diff_local_git)}")
    for f in diff_local_git[:20]:
        print(f"  + {f}")
    print()

    # Git only (not local)
    print(f"Git-only files (not local):    {len(diff_git_local)}")
    for f in diff_git_local[:20]:
        print(f"  - {f}")
    print()

    # Large files check
    print("Large file check (>10MB in local eligible):")
    large = []
    for f in local_files:
        try:
            sz = os.path.getsize(f)
            if sz > 10 * 1024 * 1024:
                large.append((f, sz // (1024*1024)))
        except Exception:
            pass
    if large:
        for f, mb in large:
            print(f"  {f} ({mb} MB)")
    else:
        print("  None")
    print()

    # Nested .git repos
    print("Nested repositories (.git in subfolders):")
    nested = []
    for root, dirs, files in os.walk('.'):
        if root == '.':
            continue
        if '.git' in dirs and root != '.':
            nested.append(root)
    if nested:
        for n in nested:
            print(f"  ! {n}")
    else:
        print("  None")
    print()

    # File type breakdown
    py_local = count_by_ext(local_files, {'.py'})
    py_git = count_by_ext(git_files, {'.py'})
    qml_local = count_by_ext(local_files, {'.qml'})
    qml_git = count_by_ext(git_files, {'.qml'})
    svg_local = count_by_ext(local_files, {'.svg'})
    svg_git = count_by_ext(git_files, {'.svg'})
    img_local = count_by_ext(local_files, {'.png', '.jpg', '.jpeg', '.webp', '.ico'})
    img_git = count_by_ext(git_files, {'.png', '.jpg', '.jpeg', '.webp', '.ico'})
    json_local = count_by_ext(local_files, {'.json'})
    json_git = count_by_ext(git_files, {'.json'})
    qss_local = count_by_ext(local_files, {'.qss'})
    qss_git = count_by_ext(git_files, {'.qss'})
    doc_local = count_by_ext(local_files, {'.md', '.txt', '.html', '.csv'})
    doc_git = count_by_ext(git_files, {'.md', '.txt', '.html', '.csv'})

    tests_local = count_by_path(local_files, 'tests/')
    tests_git = count_by_path(git_files, 'tests/')
    tools_local = count_by_path(local_files, 'tools/')
    tools_git = count_by_path(git_files, 'tools/')
    res_local = count_by_path(local_files, 'resources/')
    res_git = count_by_path(git_files, 'resources/')

    print(f"{'Category':<30} {'Local':>8} {'GitHub':>8} {'Match':>8}")
    print("-" * 58)

    def row(cat, l, g):
        ok = 'OK' if l == g else 'DIFF'
        print(f"{cat:<30} {l:>8} {g:>8} {ok:>8}")

    row("QML (.qml)", qml_local, qml_git)
    row("Python (.py)", py_local, py_git)
    row("Icons (.svg)", svg_local, svg_git)
    row("Images (.png/.jpg/etc)", img_local, img_git)
    row("JSON (.json)", json_local, json_git)
    row("QSS themes (.qss)", qss_local, qss_git)
    row("Docs (.md/.txt/.html/.csv)", doc_local, doc_git)
    row("Tests/ files", tests_local, tests_git)
    row("Tools/ files", tools_local, tools_git)
    row("Resources/ files", res_local, res_git)
    print()

    # Critical path checks
    critical = [
        'main.py', 'requirements.txt', 'SINAX.spec', 'README.md',
        'THIRD_PARTY_NOTICES.md', '.gitignore'
    ]
    critical_dirs = ['app', 'docs', 'tests', 'tools', 'resources']

    print("Critical file/dir checks:")
    for c in critical:
        present = c in git_set
        print(f"  {c}: {'PRESENT' if present else 'MISSING'}")
    for d in critical_dirs:
        count = count_by_path(git_files, d + '/')
        print(f"  {d}/: {'PRESENT (' + str(count) + ' files)' if count > 0 else 'MISSING'}")
    print()

    # Requirements check
    req = open('requirements.txt', encoding='utf-8').read().lower()
    deps = ['pyside6', 'send2trash', 'pypdf', 'python-docx', 'openpyxl', 'pillow', 'imagehash', 'psutil']
    print("requirements.txt dependency check:")
    for dep in deps:
        found = dep in req
        print(f"  {dep}: {'PRESENT' if found else 'MISSING'}")
    print()

    # Final verdict
    complete = (
        len(diff_local_git) == 0 and
        len(diff_git_local) == 0 and
        is_clean and
        head == origin_sha and
        len(important_untracked) == 0 and
        not large and
        not nested
    )
    intentional_excluded = ['(.venv, build, dist, logs, __pycache__ excluded intentionally)']

    print("=" * 60)
    if complete:
        print("GITHUB MIRROR STATUS: COMPLETE WITH INTENTIONAL EXCLUSIONS")
        for e in intentional_excluded:
            print(f"  {e}")
    else:
        issues = []
        if diff_local_git:
            issues.append(f"  - {len(diff_local_git)} local files not in git")
        if diff_git_local:
            issues.append(f"  - {len(diff_git_local)} git files not local")
        if not is_clean:
            issues.append("  - git status is DIRTY")
        if head != origin_sha:
            issues.append("  - HEAD != origin/main")
        if important_untracked:
            issues.append(f"  - {len(important_untracked)} important untracked files")
        if large:
            issues.append(f"  - {len(large)} large files not uploaded")
        print("GITHUB MIRROR STATUS: INCOMPLETE")
        for i in issues:
            print(i)
    print("=" * 60)


if __name__ == '__main__':
    main()
