import numpy as np, xarray as xr, json, os

me = '/work/me/'
target = np.load(me+'target.npy')
mhw = np.load(me+'mhw.npy')
tt = np.load(me+'times_target.npy')
lat_sub = np.load(me+'lat_sub.npy'); lon_sub = np.load(me+'lon_sub.npy')

fin_per_cell = np.isfinite(target).sum(axis=0)
print("cells all-finite:", int((fin_per_cell==92).sum()),
      "| all-NaN:", int((fin_per_cell==0).sum()),
      "| partially finite:", int(((fin_per_cell>0)&(fin_per_cell<92)).sum()))

os.makedirs('/work/output', exist_ok=True)
ds_out = xr.Dataset(
    {"mhw": (("time","lat","lon"), mhw.astype(np.uint8))},
    coords={"time": ("time", tt.astype('datetime64[s]')),
            "lat": ("lat", lat_sub.astype(np.float32)),
            "lon": ("lon", lon_sub.astype(np.float32))},
)
ds_out['lat'].attrs.update({'standard_name':'latitude','units':'degrees_north','long_name':'latitude'})
ds_out['lon'].attrs.update({'standard_name':'longitude','units':'degrees_east','long_name':'longitude'})
ds_out['mhw'].attrs.update({'long_name':'marine heatwave per-cell mask (1 = inside per-cell MHW)',
                            'units':'1','flag_values':np.array([0,1],dtype=np.uint8),
                            'flag_meanings':'not_in_mhw in_mhw'})
enc = {'mhw': {'dtype':'uint8','_FillValue':None,'zlib':True},
       'time': {'dtype':'int64','units':'seconds since 1981-01-01','calendar':'proleptic_gregorian'},
       'lat': {'dtype':'float32'}, 'lon': {'dtype':'float32'}}
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print("wrote mhw_mask.nc")

# verify by re-reading
chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(chk)
m2 = chk['mhw'].values
print("dtype:", m2.dtype, "| equal to computed mask:", np.array_equal(m2, mhw))
print("sum:", int(m2.sum()))
latc = chk['lat'].values; lonc = chk['lon'].values; tc = chk['time'].values
print("lat match:", np.array_equal(latc, lat_sub), "lon match:", np.array_equal(lonc, lon_sub),
      "time match:", np.array_equal(tc, tt.astype('datetime64[s]')))
chk.close()
