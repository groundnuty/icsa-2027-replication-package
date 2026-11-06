import numpy as np, xarray as xr, datetime as dt, json
import warnings; warnings.filterwarnings('ignore')

mhw = np.load('/work/mhw_bool.npy')                    # (92, 3600)
cr = np.load('/work/coords.npz')
lat = cr['lat']; lon = cr['lon']
tgt_dates = [dt.date.fromisoformat(str(d)) for d in cr['target_dates'].astype('datetime64[D]').astype(object)]
epoch = dt.date(1981,1,1)
time_int = np.array([(d - epoch).days * 86400 for d in tgt_dates], dtype=np.int32)

mhw3 = mhw.reshape(92, 60, 60).astype(np.uint8)
ds_out = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw3, {'long_name':'marine heatwave mask (1 = inside per-cell MHW, 0 = not; land = 0)'})),
    coords={
        'time': ('time', time_int, {'long_name':'Time','standard_name':'time','axis':'T',
                                     'units':'seconds since 1981-01-01','calendar':'proleptic_gregorian'}),
        'lat': ('lat', lat.astype(np.float32), {'long_name':'latitude','units':'degrees_north','standard_name':'latitude','axis':'Y'}),
        'lon': ('lon', lon.astype(np.float32), {'long_name':'longitude','units':'degrees_east','standard_name':'longitude','axis':'X'}),
    },
)
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print("wrote mhw_mask.nc")

report = {
    "region": {"lat_min": 54.17, "lat_max": 55.37, "lon_min": 13.25, "lon_max": 14.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2004-06-01", "end": "2004-08-31"},
    "events": [],
    "complete": True,
    "caveats": ("All 92 target days and all 4028 baseline-window days (1991-12-27 to 2003-01-05) were available and analysed. "
                "No per-cell MHW was found in any sea cell (longest run of hot days was 2, below the 5-day minimum), "
                "hence no regional MHW events; 297 of the 3600 region cells are non-sea (no SST on some target days) and are 0 in the mask."),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("wrote report.json")

# ---------- verification ----------
chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "values:", set(np.unique(chk['mhw'].values).tolist()))
print("time decoded:", chk['time'].values[0], "->", chk['time'].values[-1], "n=", len(chk['time']))
expected = np.array([np.datetime64(d.isoformat()) for d in tgt_dates])
print("time matches target dates:", bool((chk['time'].values == expected).all()))
print("lat/lon match dataset region:", bool((chk['lat'].values == lat.astype(np.float32)).all() and (chk['lon'].values == lon.astype(np.float32)).all()))
# compare against the source dataset file for one day's coordinates
src = xr.open_dataset('/work/data/sst_20040715.nc', engine='h5netcdf')
print("src lat[34:94] equal:", bool((src['latitude'].values[34:94].astype(np.float64) == lat).all()))
print("src lon[213:273] equal:", bool((src['longitude'].values[213:273].astype(np.float64) == lon).all()))
src.close()
