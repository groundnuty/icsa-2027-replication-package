import datetime as dt
import numpy as np

ext = np.load('/work/chk/ext.npy').astype(np.float64)
sea = np.load('/work/chk/sea.npy')
thr = np.load('/work/chk/thr.npy')
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
doy_ext = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in ext_dates])
doy_b = doy_ext[5:5+4018]

# redo explicit check doy 225 -> (8,12)
def explicit_pool(doy, i, j, md):
    m, dd = md
    vals = []
    for y in range(1992, 2003):
        b = dt.date(y, m, dd)
        if dt.date(2000, m, dd).timetuple().tm_yday != doy:
            continue
        for k in range(-5, 6):
            d = b + dt.timedelta(days=k)
            vals.append(ext[ext_dates.index(d), i, j])
    return np.array(vals)

js = np.where(doy_b == 225)[0]
rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
vec = ext[rows, 30, 30]
exp = explicit_pool(225, 30, 30, (8, 12))
print("doy225 (8,12) explicit n:", exp.size, " multiset equal:",
      np.array_equal(np.sort(vec[np.isfinite(vec)]), np.sort(exp[np.isfinite(exp)])))

# correct window: Aug 14..21 2012 -> t = 73..80
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
doy_tgt = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in tgt_dates])
print("t for Aug 14..21:", [t for t in range(92) if str(tgt_dates[t]).startswith('2012-08-1') and tgt_dates[t].day >= 14][:8])
print("\nnorthern cells (lat idx 1-4, lon idx 35-45), Aug 14-21 2012 (excess K):")
hdr = "date    " + " ".join(f"{j:4d}" for j in range(35, 46))
print(hdr)
for t in range(73, 81):
    row = []
    for i in (3,):
        for j in range(35, 46):
            if not sea[i, j]:
                row.append("  --")
            else:
                e = tgt[t, i, j] - thr[doy_tgt[t]-1, i, j]
                row.append(f"{e:+5.1f}")
    print(tgt_dates[t], " ".join(row))

# per-cell hot days in Aug 14-21 for the northern strip
print("\nhot days (SST>=thr) per cell, lat idx 1-4, lon idx 35-45, Aug 14-21:")
for i in range(1, 5):
    for j in range(35, 46):
        if not sea[i, j]:
            continue
        days = [tgt_dates[t].day for t in range(73, 81) if tgt[t, i, j] >= thr[doy_tgt[t]-1, i, j]]
        if days:
            print(f"  ({i},{j}) lon={20.02+j*0.02:.2f} lat={60.10+i*0.02:.2f}: days {days}")
