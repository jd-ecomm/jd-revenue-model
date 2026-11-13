#!/usr/bin/env python3
"""PRM Shopify steps (runbook 2b, 2c, 3b) through the Shopify connector, no browser. Added 13 Nov 2026.

  python3 tools/prm_shopify.py query <yesterday> [--week <Sun>]   -> {"query","variables"} for graphql_query
  python3 tools/prm_shopify.py apply <saved file> <data dir> <yesterday> [--week <Sun>]
      patches channel_daily.csv, shopdraft_daily.csv (last 7 days to yesterday replaced),
      peak_days.csv act_net / act_chk / act_sessions (1 Nov to yesterday), and with --week appends
      the week to shopify_weekly.csv and prints the Shopify net for gap_weekly.

Same ShopifyQL as claude/prm-channel-model.md and the runbook, with GROUP BY day (TIMESERIES is a UI clause).
The saved file is the tool-results file the connector call produced (JSON list of {type,text}) or plain JSON.
"""
import csv, json, sys, datetime as dt
from pathlib import Path

F = 'FROM sales, sessions SHOW sessions, gross_sales, net_sales, orders WHERE {w} GROUP BY day WITH LAST_NON_DIRECT_CLICK_ATTRIBUTION SINCE {s} UNTIL {e} ORDER BY day ASC LIMIT 1000'
BUCKETS = {
    'Email': "marketing_channel IN ('Klaviyo', 'Attentive')",
    'Paid': "(traffic_type = 'paid' AND marketing_channel NOT IN ('Klaviyo', 'Attentive', 'Direct')) OR (traffic_type = 'unknown' AND marketing_channel IN ('Rakuten Ads', 'rakuten', 'spccard', 'linktree', 'linktr'))",
    'Organic': "(traffic_type = 'organic' AND marketing_channel NOT IN ('Klaviyo', 'Attentive', 'Direct')) OR (traffic_type = 'unknown' AND marketing_channel IN ('chatgpt.com', 'ChatGPT', 'Instagram', 'Facebook', 'Google', 'Shop')) OR (traffic_type = 'unknown' AND marketing_platform = 'meta' AND marketing_channel = 'Unattributed')",
    'Direct': "marketing_channel = 'Direct' OR (traffic_type = 'unknown' AND marketing_channel IN ('afterpay', 'klarna', 'paypal')) OR (traffic_type = 'unknown' AND marketing_platform = 'shopify' AND marketing_channel = 'Unattributed')",
}
TOTAL = 'FROM sales, sessions SHOW sessions, gross_sales, orders GROUP BY day WITH LAST_NON_DIRECT_CLICK_ATTRIBUTION SINCE {s} UNTIL {e} ORDER BY day ASC LIMIT 1000'
SHOPDRAFT = "FROM sales SHOW orders, gross_sales, net_sales WHERE sales_channel IN ('Shop', 'Draft Orders') GROUP BY day SINCE {s} UNTIL {e} ORDER BY day ASC LIMIT 1000"
PEAK = 'FROM sales, sessions SHOW sessions, sessions_that_completed_checkout, net_sales GROUP BY day SINCE {s} UNTIL {e} ORDER BY day ASC LIMIT 1000'
WEEK = 'FROM sales, sessions SHOW sessions, sessions_that_completed_checkout, orders, gross_sales, discounts, returns, net_sales GROUP BY day SINCE {s} UNTIL {e} ORDER BY day ASC LIMIT 1000'
D = dt.date.fromisoformat


def items(yday, week=None):
    s = str(D(yday) - dt.timedelta(days=6))
    q = {f'ch_{k.lower()}': F.format(w=w, s=s, e=yday) for k, w in BUCKETS.items()}
    q['ch_total'] = TOTAL.format(s=s, e=yday)
    q['shopdraft'] = SHOPDRAFT.format(s=s, e=yday)
    q['peak'] = PEAK.format(s='2026-11-01', e=yday)
    if week:
        q['week'] = WEEK.format(s=week, e=str(D(week) + dt.timedelta(days=6)))
    # pad: a large query so the answer is always saved to a tool-results file (never retyped); ignored by apply
    q['pad'] = f'FROM sales SHOW net_sales, gross_sales GROUP BY product_id, day SINCE {s} UNTIL {yday} LIMIT 10000'
    return q


def gql(q):
    head = ', '.join(f'${k}: String!' for k in q)
    body = ' '.join(f'{k}: shopifyqlQuery(query: ${k}) {{ tableData {{ columns {{ name }} rows }} parseErrors }}' for k in q)
    return {'query': f'query({head}) {{ {body} }}', 'variables': q}


