v=d.analysed_sst
print(v.attrs); print(v.encoding)
import numpy as np
a=v.values[0]; print(np.nanmin(a),np.nanmax(a),np.isnan(a).sum(), a.shape)
lat=d.latitude.values; lon=d.longitude.values
print(np.diff(lat)[:3], np.unique(np.round(np.diff(lat),6)), np.unique(np.round(np.diff(lon),6)))