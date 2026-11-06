
import xarray as xr, json, os
os.makedirs('output',exist_ok=True)
da=xr.DataArray(mhw.astype(np.uint8), dims=('time','lat','lon'),
    coords={'time':tdates_.astype('datetime64[ns]'),'lat':lat,'lon':lon}, name='mhw')
ds_out=xr.Dataset({'mhw':da})
try:
    ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
except Exception as e:
    print('h5netcdf failed',e); ds_out.to_netcdf('output/mhw_mask.nc')
rep={
 'region':{'lat_min':54.17,'lat_max':55.37,'lon_min':13.25,'lon_max':14.45},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2014-06-01','end':'2014-08-31'},
 'events':[{'onset':s,'end':e} for s,e in events],
 'complete':True,
 'caveats':'Grid cells in region: 60x60 (lat 54.18-55.36, lon 13.26-14.44). 3303 of 3600 cells are sea cells (finite on all target days); other cells are 0 in mask. Threshold/climatology pools built from dates within +/-5 days of 1992-2002 baseline dates, using the extended 1991-12-27 to 2003-01-05 window. Day 60 set to mean of days 59 and 61 before smoothing. Hot-run and gap-joining computed within the target period only.'
}
json.dump(rep,open('output/report.json','w'),indent=2)
print(xr.open_dataset('output/mhw_mask.nc').mhw.shape, open('output/report.json').read()[:600])
