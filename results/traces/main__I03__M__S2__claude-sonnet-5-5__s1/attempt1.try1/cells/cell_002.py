
import numpy as np, pandas as pd
la=d.latitude.values;lo=d.longitude.values
iy=np.where((la>=54.17-1e-4)&(la<=55.37+1e-4))[0];ix=np.where((lo>=13.25-1e-4)&(lo<=14.45+1e-4))[0]
print(la[iy][[0,-1]],lo[ix][[0,-1]],len(iy),len(ix))
s=d.analysed_sst.isel(latitude=slice(iy[0],iy[-1]+1),longitude=slice(ix[0],ix[-1]+1)).load()
print(s.dtype,float(s.max()), len(pd.date_range("1991-12-27","1991-12-31")), s.time.values[:1])
# check missing days in time
print(len(pd.date_range("1982-01-01","2023-12-31")))
