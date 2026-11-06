
print(ds.attrs['comment'])
import numpy as np
la=ds.latitude.values; lo=ds.longitude.values
ri=np.where((la>=57.13-1e-6)&(la<=58.33+1e-6))[0]; ci=np.where((lo>=22.79-1e-6)&(lo<=23.99+1e-6))[0]
print(len(ri),len(ci), la[ri[0]],la[ri[-1]],lo[ci[0]],lo[ci[-1]])
print(os.path.getsize('/work/sst_s2.nc')/1e9)
