script = r'''
import numpy as np, xarray as xr, json, os, warnings

os.makedirs('/work/output', exist_ok=True)

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
times = ds['time'].values.astype('datetime64[D]')
lat = ds['latitude'].values; lon = ds['longitude'].values

LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 61.57, 62.77, 20.17, 21.37
tol = 1e-5
latm = (lat >= LAT_MIN - tol) & (lat <= LAT_MAX + tol)
lonm = (lon >= LON_MIN - tol) & (lon <= LON_MAX + tol)
li, lo = np.where(latm)[0], np.where(lonm)[0]
print("region cells:", len(li), "x", len(lo), "=", len(li)*len(lo))

def tidx(d):
    return int(np.searchsorted(times, np.datetime64(d, 'D')))

# ---- day of year by month and day (leap-year calendar: 1 Jan=1 ... 31 Dec=366) ----
def doy_of(dates):
    dates = dates.astype('datetime64[D]')
    y = (dates.astype('datetime64[Y]')).astype('int64')
    start = dates.astype('datetime64[Y]')
    md = (dates - start).astype('int64')  # days since Jan 1 of that year
    leap = (y % 4 == 0) & ((y % 100 != 0) | (y % 400 == 0))
    on_or_after_mar1 = (dates >= start + np.timedelta64(59, 'D'))
    return (md + 1 + np.where(leap, 0, np.where(on_or_after_mar1, 1, 0))).astype(np.int64)

# sanity checks on doy mapping
chk = np.array(['1992-01-01','1992-02-28','1992-02-29','1993-03-01','2000-12-31','2021-06-01','2021-08-31'], dtype='datetime64[D]')
print("doy check:", doy_of(chk), "expect [1 59 60 61 366 153 244]")

# ---- baseline window: 1991-12-27 .. 2003-01-05 ----
t0b, t1b = tidx('1991-12-27'), tidx('2003-01-05')
assert times[t0b] == np.datetime64('1991-12-27') and times[t1b] == np.datetime64('2003-01-05')
Xw = ds['analysed_sst'].isel(time=slice(t0b, t1b + 1), latitude=li, longitude=lo).values.astype(np.float64)
T = Xw.shape[0]
assert T == 4093, T
C = Xw.shape[1]
print("window days:", T, "cells:", C, "window NaNs:", int(np.isnan(Xw).sum()))

# ---- target period 2021-06-01 .. 2021-08-31 ----
t0t, t1t = tidx('2021-06-01'), tidx('2021-08-31')
assert times[t0t] == np.datetime64('2021-06-01') and times[t1t] == np.datetime64('2021-08-31')
Xt = ds['analysed_sst'].isel(time=slice(t0t, t1t + 1), latitude=li, longitude=lo).values.astype(np.float64)
assert Xt.shape[0] == 92, Xt.shape
print("target days:", Xt.shape[0], "target NaNs:", int(np.isnan(Xt).sum()))
ds.close()

# ---- sea cells ----
sea = np.isfinite(Xt).all(axis=0)
print("sea cells:", int(sea.sum()), "land/other:", int((~sea).sum()))

# ---- build pool mask M[d, p]: pool date p (window) belongs to doy d if some baseline q with doy(q)=d is within +-5 days ----
wstart = np.datetime64('1991-12-27', 'D')
wdates = wstart + np.arange(T, dtype='int64') * np.timedelta64(1, 'D')
bdates = np.datetime64('1992-01-01') + np.arange(4018, dtype='int64') * np.timedelta64(1, 'D')
bend = bdates[-1]
print("baseline first/last:", bdates[0], bend)
assert bend == np.datetime64('2002-12-31')
b_doy = doy_of(bdates)
qidx = np.arange(5, 5 + 4018)  # indices of baseline dates inside the window
M = np.zeros((366, T), dtype=bool)
for k in range(-5, 6):
    M[b_doy - 1, qidx + k] = True
psizes = M.sum(axis=1)
print("pool size day60:", psizes[59], " others:", psizes[59].size,
      "min/max non-60:", psizes[:59].min(), psizes[60:].max())

# ---- threshold & climatology per cell ----
thr = np.full((366, C), np.nan)
clim = np.full((366, C), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', category=RuntimeWarning)
    for d in range(366):
        m = M[d]
        if m.any():
            V = Xw[m, :]
            clim[d] = np.nanmean(V, axis=0)
            thr[d] = np.nanquantile(V, 0.9, method='hazen', axis=0)
# day 60 <- mean of 59 and 61
thr[59] = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])
print("pre-smooth NaNs: thr", int(np.isnan(thr).sum()), "clim", int(np.isnan(clim).sum()))

# ---- 31-day centred circular moving mean over 366 ----
def smooth366(A):
    Af = np.where(np.isnan(A), 0.0, A)
    Cf = (~np.isnan(A)).astype(np.float64)
    S = np.zeros_like(A); N = np.zeros_like(A)
    for k in range(-15, 16):
        S += np.roll(Af, -k, axis=0)
        N += np.roll(Cf, -k, axis=0)
    out = np.full_like(A, np.nan)
    nz = N > 0
    out[nz] = S[nz] / N[nz]
    return out

thr_s = smooth366(thr)
clim_s = smooth366(clim)
print("post-smooth NaNs: thr", int(np.isnan(thr_s).sum()), "clim", int(np.isnan(clim_s).sum()))

# ---- target doys & hot days ----
tdays = times[t0t:t1t + 1]
tdoy = doy_of(tdays)
print("target doy range:", tdoy.min(), tdoy.max())
thrT = thr_s[tdoy, :]  # (92, C)
hot = Xt >= thrT       # NaN threshold -> False

# ---- per-cell MHWs (sea cells only) ----
mask = np.zeros((92, C), dtype=np.uint8)
ndays = 92
for c in range(C):
    if not sea[c]:
        continue
    h = hot[:, c]
    runs = []
    i = 0
    while i < ndays:
        if h[i]:
            j = i
            while j + 1 < ndays and h[j + 1]:
                j += 1
            if j - i + 1 >= 5:
                runs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    for s, e in merged:
        mask[s:e + 1, c] = 1

print("mask cells with any MHW:", int((mask.sum(axis=0) > 0).sum()),
      "total MHW cell-days:", int(mask.sum()))

# ---- regional events ----
active = mask.any(axis=1)
events = []
i = 0
while i < ndays:
    if active[i]:
        j = i
        while j + 1 < ndays and active[j + 1]:
            j += 1
        events.append((str(tdays[i]), str(tdays[j])))
        i = j + 1
    else:
        i += 1
print("active days:", int(active.sum()), "events:", events)

# ---- outputs ----
out = xr.Dataset(
    data_vars={'mhw': (('time', 'latitude', 'longitude'), mask, {})},
    coords={
        'time': ('time', times[t0t:t1t + 1]),
        'latitude': ('latitude', lat[latm]),
        'longitude': ('longitude', lon[lonm]),
    },
)
out.to_netcdf('/work/output/mhw_mask.nc')
print("wrote mhw_mask.nc", out.sizes, out['mhw'].dtype)

report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": s, "end": e} for s, e in events],
    "complete": True,
    "caveats": ("Sea cells = region grid cells with finite SST on all 92 target days. "
                "Baseline pools include the +-5 day windows around 1992-01-01..2002-12-31, i.e. "
                "dates 1991-12-27..2003-01-05. Threshold = 90th percentile via numpy method='hazen' "
                "(MATLAB default per task), climatology = mean, both NaN-ignoring; day 60 set to mean "
                "of days 59 and 61 before a 31-day centred circular moving mean over 366 days. "
                "Per-cell MHWs: >=5 consecutive days with SST >= threshold, runs separated by <=2 "
                "non-hot days joined; restricted to 2021-06-01..2021-08-31. Regional event = maximal "
                "run of days where at least one sea cell is in a per-cell MHW."),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("wrote report.json")
'''
with open('/work/pipeline.py', 'w') as f:
    f.write(script)
print("script written")
