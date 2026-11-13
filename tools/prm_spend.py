#!/usr/bin/env python3
"""PRM peak_days act_spend = self-funded ad spend (Google + Meta, co-op and NSO removed), from connectors. Added 13 Nov 2026.

Replaces reading the Weekly Reporting Looker report (Spend vs Sales, Total Ad Spend). Tested 13 Nov: for 1 to 8 Nov this
equals the Looker figure to within $2 a day (Looker's total is Google + Meta self-funded only).

  python3 tools/prm_spend.py apply <google values file> <meta file> <peak_days.csv> <yesterday>

google values file: the saved result of Google Sheets get_values on "JD Ads - Campaign Daily"
  (1StJm3zbN0MORRJYzuY4vzOP8FyUTbBeEcgNEvJaXH7Q), range data!A<n>:H<last> covering 1 Nov to yesterday
  (columns date, campaign_id, campaign, channel, campaign_status, impressions, clicks, cost).
meta file: the saved result of Meta ads_get_ad_entities, account 1101395547052286, level campaign, fields id, name,
  amount_spent, time_range <yesterday minus 3> to yesterday, time_increment "1", filter amount_spent > 0, limit 100
  (all pages; several files comma-separated). A small answer comes back inline: save its JSON text unchanged to a file.
Days covered by both files are refilled (the daily run refreshes yesterday and the 3 days before); older days are kept.
Either may be a tool-results file (JSON) or the JSON text itself. Only act_spend changes; every other column is kept.
"""
import csv, json, re, sys, collections
from pathlib import Path

COOP = re.compile(r'(^|_)coop(_|$)|co-op|(^|_)nso(_|$)', re.I)   # same rule as the Lifetimely fallback


def jload(path):
    t = Path(path).read_text()
    x = json.loads(t)
    if isinstance(x, list) and x and isinstance(x[0], dict) and 'text' in x[0]:
        x = json.loads(next(i['text'] for i in x if i.get('text', '').lstrip()[:1] in '{['))
    return x


def google(path):
    rows = jload(path)['values']
    out = collections.defaultdict(float)
    for r in rows:
        if len(r) < 8 or not re.match(r'\d{4}-\d\d-\d\d', r[0]):
            continue
        if not COOP.search(r[2]):
            out[r[0]] += float(r[7] or 0)
    return out


def meta(paths):
    out = collections.defaultdict(float)
    for p in paths.split(','):
        x = jload(p)
        ents = x['ad_entities']
        ents = json.loads(ents) if isinstance(ents, str) else ents
        for e in ents:
            if not COOP.search(e['name']):
                out[e['date_start']] += float(e['amount_spent']['value'] or 0)
    return out


def apply(gfile, mfile, peak, yday):
    g, m = google(gfile), meta(mfile)
    if yday not in g or yday not in m:
        raise SystemExit(f'no {"Google" if yday not in g else "Meta"} spend for {yday} yet')
    p = Path(peak); raw = p.read_bytes(); nl = '\r\n' if b'\r\n' in raw else '\n'
    rows = list(csv.DictReader(raw.decode().splitlines())); cols = list(rows[0].keys()); n = 0
    for r in rows:
        d = r['date']
        if '2026-11-01' <= d <= yday and d in g and d in m:   # only days both sources cover; older days keep their value
            r['act_spend'] = f'{g[d] + m[d]:.2f}'; n += 1
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator=nl); w.writeheader(); w.writerows(rows)
    print(json.dumps({'filled': n, 'last': yday, 'google': round(g.get(yday, 0), 2), 'meta': round(m.get(yday, 0), 2)}))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['apply'] and len(a) == 5:
        apply(*a[1:])
    else:
        raise SystemExit(__doc__)
