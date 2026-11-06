
import numpy as np, json, os, datetime as dt
import xarray as xr

mhwA = np.load('/tmp/mhwA.npy')   # (92, 3600) bool
sea  = np.load('/tmp/sea.npy')
tor  = np.load('/tmp/tdates.npy')

# coordinates from the dataset (region slice)
ILAT = (204, 263); ILON = (63, 122)
lat_vals = np.array([53.5 + 0.02*k for k in range(626)], dtype=np.float32)
lon_vals = np.array([9.0 + 0.02*k for k in range(1051)], dtype=np.float32)
lat = lat_vals[ILAT[0]:ILAT[1]+1]
lon = lon_vals[ILON[0]:ILON[1]+1]
print("lat:", lat[0], lat[-1], "n:", len(lat))
print("lon:", lon[0], lon[-1], "n:", len(lon))
# verify these exactly match the dataset's coordinate values (float32)
import fsspec, io
fs = fsspec.filesystem('onedata')
raw = fs.cat_file('/icsa2027_data_20261101T090944Z/s1z/sst_20160601.nc')
ds = xr.open_dataset(io.BytesIO(raw), engine='h5netcdf')
assert bool((ds.latitude.values[ILAT[0]:ILAT[1]+1] == lat).all())
assert bool((ds.longitude.values[ILON[0]:ILON[1]+1] == lon).all())
time_vals = ds.time.values
ds.close()
print("coords match dataset exactly")

# reshape mask (92, 60, 60) -> cells were stored row-major over lat,lon slice
mask2d = mhwA.reshape(92, 60, 60)
# sanity: land cells (NaN sst) must be 0 everywhere
sst_tgt = np.load('/tmp/sst_tgt.npy').reshape(92, 60, 60)
land = ~np.isfinite(sst_tgt).all(axis=0)
print("land cells in slice:", int(land.sum()), "mask zeros on land:", bool((mask2d[:, land].sum()==0)))
print("mask uint8 values:", np.unique(mask2d))

os.makedirs('output', exist_ok=True)
out = xr.Dataset(
    {'mhw': ('time', 'latitude', 'longitude'), mask2d.astype(np.uint8)},
    coords={
        'time': ('time', time_vals),
        'latitude': ('latitude', lat),
        'longitude': ('longitude', lon),
    }
)
out['mhw'].attrs['long_name'] = '1 if grid cell is inside a per-cell marine heatwave on that day, else 0 (land = 0)'
out.attrs['title'] = 'Per-cell MHW mask, Baltic Sea region 57.57-58.77N x 10.25-11.45E, 2016-06-01..2016-08-31'
out.attrs['source'] = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (version 202506); method: 1992-2002 baseline, 90th pct (hazen) +/-5d doy windows, 31d circular smoothing, 5-day runs, gap<=2 merging'
out.to_netcdf('output/mhw_mask.nc')

active = mhwA.any(axis=1)
events=[]
i=0
while i < 92:
    if active[i]:
        j=i
        while j+1<92 and active[j+1]: j+=1
        events.append({"onset": dt.date.fromordinal(int(tor[i])).isoformat(),
                       "end":   dt.date.fromordinal(int(tor[j])).isoformat()})
        i=j+1
    else: i+=1

report = {
    "region": {"lat_min": 57.57, "lat_max": 58.77, "lon_min": 10.25, "lon_max": 11.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2016-06-01", "end": "2016-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("Region contains 3600 grid cells (60x60), of which 3304 are sea cells (finite SST on all 92 target days) "
                "and 296 are land cells, set to 0 in the mask. SST analysed in kelvin as stored; thresholds are the "
                "90th percentile (hazen quantile) of the day-of-year pool (121 baseline values from 1992-2002 with +/-5-day "
                "calendar windows incl. 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05), day-60 values set to the mean "
                "of days 59 and 61, then a 31-day circular moving mean. Per-cell MHWs are runs of >=5 consecutive hot days "
                "merged across gaps of <=2 non-hot days. One regional event was found: 2016-06-01 to 2016-06-18; no other "
                "active days in the target period.")
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
print("written")
