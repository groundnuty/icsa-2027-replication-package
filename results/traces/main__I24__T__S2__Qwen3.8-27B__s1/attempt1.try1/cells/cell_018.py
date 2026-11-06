import numpy as np, xarray as xr, datetime as dt, warnings

sub = xr.open_dataset("/tmp/mhw/subset.nc")
sst = sub.analysed_sst.values
ts = sub.time.values.astype("datetime64[D]")
o = (ts - ts.astype("datetime64[Y]")).astype("timedelta64[D]").astype(np.int64) + 1
year = ts.astype("datetime64[Y]").astype(np.int64) + 1970
is_leap = (year % 4 == 0) & ((year % 100 != 0) | (year % 400 == 0))
doy = o + np.where(~is_leap & (o > 59), 1, 0)
d2i = {t: i for i, t in enumerate(ts)}

def pool_rows(d):
    b0 = d2i[np.datetime64("1992-01-01")]; b1 = d2i[np.datetime64("2002-12-31")]
    base_idx = np.arange(b0, b1+1)
    bd = doy[base_idx]
    return np.concatenate([np.arange(i-5, i+6) for i in base_idx[bd == d]])

sea = np.load("/tmp/mhw/sea.npy")
thr_s = np.load("/tmp/mhw/thr_s.npy")
clim_s = np.load("/tmp/mhw/clim_s.npy")

i, j = 0, 9  # a sea cell
# wrap check at doy 366 (index 365)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    pres366 = [np.nanpercentile(sst[pool_rows(d), i, j], 90, method="hazen") for d in list(range(351,367)) + list(range(1,16))]
assert not any(np.isnan(pres366))
assert np.allclose(thr_s[365, i, j], float(np.mean(pres366)))
print("smoothing wrap doy366: ok")

# day-60 rule check on sea cell
pre = np.full(366, np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in list(range(1,60))+list(range(61,367)):
        pre[d-1] = np.nanpercentile(sst[pool_rows(d), i, j], 90, method="hazen")
pre[59] = 0.5*(pre[58] + pre[60])
idx = (59-15+np.arange(31)) % 366
assert np.allclose(thr_s[59, i, j], pre[idx].mean())
print("day-60 rule + smoothing at doy60: ok")

# climatology day-60 + smoothing check
prec = np.full(366, np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in list(range(1,60))+list(range(61,367)):
        prec[d-1] = np.nanmean(sst[pool_rows(d), i, j])
prec[59] = 0.5*(prec[58] + prec[60])
assert np.allclose(clim_s[59, i, j], prec[idx].mean())
print("climatology day-60 + smoothing at doy60: ok")

# cross-check full smoothed arrays for this cell by independent convolution
thr_full_check = np.full(366, np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in list(range(1,60))+list(range(61,367)):
        thr_full_check[d-1] = np.nanpercentile(sst[pool_rows(d), i, j], 90, method="hazen")
thr_full_check[59] = 0.5*(thr_full_check[58] + thr_full_check[60])
sm_ref = np.array([thr_full_check[(d-15+np.arange(31)) % 366].mean() for d in range(366)])
assert np.allclose(sm_ref, thr_s[:, i, j])
print("full 366-day smoothed threshold for cell(0,9): identical to pipeline")
print("ALL VERIFICATION OK")
