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

# self-test on baseline summers: use sea cells only (finite in 2012 target); some may have NaN in baseline (ice) -> handle
for (y0, y1) in [(1992, 1997), (1997, 1998), (2000, 2001), (2002, 2003)]:
    d0 = daterange(dt.date(y0, 6, 1), dt.date(y1 - 1 if y1 <= 12 else y1, 8, 31))
    # simpler: pick Jun1-Aug31 of one year
    dates = daterange(dt.date(y0, 6, 1), dt.date(y0, 8, 31))
    idxs = [ext_dates.index(d) for d in dates]
    doys = [doy_ext[i] for i in idxs]
    sst = ext[idxs]                      # (92, 60, 60)
    th = thr[np.array(doys) - 1]
    valid = sea[None] & np.isfinite(sst)
    ex = sst - th
    f_hot = (ex[valid] >= 0).mean()
    # per-cell 5+ runs with 2-day gap joining
    mhw_count = 0
    for (i, j) in np.argwhere(sea):
        b = valid[:, i, j] & (ex[:, i, j] >= 0)
        if not b.any():
            continue
        dd = np.diff(np.concatenate(([0], b.view(np.int8), [0])))
        st = np.flatnonzero(dd == 1); en = np.flatnonzero(dd == -1) - 1
        seeds = np.flatnonzero(en - st + 1 >= 5)
        if seeds.size == 0:
            continue
        mhw_count += 1
        cur_s, cur_e = int(st[seeds[0]]), int(en[seeds[0]])
        for sidx in seeds[1:]:
            if int(st[sidx]) - cur_e - 1 <= 2:
                cur_e = max(cur_e, int(en[sidx]))
            else:
                mhw_count += 1
                cur_s, cur_e = int(st[sidx]), int(en[sidx])
    print(f"baseline summer {y0}: hot fraction = {f_hot:.4f}   cells with >=1 MHW = {mhw_count}, per-cell MHWs = {mhw_count}")
