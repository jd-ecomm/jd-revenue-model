"""Publish the daily refresh by patching only what changed into the live page.
The dashboard's daily refresh swaps a handful of dataset files; everything else
(page code, fonts, other datasets) stays as built. This keeps the daily publish to a
few downloads instead of rebuilding from ~50 files.

Usage: python3 tools/patch_site.py <work-dir>
<work-dir>/datasets.json   ArtifactData list of collection "datasets": [{"id":..., "data": {...}}, ...]
<work-dir>/blobs/<id>.<ext> the dataset files whose blob id differs from tools/blob_manifest.json
<work-dir>/lt/<name>.json   Lifetimely series [{date, value}] for every dataset with source.kind "query"
Writes index.html and tools/blob_manifest.json in place. Exits non-zero (writing nothing) on any gap."""
import csv, json, os, re, sys
W = sys.argv[1]
MAN = 'tools/blob_manifest.json'
html = open('index.html', encoding='utf-8').read()
m = re.search(r'window\.__DATA=(\{.*?\});\nwindow\.dash=', html, re.S)
if not m: sys.exit('could not find window.__DATA in index.html')
data = json.loads(m.group(1))
man = json.load(open(MAN)) if os.path.exists(MAN) else {}
docs = json.load(open(f'{W}/datasets.json'))
docs = {d['id']: d['data'] for d in docs}
changed, need = [], []
for n, d in docs.items():
    s = d['source']
    if s['kind'] == 'file':
        bid = s['url'].split('/')[-1]
        if man.get(n) == bid and n in data: continue
        p = f"{W}/blobs/{bid}.{s.get('format', 'csv')}"
        if not os.path.exists(p): need.append(f'{n} {bid}'); continue
        data[n] = json.load(open(p)) if s.get('format') == 'json' else list(csv.DictReader(open(p, encoding='utf-8')))
        man[n] = bid; changed.append(n)
    else:
        p = f'{W}/lt/{n}.json'
        if not os.path.exists(p): need.append(f'{n} (Lifetimely)'); continue
        data[n] = json.load(open(p)); changed.append(n)
if need: sys.exit('missing inputs, nothing written: ' + '; '.join(need))
through = max(r['date'] for r in data['lt_sales'])
new = html[:m.start(1)] + json.dumps(data, separators=(',', ':')) + html[m.end(1):]
new = re.sub(r'const P=\{through:"[0-9-]+"\}', 'const P={through:%s}' % json.dumps(through), new, count=1)
open('index.html', 'w', encoding='utf-8').write(new)
json.dump(man, open(MAN, 'w'), indent=0, sort_keys=True)
print(f'patched {len(changed)} datasets ({", ".join(sorted(changed))}); data through {through}')
