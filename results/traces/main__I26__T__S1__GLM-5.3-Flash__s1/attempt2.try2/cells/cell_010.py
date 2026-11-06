import numpy as np
# check coordinate arithmetic against actual coords
lat_vals = 53.5 + 0.02*np.arange(626)
lon_vals = 9.0 + 0.02*np.arange(1051)
# emulate float32 storage
lat32 = lat_vals.astype('float32').astype('float64')
lon32 = lon_vals.astype('float32').astype('float64')
latm = (lat32>=57.83)&(lat32<=59.03); lonm=(lon32>=17.41)&(lon32<=18.61)
print('nlat',latm.sum(),'nlon',lonm.sum())
print(lat32[latm][:3], lat32[latm][-3:])
print(lon32[lonm][:3], lon32[lonm][-3:])
idx_lat = np.where(latm)[0]; idx_lon=np.where(lonm)[0]
print(idx_lat[0], idx_lat[-1], idx_lon[0], idx_lon[-1])
