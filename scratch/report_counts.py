import os
import subprocess

excluded_dirs = {'.git', '.venv', 'build', 'dist', '__pycache__', 'logs'}
excluded_exts = {'.pyc', '.pyo'}

ext_counts = {}
local_files = []
local_dirs = []

for root, dirs, files in os.walk('.'):
    parts = root.replace('\\', '/').split('/')
    if any(p in excluded_dirs for p in parts):
        continue
    dirs[:] = [d for d in dirs if d not in excluded_dirs]
    for d in dirs:
        local_dirs.append(d)
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in excluded_exts:
            continue
        rel = os.path.normpath(os.path.join(root, f)).replace('\\', '/')
        local_files.append(rel)
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

git_files = subprocess.check_output(['git', 'ls-files'], text=True).strip().split('\n')
git_files = [f.strip() for f in git_files if f.strip()]

gh_ext_counts = {}
for f in git_files:
    ext = os.path.splitext(f)[1].lower()
    gh_ext_counts[ext] = gh_ext_counts.get(ext, 0) + 1


def count_by_exts(d, exts):
    return sum(d.get(e, 0) for e in exts)


categories = {
    'Python (.py)': ['.py'],
    'QML (.qml)': ['.qml', '.qrc'],
    'JSON (.json)': ['.json'],
    'Images (.png/.jpg/.webp/.ico)': ['.png', '.jpg', '.jpeg', '.webp', '.ico'],
    'Icons (.svg)': ['.svg'],
    'QSS themes (.qss)': ['.qss'],
    'Docs (.md/.txt/.html/.csv)': ['.md', '.txt', '.html', '.csv'],
    'Config (.spec/.ini/.cfg/.toml)': ['.spec', '.ini', '.cfg', '.toml'],
}

all_known_exts = [e for exts_list in categories.values() for e in exts_list]

print('=== FILE COUNTS ===')
for cat, exts in categories.items():
    l = count_by_exts(ext_counts, exts)
    g = count_by_exts(gh_ext_counts, exts)
    status = 'OK' if l == g else 'DIFF'
    print(cat + ': Local=' + str(l) + ', GitHub=' + str(g) + ', ' + status)

other_l = sum(v for k, v in ext_counts.items() if k not in all_known_exts)
other_g = sum(v for k, v in gh_ext_counts.items() if k not in all_known_exts)
print('Other: Local=' + str(other_l) + ', GitHub=' + str(other_g) + ', ' + ('OK' if other_l == other_g else 'DIFF'))

test_py = sum(1 for f in local_files if '/tests/' in f and f.endswith('.py'))
gh_test_py = sum(1 for f in git_files if 'tests/' in f and f.endswith('.py'))
tools_py = sum(1 for f in local_files if '/tools/' in f and f.endswith('.py'))
gh_tools_py = sum(1 for f in git_files if 'tools/' in f and f.endswith('.py'))

print('Tests .py: Local=' + str(test_py) + ', GitHub=' + str(gh_test_py) + ', ' + ('OK' if test_py == gh_test_py else 'DIFF'))
print('Tools .py: Local=' + str(tools_py) + ', GitHub=' + str(gh_tools_py) + ', ' + ('OK' if tools_py == gh_tools_py else 'DIFF'))
print('')
print('Total local eligible files: ' + str(len(local_files)))
print('Total git tracked files: ' + str(len(git_files)))
print('Difference: ' + str(len(local_files) - len(git_files)))

# QML check
qml_local = [f for f in local_files if f.endswith('.qml')]
qml_git = [f for f in git_files if f.endswith('.qml')]
print('')
print('QML local: ' + str(len(qml_local)))
print('QML GitHub: ' + str(len(qml_git)))
