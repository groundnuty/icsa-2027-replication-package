import datetime as dt
import numpy as np

ext = np.load('/work/chk/ext.npy').astype(np.float64)
sea = np.load('/work/chk/sea.npy')
thr = np.load('/work/chk/thr.npy')

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
doy_ext = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in ext_dates])
doy_b = doy_ext[5:5+4018]

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

# note: for doy > 60 the (m,dd) is the same in all years; doy 183 -> (7,1), 225 -> (8,13), 244 -> (8,31)
checks = [(183, (7,1), (30,30)), (225, (8,13), (30,30)), (244, (8,31), (10,40)), (153, (6,1), (55,10)), (200, (7,18), (10,40))]
for doy, md, (i, j) in checks:
    js = np.where(doy_b == doy)[0]
    rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
    vec = ext[rows, i, j]
    exp = explicit_pool(doy, i, j, md)
    same = np.array_equal(np.sort(vec[np.isfinite(vec)]), np.sort(exp[np.isfinite(exp)]))
    print(f"doy {doy} cell ({i},{j}): vec n={vec.size} exp n={exp.size} multiset equal: {same}")

# fine-grained raw threshold at (30,30) and (10,40)
def raw_thr(doy, i, j):
    js = np.where(doy_b == doy)[0]
    rows = (5 + js[:, None] + np.arange(-5, 6)[None, :]).ravel()
    return np.nanquantile(ext[rows, i, j], 0.9, method='hazen')

print("\nraw thr (30,30) doy 180..250 step 2:")
print(" ".join(f"{d}:{raw_thr(d,30,30):.1f}" for d in range(180, 251, 2)))
print("\nraw thr (10,40) doy 180..250 step 2:")
print(" ".join(f"{d}:{raw_thr(d,10,40):.1f}" for d in range(180, 251, 2)))

# the northern cluster hot days
tgt = np.load('/work/chk/tgt.npy').astype(np.float64)
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
doy_tgt = np.array([dt.date(2000, d.month, d.day).timetuple().tm_yday for d in tgt_dates])
print("\nnorthern cells Aug 15-21 (lat idx 2-4, lon idx 36-44):")
for t in range(55, 62):  # Aug 15..21
    row = []
    for i in range(2, 5):
        for j in range(36, 45):
            if not sea[i, j]:
                row.append("--")
            else:
                e = tgt[t, i, j] - thr[doy_tgt[t]-1, i, j]
                row.append(f"{e:+.1f}")
    print(tgt_dates[t], " ".join(row))
