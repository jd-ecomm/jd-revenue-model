"""Channel driver model: sessions x conversion x AOV by channel, retail months FY26-FY27.
Inputs: channel_daily.csv (Shopify last non-direct click buckets), shopdraft_daily.csv (Shop app + Draft Orders).
Output: channel_months.csv (argv[2]; default /home/claude/prm2/data/channel_months.csv). Run in the folder holding the two CSVs.
Copied from claude/prm-channel-model.md on 13 Nov 2026.
"""
import csv, collections, datetime as dt

D = dt.date.fromisoformat
FY = {'FY25': '2024-02-04', 'FY26': '2025-02-02', 'FY27': '2026-02-01', 'FY28': '2027-01-31'}
ENDS = [4, 9, 13, 17, 22, 26, 30, 35, 39, 43, 48, 52]
MN = ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan']
import sys
LAST = sys.argv[1] if len(sys.argv) > 1 else '2026-10-26'   # last day of data
OUT = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/prm2/data/channel_months.csv'
TREND_WEEKS = 8


def retail(d):
    fy = max(k for k, v in FY.items() if v <= d)
    wk = (D(d) - D(FY[fy])).days // 7 + 1
    mi = next(i for i, e in enumerate(ENDS) if wk <= e)
    return fy, wk, MN[mi] + ' ' + fy


LINES = ['Paid', 'Organic', 'Direct', 'Email', 'Shop app & draft', 'Untracked']
day = collections.defaultdict(lambda: {l: [0.0, 0.0, 0.0] for l in LINES})  # sessions, orders, gross
for r in csv.DictReader(open('channel_daily.csv')):
    c = 'Untracked' if r['channel'] == 'Unknown' else r['channel']
    x = day[r['date']][c]
    x[0] += float(r['sessions']); x[1] += float(r['orders']); x[2] += float(r['gross_sales'])
for r in csv.DictReader(open('shopdraft_daily.csv')):
    u, s = day[r['date']]['Untracked'], day[r['date']]['Shop app & draft']
    o, g = float(r['orders']), float(r['gross_sales'])
    s[1] += o; s[2] += g; u[1] -= o; u[2] -= g
# the 25-27 Apr 2025 tracking outage: sessions collapsed, orders fell into Untracked.
# Rebuild those days from the same weekday a week either side so FY27 has a sane base.
for d in ['2025-04-25', '2025-04-26', '2025-04-27']:
    a, b = (D(d) - dt.timedelta(7)).isoformat(), (D(d) + dt.timedelta(7)).isoformat()
    tot_o = sum(day[d][l][1] for l in LINES); tot_g = sum(day[d][l][2] for l in LINES)
    ref_o = {l: (day[a][l][1] + day[b][l][1]) / 2 for l in LINES}
    ref_g = {l: (day[a][l][2] + day[b][l][2]) / 2 for l in LINES}
    so, sg = sum(ref_o.values()), sum(ref_g.values())
    for l in LINES:
        day[d][l] = [(day[a][l][0] + day[b][l][0]) / 2, tot_o * ref_o[l] / so, tot_g * ref_g[l] / sg]

dates = sorted(day)
cal = {d: retail(d) for d in dates}
# extend calendar for forecast days to end of FY27
d = D(LAST) + dt.timedelta(1)
fut = []
while d < D(FY['FY28']):
    fut.append(d.isoformat()); cal[d.isoformat()] = retail(d.isoformat()); d += dt.timedelta(1)
ly = lambda d: (D(d) - dt.timedelta(364)).isoformat()


