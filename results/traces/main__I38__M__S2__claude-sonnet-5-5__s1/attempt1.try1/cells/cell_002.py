import numpy as np,pandas as pd
la=ds.latitude.values;lo=ds.longitude.values
yi=np.where((la>=60.49-1e-4)&(la<=61.69+1e-4))[0];xi=np.where((lo>=17.25-1e-4)&(lo<=18.45+1e-4))[0]
print(la[yi][[0,-1]],lo[xi][[0,-1]])
sub=ds.analysed_sst.isel(latitude=slice(yi[0],yi[-1]+1),longitude=slice(xi[0],xi[-1]+1)).sel(time=slice("1991-12-27","2003-08-31")).load()
print(sub.shape, sub.time.size, pd.Series(sub.time.values).diff().value_counts())