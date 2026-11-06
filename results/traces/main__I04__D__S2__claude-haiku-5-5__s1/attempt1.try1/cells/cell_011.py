
import xarray as xr
os.makedirs('/work/../output',exist_ok=True)
os.makedirs('output',exist_ok=True)
src=xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
latc=src.latitude.values[np.where((src.latitude.values>=54.39-1e-6)&(src.latitude.values<=55.59+1e-6))[0]]
lonc=src.longitude.values[np.where((src.longitude.values>=18.25-1e-6)&(src.longitude.values<=19.45+1e-6))[0]]
assert np.allclose(latc,lat) and np.allclose(lonc,lon)
da=xr.DataArray(mhw, dims=('time','lat','lon'), coords={'time':td.values,'lat':latc,'lon':lonc}, name='mhw')
da.to_netcdf('output/mhw_mask.nc', engine='h5netcdf', encoding={'mhw':{'dtype':'uint8'}})
rep={"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2020-06-01","end":"2020-08-31"},
     "events":events,"complete":True,
     "caveats":"Sea cells = 3309 of 3600 grid cells (finite on all target days); other cells are land/NaN and are 0 in the mask. Smoothed 366-day climatology/threshold computed via month-day DOY mapping (leap reference). Analysis subset extracted from the 40 GB source file; the 1982-2023 full record was not otherwise used."}
json.dump(rep,open('output/report.json','w'),indent=2)
chk=xr.open_dataset('output/mhw_mask.nc',engine='h5netcdf'); print(chk.mhw.dtype, chk.mhw.shape, int(chk.mhw.sum())); print(open('output/report.json').read()[:400])
