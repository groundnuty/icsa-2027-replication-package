import numpy as np, json, os, datetime as dt
import fsspec, h5py
import netCDF4 as nc

out_dir = os.path.join(os.getcwd(), 'output')
os.makedirs(out_dir, exist_ok=True)
print("writing to:", out_dir)

mhw = np.load('/tmp/mhw_final.npy')                      # (92, 60, 60) uint8
idx = np.load('/tmp/idxmeta.npy') if os.path.exists('/tmp/idxmeta.npy') else None

PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
fs = fsspec.filesystem('onedata')
def read_with_retry(fn, tries=4, tag=""):
    last = None
    for k in range(tries):
        hf = None
        try:
            hf = h5py.File(fs.open(PATH, 'rb'), 'r')
            out = fn(hf)
            try: hf.close()
            except Exception: pass
            return out
        except Exception as e:
            last = e; time.sleep(2 + 2*k)
    raise last
import time as _t
lat, lon, tvals = read_with_retry(lambda hf: (hf['latitude'][545:605], hf['longitude'][721:781],
                                              hf['time'][13665:13757]), tag="coords")
assert mhw.shape == (len(tvals), len(lat), len(lon)), (mhw.shape, len(tvals), len(lat), len(lon))
print("coords:", lat[0], lat[-1], lon[0], lon[-1], "time n:", len(tvals), "first/last tvals:", tvals[0], tvals[-1])

ncp = os.path.join(out_dir, 'mhw_mask.nc')
with nc.Dataset(ncp, 'w', format='NETCDF4') as ds:
    ds.createDimension('time', len(tvals))
    ds.createDimension('lat', len(lat))
    ds.createDimension('lon', len(lon))
    v = ds.createVariable('time', 'i4', ('time',))
    v.units = 'seconds since 1981-01-01'
    v.calendar = 'proleptic_gregorian'
    v.standard_name = 'time'; v.long_name = 'Time'; v.axis = 'T'
    v[:] = tvals.astype(np.int32)
    v = ds.createVariable('lat', 'f4', ('lat',))
    v.standard_name = 'latitude'; v.long_name = 'Latitude'; v.units = 'degrees_north'; v.axis = 'Y'
    v[:] = lat.astype(np.float32)
    v = ds.createVariable('lon', 'f4', ('lon',))
    v.standard_name = 'longitude'; v.long_name = 'Longitude'; v.units = 'degrees_east'; v.axis = 'X'
    v[:] = lon.astype(np.float32)
    v = ds.createVariable('mhw', 'u1', ('time', 'lat', 'lon'), zlib=True, complevel=4)
    v.long_name = 'marine heatwave flag (per-cell MHW membership)'
    v.units = '1'
    v.flag_values = np.array([0, 1], np.uint8)
    v.flag_meanings = 'not_in_mhw in_mhw'
    v.comment = ('1 where the sea cell is inside a per-cell marine heatwave on that day '
                 '(hot = SST >= smoothed 90th-percentile day-of-year threshold, runs >= 5 days, '
                 'gaps <= 2 days joined); land cells are 0.')
    v[:] = mhw
    ds.Conventions = 'CF-1.8'
    ds.title = 'Per-cell marine heatwave mask, Baltic Sea region (64.39-65.59N, 23.41-24.61E), 2019-06-01 to 2019-08-31'
    ds.source = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016), analysed_sst'
    ds.region = 'lat 64.39-65.59, lon 23.41-24.61 (inclusive bounds)'
    ds.baseline = '1992-01-01 to 2002-12-31 (+/-5 calendar-day windows; edge days 1991-12-27..31, 2003-01-01..05 included)'
    ds.threshold_definition = ('90th percentile (Hazen / MATLAB quantile default) of baseline pool per cell and '
                               'leap-aligned day of year, day 60 = mean(day59, day61), then unweighted centred '
                               '31-day circular moving mean')
print("wrote", ncp, os.path.getsize(ncp), "bytes")

report = {
    "region": {"lat_min": 64.39, "lat_max": 65.59, "lon_min": 23.41, "lon_max": 24.61},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2019-06-01", "end": "2019-08-31"},
    "events": [
        {"onset": "2019-06-06", "end": "2019-06-22"},
        {"onset": "2019-07-20", "end": "2019-07-29"}
    ],
    "complete": True,
    "caveats": ("Sea cells (3311 of 3600 grid cells) are those with finite SST on every target day; "
                "land/ice-masked cells carry mhw=0. Baseline pools additionally use the 5 days beyond the "
                "baseline period on each side (1991-12-27..31 and 2003-01-01..05) exactly as the prescribed "
                "+/-5-day windows require. Thresholds and climatology were derived from the same reprocessed "
                "L4 product as the target period.")
}
jpath = os.path.join(out_dir, 'report.json')
with open(jpath, 'w') as fh:
    json.dump(report, fh, indent=2)
print("wrote", jpath, os.path.getsize(jpath), "bytes")

# ---------------- read back & validate ----------------
with nc.Dataset(ncp, 'r') as ds:
    assert set(ds.variables) >= {'mhw', 'time', 'lat', 'lon'}
    assert ds['mhw'].dtype == np.uint8, ds['mhw'].dtype
    assert ds['mhw'].dimensions == ('time', 'lat', 'lon')
    m2 = ds['mhw'][:]
    lat2, lon2, tv2 = ds['lat'][:], ds['lon'][:], ds['time'][:]
print("readback: shape", m2.shape, "dtype", m2.dtype, "| equals computed mask:", np.array_equal(np.asarray(m2), mhw))
print("coords match dataset:", np.array_equal(lat2, lat), np.array_equal(lon2, lon), np.array_equal(tv2, tvals))
dates_rb = np.datetime64('1981-01-01') + np.asarray(tv2).astype('timedelta64[s]')
print("time decode:", str(dates_rb[0]), "..", str(dates_rb[-1]), f"({len(dates_rb)} days)")
print("mhw values:", np.unique(m2), "| ones:", int(m2.sum()))
rep = json.load(open(jpath))
print("report keys:", sorted(rep.keys()))
print(json.dumps(rep, indent=1)[:1200])
