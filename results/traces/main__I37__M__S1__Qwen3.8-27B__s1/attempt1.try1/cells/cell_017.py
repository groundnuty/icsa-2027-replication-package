import numpy as np, datetime as dt, time, warnings
from numpy.lib.format import open_memmap

t0 = time.time()
ext = np.array(open_memmap('/tmp/mhw/sst_ext.npy', dtype=np.float32, shape=(4028,60,60)), dtype=np.float64)
tgt = np.array(open_memmap('/tmp/mhw/sst_tgt.npy', dtype=np.float32, shape=(92,60,60)), dtype=np.float64)
print("loaded", time.time()-t0)

# dates
def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
print("first ext", ext_dates[0], "last ext", ext_dates[-1], "first tgt", tgt_dates[0], "last tgt", tgt_dates[-1])

def doy_map(d):  # month/day mapping, leap-year calendar
    return dt.date(2000, d.month, d.day).timetuple().tm_yday

doy_ext = np.array([doy_map(d) for d in ext_dates], dtype=np.int64)
doy_tgt = np.array([doy_map(d) for d in tgt_dates], dtype=np.int64)
# baseline block rows 5..4022
doy_b = doy_ext[5:5+4018]
assert doy_b.min() == 1 and doy_b.max() == 366
print("baseline rows:", 5, 5+4017, "doy range ok; doy60 count:", (doy_b==60).sum())

# sea cells: finite on every target day
finite_tgt = np.isfinite(tgt)
sea = finite_tgt.all(axis=0)  # (60,60)
print("sea cells:", sea.sum(), "of", sea.size)
print("per-target-day finite frac (min/max):", finite_tgt.mean(axis=(1,2)).min(), finite_tgt.mean(axis=(1,2)).max())
print("sea frac per month:", [sea.mean() for _ in range(3)])
np.save('/tmp/mhw/sea.npy', sea)
np.save('/tmp/mhw/doy_ext.npy', doy_ext); np.save('/tmp/mhw/doy_tgt.npy', doy_tgt)
