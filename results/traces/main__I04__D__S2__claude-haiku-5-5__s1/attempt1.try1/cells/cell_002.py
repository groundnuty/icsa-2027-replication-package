
import shutil, numpy as np
print(shutil.disk_usage('/work'), os.path.getsize('/work/sst_s2.nc')/1e9)
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=54.39-1e-6)&(lat<=55.59+1e-6))[0]; lo=np.where((lon>=18.25-1e-6)&(lon<=19.45+1e-6))[0]
print(lat[la[0]],lat[la[-1]],len(la),lon[lo[0]],lon[lo[-1]],len(lo))
print(ds.time.values[[0,-1]])