def ratios(end):
    """CY/LY driver ratios over the TREND_WEEKS full weeks ending the day before `end`."""
    days = [(D(end) - dt.timedelta(i)).isoformat() for i in range(1, TREND_WEEKS * 7 + 1)]
    out = {}
    for l in LINES:
        c = [sum(day[x][l][i] for x in days) for i in range(3)]
        p = [sum(day[ly(x)][l][i] for x in days) for i in range(3)]
        if l == 'Untracked':   # tracking gap: hold its current share of tracked orders, not a YoY ratio
            tr = sum(day[x][k][1] for x in days for k in LINES[:4])
            out[l] = {'share': c[1] / tr, 'aov': c[2] / c[1]}
        elif l == 'Shop app & draft':
            out[l] = {'o': c[1] / p[1], 'a': (c[2] / c[1]) / (p[2] / p[1])}
        else:
            out[l] = {'s': c[0] / p[0], 'c': (c[1] / c[0]) / (p[1] / p[0]), 'a': (c[2] / c[1]) / (p[2] / p[1])}
    return out


def fc_day(d, R):
    """Forecast one day from last year's same retail day and the ratios."""
    p = day[ly(d)]; out = {}
    for l in LINES:
        s, o, g = p[l]; r = R[l]
        if 'share' in r:
            continue
        if 'o' in r:
            on = o * r['o']; out[l] = [s, on, (g / o if o else 0) * r['a'] * on]
        else:
            sn = s * r['s']; on = o * r['c'] * r['s']; out[l] = [sn, on, (g / o if o else 0) * r['a'] * on]
    r = R['Untracked']; on = sum(out[k][1] for k in LINES[:4]) * r['share']
    out['Untracked'] = [p['Untracked'][0], on, on * r['aov']]   # current share of tracked orders at current AOV
    return out


months = []
for d in dates + fut:
    m = cal[d][2]
    if m.endswith('FY27') and m not in months: months.append(m)
mdays = collections.defaultdict(list)
for d in dates + fut:
    if cal[d][2] in months: mdays[cal[d][2]].append(d)

rows = []
Rnow = ratios((D(LAST) - dt.timedelta((D(LAST).weekday() + 1) % 7)).isoformat())  # window ends the last Saturday on or before LAST
for m in months:
    ds = mdays[m]; start = ds[0]
    Rst = ratios(start) if start <= LAST else Rnow
    done = [x for x in ds if x <= LAST]
    status = 'Actual' if len(done) == len(ds) else ('In progress' if done else 'Forecast')
    for l in LINES:
        act = [sum(day[x][l][i] for x in done) for i in range(3)]
        lyv = [sum(day[ly(x)][l][i] for x in ds) for i in range(3)]
        lyd = [sum(day[ly(x)][l][i] for x in done) for i in range(3)]   # last year, same days as booked
        fst = [sum(fc_day(x, Rst)[l][i] for x in ds) for i in range(3)]          # forecast as at month start
        rest = [sum(fc_day(x, Rnow)[l][i] for x in ds if x > LAST) for i in range(3)]
        exp = [act[i] + rest[i] for i in range(3)]
        rows.append({'month': m, 'line': l, 'status': status, 'days': len(ds), 'days_done': len(done),
                     'sessions': round(exp[0]), 'orders': round(exp[1]), 'gross': round(exp[2]),
                     'act_sessions': round(act[0]), 'act_orders': round(act[1]), 'act_gross': round(act[2]),
                     'lyd_sessions': round(lyd[0]), 'lyd_orders': round(lyd[1]), 'lyd_gross': round(lyd[2]),
                     'ly_sessions': round(lyv[0]), 'ly_orders': round(lyv[1]), 'ly_gross': round(lyv[2]),
                     'fc_sessions': round(fst[0]), 'fc_orders': round(fst[1]), 'fc_gross': round(fst[2])})
cols = list(rows[0].keys())
w = csv.DictWriter(open(OUT, 'w', newline=''), fieldnames=cols)
w.writeheader(); w.writerows(rows)
print('trend ratios now:')
for l, r in Rnow.items(): print(' ', l, {k: round(v, 3) for k, v in r.items()})
for m in months:
    rr = [r for r in rows if r['month'] == m]
    print(m, rr[0]['status'], 'gross', sum(r['gross'] for r in rr), 'fc', sum(r['fc_gross'] for r in rr), 'ly', sum(r['ly_gross'] for r in rr))
