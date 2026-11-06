import numpy as np, h5netcdf, fsspec, time as timemod
print("numpy", np.__version__)
import scipy
print("scipy", scipy.__version__)

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
nc = h5netcdf.File(f, 'r')
v = nc['analysed_sst']
# filters / compression info
try:
    print("filters:", v.filters if hasattr(v, 'filters') else "n/a")
except Exception as e:
    print("filters err", e)
try:
    h5ds = v.get_h5py_dataset()
    print("h5py ds:", h5ds.shape, h5ds.chunks, "compression:", h5ds.compression, "shuffle:", h5ds.shuffle)
except Exception as e:
    print("get_h5py_dataset err:", e)
    print([a for a in dir(v) if 'h5' in a.lower() or 'filter' in a.lower() or 'chunk' in a.lower()])
