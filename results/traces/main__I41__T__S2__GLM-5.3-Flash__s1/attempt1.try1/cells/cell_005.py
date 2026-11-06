import numpy as np, h5py, fsspec, datetime as dt

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
h5 = h5py.File(f, 'r')
dset = h5['analysed_sst']
print("fillvalue attr:", dset.fillvalue, "| attrs:", dict(dset.attrs))

# raw read of a target day region: check for fill values vs NaN
idx_target0 = (dt.date(2021,6,1) - dt.date(1982,1,1)).days
print("index of 2021-06-01:", idx_target0)
raw = dset[idx_target0, 404:464, 559:619]
print("dtype:", raw.dtype, "NaN count:", np.isnan(raw).sum(), "of", raw.size)
print("min/max finite:", np.nanmin(raw), np.nanmax(raw))
# any values equal to fillvalue?
fv = dset.fillvalue
print("count == fillvalue:", np.sum(raw == fv) if np.isscalar(fv) else 0)
# global scale_factor/add_offset?
print("has scale_factor:", 'scale_factor' in dset.attrs, "add_offset:", 'add_offset' in dset.attrs)

# check a known land point (island in the region?) - just print a small patch
print("corner patch (5x5) of 2021-06-01:\n", np.round(raw[:5,:5],2))
h5.close(); f.close()

# doy function check
def doy_of(d: dt.date) -> int:
    # special calendar: leap-year-style day of year (Feb29=60, Mar1=61 always)
    base = dt.date(d.year, 1, 1)
    n = (d - base).days + 1
    if d.month > 2 or (d.month == 2 and d.day == 29):
        n += 1  # account for the non-existent Feb 29 in non-leap years
    return n

tests = {(1992,1,1):1, (1992,2,28):59, (1992,2,29):60, (1992,3,1):61, (1992,12,31):366,
         (1993,2,28):59, (1993,3,1):61, (1993,12,31):366, (2000,2,29):60, (2000,3,1):61,
         (2021,6,1):153, (2021,8,31):244, (1996,3,1):61}
for (y,m,dd), exp in tests.items():
    got = doy_of(dt.date(y,m,dd))
    print((y,m,dd), "->", got, "expected", exp, "OK" if got==exp else "MISMATCH")
