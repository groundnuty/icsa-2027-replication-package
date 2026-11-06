import numpy as np, xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
raw = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf', mask_and_scale=False)
print('raw attrs:', {k: str(v) for k, v in raw['analysed_sst'].attrs.items()})
print('raw encoding:', {k: str(v) for k, v in raw['analysed_sst'].encoding.items() if k in ('dtype','scale_factor','add_offset','_FillValue')})

L0, L1, O0, O1 = 545, 604, 721, 780
# raw int16 for 2019-06-01, one cell (30,30); manual decode
r1 = raw['analysed_sst'].isel(time=13665, latitude=575, longitude=750).values
sf = raw['analysed_sst'].attrs.get('scale_factor'); ao = raw['analysed_sst'].attrs.get('add_offset')
print('raw int16 value 2019-06-01 cell(30,30):', r1, '-> manual decode:', r1*sf + ao)
d1 = ds['analysed_sst'].isel(time=13665, latitude=575, longitude=750).values
print('xarray decoded value:', d1)

sst_b = np.load('/work/sst_b.npy')
bd = np.arange('1991-12-27', '2003-01-06', dtype='datetime64[D]')
for lab, i in [('1992-01-15', 19), ('1992-04-15', 110), ('1992-06-27', 183), ('1992-08-01', 218),
               ('1997-07-15', 2012), ('2002-07-01', 3843), ('2003-01-01', 4021)]:
    a = sst_b[i]
    print('%s  min %.2f mean %.2f max %.2f  (degC: %.2f/%.2f/%.2f)' %
          (lab, np.nanmin(a), np.nanmean(a), np.nanmax(a), np.nanmin(a)-273.15, np.nanmean(a)-273.15, np.nanmax(a)-273.15))

sst_t = ds['analysed_sst'].isel(time=slice(13665, 13757), latitude=slice(L0, L1+1), longitude=slice(O0, O1+1)).values.astype(np.float64)
for lab, i in [('2019-06-01', 0), ('2019-07-16', 45), ('2019-08-31', 91)]:
    a = sst_t[i]
    print('%s  min %.2f mean %.2f max %.2f  (degC: %.2f/%.2f/%.2f)' %
          (lab, np.nanmin(a), np.nanmean(a), np.nanmax(a), np.nanmin(a)-273.15, np.nanmean(a)-273.15, np.nanmax(a)-273.15))
