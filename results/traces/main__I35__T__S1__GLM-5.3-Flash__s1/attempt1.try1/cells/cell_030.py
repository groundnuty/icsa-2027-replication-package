import numpy as np, datetime as dt, json, os
import xarray as xr

r=np.load('/work/results.npz')
z=np.load('/work/extracted.npz', allow_pickle=False)
TGT=[dt.date.fromisoformat(s) for s in z['tgt_dates']]
mhw=r['mhw']; sea=r['sea']   # mhw (92, nsea), sea (60,60)

# rebuild full 60x60 mask (land = 0)
mask=np.zeros((len(TGT),60,60), dtype=np.uint8)
flat=mask.reshape(len(TGT), -1)
flat[:, r['sea_idx']] = mhw.astype(np.uint8)
mask=flat.reshape(len(TGT),60,60)
print('mask shape', mask.shape, 'dtype', mask.dtype, 'ones:', int(mask.sum()))

lat=np.arange(322,382)*0.02+53.5   # recover float32 grid values exactly
lon=np.arange(485,545)*0.02+9.0
# use exact dataset float32 values from the saved reference file
import h5py
with h5py.File('/work/cache/sst_20090601.nc','r') as f:
    lat=f['latitude'][322:382].astype(np.float32)
    lon=f['longitude'][485:545].astype(np.float32)
print('lat[0],lat[-1],lon[0],lon[-1]:', lat[0], lat[-1], lon[0], lon[-1])

time_vals=np.array([np.datetime64(d.isoformat()) for d in TGT])
ds=xr.Dataset(
    {'mhw': (('time','latitude','longitude'), mask)},
    coords={'time': time_vals, 'latitude': lat, 'longitude': lon},
    attrs={
        'title': 'Per-cell marine heatwave mask, Baltic Sea region, 2009-06-01 to 2009-08-31',
        'dataset_id': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m',
        'method': 'Baseline 1992-2002; per day-of-year 11x11-day +-5 calendar-day pools; 90th percentile (Hazen/MATLAB quantile); day 60 = mean of days 59,61; circular 31-day moving mean; hot if SST >= threshold; runs >=5 days joined across gaps <=2 days; land cells 0',
    })
ds['mhw'].attrs={'long_name':'marine heatwave mask (1 = cell inside per-cell MHW, 0 otherwise)', 'units':'1', 'flag_values':np.array([0,1],dtype=np.uint8), 'flag_meanings':'not_in_mhw in_mhw'}
ds['time'].attrs={'standard_name':'time', 'long_name':'Time', 'axis':'T'}
ds['latitude'].attrs={'standard_name':'latitude','long_name':'latitude','units':'degrees_north','axis':'Y'}
ds['longitude'].attrs={'standard_name':'longitude','long_name':'longitude','units':'degrees_east','axis':'X'}
os.makedirs('/work/output', exist_ok=True)
path='/work/output/mhw_mask.nc'
ds.to_netcdf(path, engine='h5netcdf', encoding={'mhw': {'dtype':'uint8','zlib':True},
                                                'time': {'units':'seconds since 1981-01-01','calendar':'proleptic_gregorian','dtype':'int64'}})
print('wrote', path, os.path.getsize(path), 'bytes')

report={
 "region": {"lat_min": 59.93, "lat_max": 61.13, "lon_min": 18.69, "lon_max": 19.89},
 "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
 "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
 "events": [{"onset": "2009-06-26", "end": "2009-07-07"},
            {"onset": "2009-08-06", "end": "2009-08-10"}],
 "complete": True,
 "caveats": "Region interpreted as the dataset's grid cells with latitude in [59.93, 61.13] N and longitude in [18.69, 19.89] E inclusive (60 x 60 cells at 0.02 deg). Sea cells = 3302 cells with finite SST on all 92 target days; remaining 298 coastal/land cells are 0 in the mask. Thresholds/climatology use the extended day-of-year pools (1991-12-27 to 2003-01-05 edges included); no SST gaps occurred on sea cells. Per-cell MHW detection restricted to the target window as specified, so runs touching window edges are truncated."
}
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print('wrote /work/output/report.json')
print(json.dumps(report, indent=2))
