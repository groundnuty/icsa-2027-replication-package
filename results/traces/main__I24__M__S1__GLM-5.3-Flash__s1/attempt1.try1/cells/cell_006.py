import h5py, numpy as np, os
D='/data/icsa2027_data_20261101T090944Z/s1z'
with h5py.File(os.path.join(D,'sst_20040615.nc'),'r') as f:
    lat_ref=f['latitude'][:]; lon_ref=f['longitude'][:]
same=True
for name in ['sst_19920601.nc','sst_19960229.nc','sst_20021231.nc','sst_19911227.nc','sst_20030105.nc','sst_19820101.nc']:
    with h5py.File(os.path.join(D,name),'r') as f:
        same &= np.array_equal(f['latitude'][:],lat_ref) and np.array_equal(f['longitude'][:],lon_ref)
print('grid identical across sampled files:',same)
print('lat[203:207]',lat_ref[203:207],'lat[262:266]',lat_ref[262:266])
print('lon[61:65]',lon_ref[61:65],'lon[121:125]',lon_ref[121:125])
