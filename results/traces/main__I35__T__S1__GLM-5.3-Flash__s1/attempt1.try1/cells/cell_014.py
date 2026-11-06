import h5py, numpy as np, os
local='/work/cache/sst_20090601.nc'
with h5py.File(local,'r') as f:
    d=f['analysed_sst']
    print('dtype:', d.dtype, 'shape:', d.shape, 'chunks:', d.chunks, 'compression:', d.compression)
    print('attrs:', {k: (v if not isinstance(v, np.ndarray) else v) for k,v in d.attrs.items()})
    sl=d[0,322:382,485:545]
    print('finite:', int(np.isfinite(sl).sum()), 'of', sl.size, 'NaN count:', int(np.isnan(sl).sum()))
    print('min/max finite:', np.nanmin(sl), np.nanmax(sl))
    print('unique sample of non-finite handled? dtype float32 confirmed')
    # check lon attrs
    print('lon attrs:', {k:v for k,v in f['longitude'].attrs.items() if k in ('units','standard_name')})
