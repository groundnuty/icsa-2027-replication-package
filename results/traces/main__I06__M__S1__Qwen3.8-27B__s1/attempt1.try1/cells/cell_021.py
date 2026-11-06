import numpy as np, datetime as dt

TC = np.load("/tmp/mhw/thrcli.npz"); THR = TC["THR"]; sea = TC["sea"]
Z = np.load("/tmp/mhw/loaded.npz"); Vt = Z["Vt"]
mask = np.load("/tmp/mhw/mask.npy").astype(bool)
TG_START = dt.date(2012,6,1)
tgt_dates = [TG_START + dt.timedelta(days=i) for i in range(92)]

base_ord = dt.date(2012,1,1).toordinal()
tdoy2 = np.array([dd.toordinal() - base_ord + 1 for dd in tgt_dates])
leap_month = [31,29,31,30,31,30,31,31,30,31,30,31]
doy_of = {}
for m in range(1,13):
    s = 1
    for mm in range(1,m): s += leap_month[mm-1]
    for day in range(1, leap_month[m-1]+1): doy_of[(m,day)] = s + day - 1
tdoy1 = np.array([doy_of[(dd.month,dd.day)] for dd in tgt_dates])
print("doy methods agree:", bool((tdoy1 == tdoy2).all()),
      "|", tgt_dates[0].isoformat(), tdoy1[0], tdoy2[0], "|", tgt_dates[-1].isoformat(), tdoy1[-1], tdoy2[-1])

def runs_in(h):
    out = []; s = None
    for i, v in enumerate(list(h) + [False]):
        if v and s is None: s = i
        if not v and s is not None: out.append((s, i-1)); s = None
    return out

n_t = 92
m2 = np.zeros((n_t,60,60), dtype=bool)
counts = 0
for r in range(60):
    for c in range(60):
        if not sea[r,c]: continue
        h = [bool(Vt[i,r,c] >= THR[tdoy2[i]-1,r,c]) for i in range(n_t)]
        evs = [x for x in runs_in(h) if x[1]-x[0]+1 >= 5]
        merged = []
        for a,b in evs:
            if merged and a - merged[-1][1] - 1 <= 2: merged[-1] = (merged[-1][0], b)
            else: merged.append((a,b))
        counts += len(merged)
        for a,b in merged: m2[a:b+1, r, c] = True
print("independent per-cell MHW count:", counts, "masks identical:", bool((m2 == mask).all()))

cell_events = {}
for r in range(60):
    for c in range(60):
        if not sea[r,c]: continue
        mm = mask[:, r, c]
        if not mm.any(): continue
        ivs = runs_in(mm.tolist())
        cell_events[(r,c)] = [(tgt_dates[a].isoformat(), tgt_dates[b].isoformat(), b-a+1) for a,b in ivs]
print("cells with MHW:", len(cell_events))
for k in sorted(cell_events, key=lambda k: cell_events[k][0][0]):
    print(k, cell_events[k])
