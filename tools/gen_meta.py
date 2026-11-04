"""data/exams.json と sw.js（オフライン用のキャッシュ一覧）を作り直す。データや画面を変えたら実行する。"""
import hashlib, json, os
APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
exams = sys.argv[1:] or sorted([f[:-5] for f in os.listdir(f'{APP}/data') if f.endswith('.json') and f != 'exams.json'], key=lambda e: (e[:4], e[-1] == 'a'), reverse=True)
json.dump(exams, open(f'{APP}/data/exams.json', 'w', encoding='utf-8'))
files = ['./', 'index.html', 'manifest.webmanifest?v=1', 'icons/icon-180.png?v=1', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon.svg?v=1', 'data/exams.json']
files += [f'data/{e}.json' for e in exams]
for e in exams:
    d = f'{APP}/img/{e}'
    if os.path.isdir(d): files += [f'img/{e}/{f}' for f in sorted(os.listdir(d))]
h = hashlib.sha1()
for f in files:
    p = f'{APP}/{f.split("?")[0]}'
    if os.path.isfile(p): h.update(open(p, 'rb').read())
ver = h.hexdigest()[:10]
sw = open(f'{APP}/tools/sw.template.js', encoding='utf-8').read().replace('__VERSION__', ver).replace('__FILES__', json.dumps(files, ensure_ascii=False))
open(f'{APP}/sw.js', 'w', encoding='utf-8').write(sw)
print('exams', exams, 'files', len(files), 'version', ver)
