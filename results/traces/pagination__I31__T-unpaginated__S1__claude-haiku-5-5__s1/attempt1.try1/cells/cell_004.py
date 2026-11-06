
v=ds['analysed_sst']; print(v.attrs); print(v.encoding); print(ds.attrs['comment'])
import numpy as np
a=v.values; print(np.nanmin(a),np.nanmax(a), np.isnan(a).sum(), a.size)
print(ds.latitude.values[[0,-1]], ds.longitude.values[[0,-1]])
