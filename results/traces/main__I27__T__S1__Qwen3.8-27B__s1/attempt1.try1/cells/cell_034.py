
import numpy as np, datetime as dt, json, os
import xarray as xr

print("cwd:", os.getcwd())
os.makedirs('output', exist_ok=True)

maskA = np.load('/tmp/mhw/maskA.npy')          # (92, 3600)
lat = np.load('/tmp/mhw/lat.npy'); lon = np.load('/tmp/mhw/lon.npy')
tdates = [dt.datetime(2008,6,1) + dt.timedelta(days=i) for i in range(92)]

m = maskA.reshape(92, 60, 60).astype(np.uint8)
print("m:", m.dtype, m.shape, "sum:", int(m.sum()))

ds = xr.Dataset(
    data_vars=dict(mhw=(('time','lat','lon'), m)),
    coords=dict(
        time=("time", np.array([t for t in tdates], dtype='datetime64[ns]')),
        lat=("lat", lat.astype(np.float32)),
        lon=("lon", lon.astype(np.float32)),
    ),
)
ds['mhw'].attrs = dict(
    long_name="Marine heatwave mask (1 = cell inside a per-cell MHW, 0 = otherwise; land cells 0)",
    units="1",
)
ds.attrs = dict(
    title="Baltic Sea regional MHW detection, 2008-06-01 to 2008-08-31",
    source_dataset="cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (reprocessed L4 daily SST)",
    region="lat 57.83-59.03 N, lon 17.41-18.61 E (inclusive)",
    baseline="1992-01-01 to 2002-12-31 (90th percentile threshold, hazen quantile, +-5 day windows, 31-day circular smoothing)",
    method="hot: SST >= threshold(doy); per-cell MHW: >=5 consecutive hot days, joined over 1-2 day gaps; regional event: >=1 cell in MHW",
)
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("wrote output/mhw_mask.nc")

# verify round-trip
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "dims:", chk['mhw'].dims)
print("time range:", chk['time'].values[0], chk['time'].values[-1])
print("lat range:", float(chk['lat'].values[0]), float(chk['lat'].values[-1]))
print("lon range:", float(chk['lon'].values[0]), float(chk['lon'].values[-1]))
print("mhw sum:", int(chk['mhw'].values.sum()))
