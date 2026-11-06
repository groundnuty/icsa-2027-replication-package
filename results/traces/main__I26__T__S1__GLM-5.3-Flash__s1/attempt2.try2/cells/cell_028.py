import xarray as xr, numpy as np, json
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
m = ds['mhw'].values
t = ds['time'].values
active = m.reshape(m.shape[0], -1).any(axis=1)
idx = np.where(active)[0]
print('active days in file:', [(str(t[i])[:10]) for i in idx])
rep = json.load(open('output/report.json'))
print('report events:', rep['events'])
print('fields:', sorted(rep.keys()))
print('mask sum:', int(m.sum()), '| dtype:', m.dtype, '| shape:', m.shape)
ds.close()
print('files:', __import__('os').listdir('output'))
