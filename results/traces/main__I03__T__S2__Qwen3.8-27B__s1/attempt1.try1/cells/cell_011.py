import numpy as np, json
from datetime import date, timedelta
st = np.load('/tmp/mhw_state.npz')
Bf, Tf, thr, clim, thr_s, clim_s, hot, cellmhw, sea = st['Bf'], st['Tf'], st['thr'], st['clim'], st['thr_s'], st['clim_s'], st['hot'], st['cellmhw'], st['sea']

leap = date(2000,1,1)
cal2doy = {( (leap+timedelta(days=d-1)).month, (leap+timedelta(days=d-1)).day ): d for d in range(1,367)}
t_bdates = [date(1991,12,27)+timedelta(days=k) for k in range(Bf.shape[0])]
pos = {d: i for i,d in enumerate(t_bdates)}
t_tdates = [date(2014,6,1)+timedelta(days=k) for k in range(Tf.shape[0])]
t_doy = [cal2doy[(d.month, d.day)] for d in t_tdates]
print('doy map spot: 2014-06-01 ->', cal2doy[(6,1)], '; 2014-08-31 ->', cal2doy[(8,31)], '; 2001-12-31 ->', cal2doy[(12,31)], '; 2000-02-29 ->', cal2doy[(2,29)])
assert t_doy[0]==153 and t_doy[-1]==244

def hazen_manual(x, p=0.9):
    x = np.sort(x[~np.isnan(x)])
    n = x.size
    if n == 0: return np.nan
    h = p*n + 0.5
    if h >= n: return x[-1]
    if h <= 1: return x[0]
    k = int(np.floor(h))
    return x[k-1] + (h-k)*(x[k]-x[k-1])

def indep_pool(c, d):
    m_d, day_d = ((leap+timedelta(days=d-1)).month, (leap+timedelta(days=d-1)).day)
    vals = []
    for y in range(1992, 2003):
        anchor = date(y, m_d, day_d)
        for k in range(-5, 6):
            dt = anchor + timedelta(days=k)
            assert dt in pos, (d, y, dt)
            vals.append(Bf[pos[dt], c])
    return np.array(vals)

sea_idx = np.where(sea)[0]
samples = [(1, sea_idx[0]), (59, sea_idx[100]), (61, sea_idx[200]), (153, sea_idx[500]),
           (200, sea_idx[1500]), (244, sea_idx[3000]), (366, sea_idx[3300]), (366, 0), (365, sea_idx[42])]
ok = True
for d, c in samples:
    p = indep_pool(c, d)
    q_np = np.nanquantile(p, 0.9, method='hazen')
    q_mn = hazen_manual(p)
    m_np = np.nanmean(p); m_mn = p[~np.isnan(p)].mean()
    same = np.isclose(thr[d-1, c], q_np) and np.isclose(thr[d-1, c], q_mn) and np.isclose(clim[d-1, c], m_np)
    ok &= same
    print(f'd={d:3d} c={c:4d} pool={p.size} nan={int(np.isnan(p).sum()):2d} thr={thr[d-1,c]:.6f} ok={same}')
print('POOL CHECK:', 'PASS' if ok else 'FAIL')

ok = True
for d in [1, 2, 60, 61, 153, 244, 351, 365, 366]:
    for c in [sea_idx[0], sea_idx[1500], 0]:
        rows = [ (d-1-15+j) % 366 for j in range(31) ]
        if not np.isclose(thr_s[d-1, c], thr[rows, c].mean()): ok = False; print('MISMATCH smooth thr d', d, c)
        if not np.isclose(clim_s[d-1, c], clim[rows, c].mean()): ok = False; print('MISMATCH smooth clim d', d, c)
print('SMOOTH CHECK:', 'PASS' if ok else 'FAIL')
print('day60 fill check:', np.allclose(thr[59], 0.5*(thr[58]+thr[60])), np.allclose(clim[59], 0.5*(clim[58]+clim[60])))

ok = True
for day in [0, 4, 20, 50, 91]:
    c = sea_idx[777]
    if bool(Tf[day, c] >= thr_s[t_doy[day], c]) != bool(hot[day, c]): ok = False
print('HOT CHECK:', 'PASS' if ok else 'FAIL')

def mhw_closure(h):
    p = np.concatenate(([False], h, [False]))
    d1 = np.diff(p.astype(np.int8))
    s = np.where(d1==1)[0]; e = np.where(d1==-1)[0]-1
    iv = [list(x) for x in zip(s, e) if x[1]-x[0]+1 >= 5]
    changed = True
    while changed:
        changed = False
        for i in range(len(iv)):
            for j in range(len(iv)-1, i, -1):
                gap = iv[j][0] - iv[i][1] - 1
                if 1 <= gap <= 2 and all(iv[k][0] > iv[j][1] or iv[k][1] < iv[i][0] for k in range(len(iv)) if k not in (i, j)):
                    iv[i][1] = iv[j][1]; del iv[j]; changed = True; break
            if changed: break
    return iv

cm2 = np.zeros(Tf.shape, dtype=bool)
short_between = 0
for c in range(Tf.shape[1]):
    h = hot[:, c]
    p = np.concatenate(([False], h, [False])); d1 = np.diff(p.astype(np.int8))
    s = np.where(d1==1)[0]; e = np.where(d1==-1)[0]-1
    runs = [(s_, e_) for s_, e_ in zip(s, e)]
    cands = [r for r in runs if r[1]-r[0]+1 >= 5]
    for (a1,a2),(b1,b2) in zip(cands, cands[1:]):
        for (r1,r2) in runs:
            if r1 > a2 and r2 < b1: short_between += 1
    for s_, e_ in mhw_closure(h):
        cm2[s_:e_+1, c] = True
print('MHW CLOSURE MATCH:', bool((cm2 == cellmhw).all()))
print('short runs strictly between two candidate MHWs (edge cases):', short_between)

act = cm2.any(axis=1)
pa = np.concatenate(([False], act, [False])); da = np.diff(pa.astype(np.int8))
es = np.where(da==1)[0]; ee = np.where(da==-1)[0]-1
ev = [(str(t_tdates[s_].isoformat()), str(t_tdates[e_].isoformat())) for s_, e_ in zip(es, ee)]
print('EVENTS:', json.dumps(ev))
for (o, e_) in ev:
    i0 = t_tdates.index(date.fromisoformat(o)); i1 = t_tdates.index(date.fromisoformat(e_))
    print(o, '->', e_, 'days:', i1-i0+1, 'max cells in MHW on last day:', int(cellmhw[i1].sum()))
print('active days:', int(act.sum()), 'of 92')
print('per-cell MHW durations (sea): min', int(cellmhw.sum(axis=0)[sea].min()), 'max', int(cellmhw.sum(axis=0)[sea].max()))
