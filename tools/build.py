"""Build the standalone dashboard page from a kit folder.
kit/index.html            page source (files/index.html from the Claude dashboard)
kit/datasets/<name>.json  dataset docs (source.kind file -> blob, query -> lt/<name>.json)
kit/blobs/<id>.<ext>      dataset files and fonts, named by their /_blob id
kit/lt/<name>.json        live Lifetimely series [{date, value}]
Usage: python3 build.py <kit> <out.html>"""
import csv, json, glob, os, re, sys, base64
K, OUT = sys.argv[1], sys.argv[2]
data = {}
for f in glob.glob(K + '/datasets/*.json'):
    n = os.path.basename(f)[:-5]; s = json.load(open(f))['source']
    if s['kind'] == 'file':
        bid = s['url'].split('/')[-1]; p = f"{K}/blobs/{bid}.{s.get('format', 'csv')}"
        data[n] = json.load(open(p)) if s.get('format') == 'json' else list(csv.DictReader(open(p, encoding='utf-8')))
    else:
        data[n] = json.load(open(f'{K}/lt/{n}.json'))
through = max(r['date'] for r in data['lt_sales'])
page = open(K + '/index.html', encoding='utf-8').read()
def font(m):
    p = glob.glob(f"{K}/blobs/{m.group(1)}.*")[0]
    return "url(data:font/woff2;base64," + base64.b64encode(open(p, 'rb').read()).decode() + ")"
page = re.sub(r"url\('/_blob/([0-9a-f]{32})'\)", font, page)
shim = """<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script><script>
window.__DATA=%s;
window.dash=(function(){const calcs={},cache={},cbs=[];const P={through:%s};const api={colors:['#FFDE14','#43D5B0','#FFFFFF','#A7A8A9'],
calc(id,o){calcs[id]=o},loader(){},setParams(){},params(){return P},resetParams(){},setLink(l){try{history.replaceState(null,'','#'+l)}catch(e){}},onData(cb){cbs.push(cb);setTimeout(cb,0)},
data(id){if(cache[id])return cache[id];if(window.__DATA[id])return cache[id]={status:'ok',data:window.__DATA[id]};const c=calcs[id];if(!c)return {status:'error',message:'missing '+id};
const ins=c.inputs.map(i=>api.data(i));if(ins.some(x=>x.status!=='ok'))return cache[id]={status:'error'};try{return cache[id]={status:'ok',data:c.fn(...ins.map(x=>x.data))}}catch(e){console.error('CALC '+id+': '+e.stack);return cache[id]={status:'error'}}}};return api})();
</script>""" % (json.dumps(data, separators=(',', ':')), json.dumps(through))
html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow"><title>Predictive Revenue Model · JD Sports Canada</title>'
        '<style>html,body{background:#000;margin:0}</style></head><body><div id="dash-root">' + shim + page + '</div></body></html>')
open(OUT, 'w', encoding='utf-8').write(html)
print(f'{OUT}: {len(html)//1024} KB, data through {through}')