def load(path):
    raw = json.loads(Path(path).read_text())
    if isinstance(raw, list):
        raw = json.loads(next(x['text'] for x in raw if x.get('text', '').lstrip().startswith('{')))
    if raw.get('errors'):
        raise SystemExit('GraphQL errors: ' + json.dumps(raw['errors'])[:500])
    out = {}
    for k, x in raw['data'].items():
        if k == 'pad':
            continue
        if x.get('parseErrors'):
            raise SystemExit(f'ShopifyQL parse error in {k}: ' + json.dumps(x['parseErrors'])[:300])
        out[k] = {r['day'][:10]: {c.replace('__last_non_direct_click', ''): v for c, v in r.items()} for r in x['tableData']['rows']}
    return out


num = lambda v: float(v or 0)


def patch(path, key, rows, cols, start):
    """Replace rows with key date >= start by `rows` (list of dicts), keep the rest; same columns and line ends."""
    raw = Path(path).read_bytes()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    old = list(csv.DictReader(raw.decode().splitlines()))
    keep = [r for r in old if r[key] < start]
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator=nl)
        w.writeheader(); w.writerows(keep + rows)
    return len(old) - len(keep), len(rows)


def apply(path, ddir, yday, week=None):
    d = load(path); ddir = Path(ddir)
    s = str(D(yday) - dt.timedelta(days=6))
    days = [str(D(s) + dt.timedelta(days=i)) for i in range(7)]
    rows = []
    for day in days:
        four = {k: d[f'ch_{k.lower()}'].get(day, {}) for k in ['Paid', 'Organic', 'Direct', 'Email']}
        for k, r in four.items():
            rows.append({'date': day, 'channel': k, 'sessions': int(num(r.get('sessions'))), 'gross_sales': f"{num(r.get('gross_sales')):.2f}",
                         'net_sales': f"{num(r.get('net_sales')):.2f}", 'orders': int(num(r.get('orders')))})
        t = d['ch_total'].get(day, {})
        rows.append({'date': day, 'channel': 'Unknown',
                     'sessions': int(num(t.get('sessions')) - sum(num(r.get('sessions')) for r in four.values())),
                     'gross_sales': round(num(t.get('gross_sales')) - sum(num(r.get('gross_sales')) for r in four.values()), 2),
                     'net_sales': '', 'orders': int(num(t.get('orders')) - sum(num(r.get('orders')) for r in four.values()))})
    print('channel_daily', patch(ddir / 'channel_daily.csv', 'date', rows, ['date', 'channel', 'sessions', 'gross_sales', 'net_sales', 'orders'], s))
    sd = [{'date': day, 'orders': int(num(d['shopdraft'].get(day, {}).get('orders'))), 'gross_sales': f"{num(d['shopdraft'].get(day, {}).get('gross_sales')):.2f}",
           'net_sales': f"{num(d['shopdraft'].get(day, {}).get('net_sales')):.2f}"} for day in days]
    print('shopdraft_daily', patch(ddir / 'shopdraft_daily.csv', 'date', sd, ['date', 'orders', 'gross_sales', 'net_sales'], s))
    # peak_days: only the three Shopify act_ columns, 1 Nov to yesterday
    p = ddir / 'peak_days.csv'; raw = p.read_bytes(); nl = '\r\n' if b'\r\n' in raw else '\n'
    rd = list(csv.DictReader(raw.decode().splitlines())); cols = list(rd[0].keys()); n = 0
    for r in rd:
        x = d['peak'].get(r['date'])
        if x and r['date'] <= yday:
            r['act_net'] = f"{num(x.get('net_sales')):.2f}"; r['act_chk'] = str(int(num(x.get('sessions_that_completed_checkout')))); r['act_sessions'] = str(int(num(x.get('sessions')))); n += 1
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator=nl); w.writeheader(); w.writerows(rd)
    print('peak_days act_ filled', n)
    if week:
        W = d['week'].values()
        ses = sum(num(r['sessions']) for r in W); chk = sum(num(r['sessions_that_completed_checkout']) for r in W)
        ords = sum(num(r['orders']) for r in W); gross = sum(num(r['gross_sales']) for r in W); disc = sum(num(r['discounts']) for r in W)
        net = sum(num(r['net_sales']) for r in W)
        print(json.dumps({'week_start': week, 'sessions': int(ses), 'checkouts': int(chk), 'cr': round(chk / ses, 5), 'orders': ords,
                          'aov': round((gross + disc) / ords, 2), 'shopify_net': round(net, 2)}))
        print('Add the shopify_weekly row (fy, fy_week, rmonth from the rows above) and the gap_weekly shopify_net yourself.')


if __name__ == '__main__':
    a = sys.argv[1:]
    wk = a[a.index('--week') + 1] if '--week' in a else None
    if a[:1] == ['query']:
        print(json.dumps(gql(items(a[1], wk))))
    elif a[:1] == ['apply']:
        apply(a[1], a[2], a[3], wk)
    else:
        raise SystemExit(__doc__)
