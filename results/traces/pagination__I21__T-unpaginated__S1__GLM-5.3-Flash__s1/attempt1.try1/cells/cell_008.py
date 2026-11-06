import fsspec, h5py, xarray as xr, numpy as np, datetime as dt, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# raw time attrs
with fs.open(f'{base}/sst_20210601.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        print("time raw attrs:", dict(hf['time'].attrs))
        print("time value:", hf['time'][:])

# xarray vs h5py equality on one file
p = f'{base}/sst_20210615.nc'
with fs.open(p,'rb') as f:
    with h5py.File(f,'r') as hf:
        a = hf['analysed_sst'][0]; la = hf['latitude'][:]; lo = hf['longitude'][:]
with fs.open(p,'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    b = ds['analysed_sst'].values[0]
    print("xarray time:", ds['time'].values)
print("equal:", np.array_equal(a, b, equal_nan=True), a.dtype, b.dtype)

# mapped doy function (leap-referenced)
def mapped_doy(d: dt.date) -> int:
    return (dt.date(2000, d.month, d.day) - dt.date(2000,1,1)).days + 1
tests = {(1992,2,28):59, (1992,2,29):60, (1992,3,1):61, (1993,2,28):59, (1993,3,1):61,
         (1993,12,31):366, (1992,12,31):366, (1992,1,1):1, (2021,6,1):153, (2021,8,31):244}
for (y,m,dd), exp in tests.items():
    got = mapped_doy(dt.date(y,m,dd))
    assert got == exp, (y,m,dd,got,exp)
print("mapped_doy OK")

# read the 92 target days (region slices), time them
t0=time.time()
def read_region(day):
    for attempt in range(4):
        try:
            with fs.open(f'{base}/sst_{day.strftime("%Y%m%d")}.nc','rb') as f:
                with h5py.File(f,'r') as hf:
                    return hf['analysed_sst'][0, 192:252, 2:62].astype(np.float32)
        except Exception as e:
            err = e
    raise err
from concurrent.futures import ThreadPoolExecutor
tgt_days = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
with ThreadPoolExecutor(16) as ex:
    tgt = np.stack(list(ex.map(read_region, tgt_days)))
print("target read %.1fs" % (time.time()-t0), tgt.shape, tgt.dtype)
fin = np.isfinite(tgt)
allfin = fin.all(axis=0); somefin = fin.any(axis=0)
print("cells:", tgt.shape[1]*tgt.shape[2], "finite all days:", allfin.sum(), "finite some:", somefin.sum(),
      "never finite:", (~somefin).sum(), "partial:", (somefin & ~allfin).sum())
print("finite fraction overall:", fin.mean())
np.save('/tmp/tgt.npy', tgt)
