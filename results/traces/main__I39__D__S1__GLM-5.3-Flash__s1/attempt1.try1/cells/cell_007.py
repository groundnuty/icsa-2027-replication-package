import fsspec, time
fs = fsspec.filesystem('onedata')
t0 = time.time()
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print('downloaded in %.1f s' % (time.time()-t0))

import os
print('size on disk:', os.path.getsize('/work/sst_s2.nc'))
