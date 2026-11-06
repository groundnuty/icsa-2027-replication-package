
import fsspec, io, h5py, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

BASE = '/icsa2027_data_20261101T090944Z/s1z'
fs = fsspec.filesystem('onedata')

def daterange(a, b):
    out = []
    while a <= b:
        out.append(a); a += timedelta(days=1)
    return out

base_dates = daterange(date(1991,12,27), date(2003,1,5))   # 4028
tgt_dates  = daterange(date(2021,6,1), date(2021,8,31))    # 92
all_dates  = base_dates + tgt_dates
print("base:", len(base_dates), base_dates[0], base_dates[-1])
print("tgt:", len(tgt_dates), tgt_dates[0], tgt_dates[-1])

# grid selection from a sample file
f0 = fs.open(BASE + '/sst_20210701.nc', "rb")
raw0 = f0.read()
h = h5py.File(io.BytesIO(raw0), 'r')
lat_full = h['latitude'][:].astype(np.float64)
lon_full = h['longitude'][:].astype(np.float64)
h.close()
lat_sel = np.where((lat_full >= 61.57 - 1e-6) & (lat_full <= 62.77 + 1e-6))[0]
lon_sel = np.where((lon_full >= 20.17 - 1e-6) & (lon_full <= 21.37 + 1e-6))[0]
print("lat idx:", lat_sel.min(), lat_sel.max(), "n=", len(lat_sel), "values:", lat_full[lat_sel[0]], "->", lat_full[lat_sel[-1]])
print("lon idx:", lon_sel.min(), lon_sel.max(), "n=", len(lon_sel), "values:", lon_full[lon_sel[0]], "->", lon_full[lon_sel[-1]])

lat_region = lat_full[lat_sel]
lon_region = lon_full[lon_sel]

def read_one(d):
    name = 'sst_%04d%02d%02d.nc' % (d.year, d.month, d.day)
    with fs.open(BASE + '/' + name, "rb") as f:
        raw = f.read()
    h = h5py.File(io.BytesIO(raw), 'r')
    a = h['analysed_sst'][0, lat_sel, lon_sel][:].astype(np.float64)
    h.close()
    return a

rows = [None] * len(all_dates)
t0 = time.time()
with ThreadPoolExecutor(max_workers=16) as ex:
    for i, a in enumerate(ex.map(read_one, all_dates)):
        rows[i] = a
        if (i+1) % 500 == 0:
            print(i+1, len(all_dates), "done, elapsed %.1f s" % (time.time()-t0))
master = np.stack(rows[:len(base_dates)])   # (4028, 60, 60)
target = np.stack(rows[len(base_dates):])   # (92, 60, 60)
print("master:", master.shape, master.dtype, "target:", target.shape)
print("finite frac master: %.5f, target: %.5f" % (np.isfinite(master).mean(), np.isfinite(target).mean()))
np.savez_compressed('/tmp/sst_data.npz',
                    master=master, target=target,
                    lat_region=lat_region, lon_region=lon_region)
print("saved. elapsed %.1f s" % (time.time()-t0))
