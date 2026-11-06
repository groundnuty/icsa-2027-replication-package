import numpy as np
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=56.09)&(lat<=57.29))[0]; lo=np.where((lon>=10.55)&(lon<=11.75))[0]
print(len(la),len(lo), lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
a=ds.analysed_sst.values[0][np.ix_(la,lo)]
print(np.isnan(a).sum(), a.size, np.nanmin(a), np.nanmax(a), a.dtype)
print(ds.analysed_sst.encoding)