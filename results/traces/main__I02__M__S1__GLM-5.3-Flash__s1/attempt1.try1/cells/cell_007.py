import time, numpy as np, h5py
D='/data/icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
for d in ['19920101','19960229','20000301','20020704','19911227','20030105','19820615','20231231']:
    p=f'{D}/sst_{d}.nc'
    with h5py.File(p,'r') as f:
        a=f['analysed_sst'][0,34:94,213:273]
        la=f['latitude'][34:94]; lo=f['longitude'][213:273]
    print(d, a.shape, np.isfinite(a).mean(), la[0], la[-1], lo[0], lo[-1])
t1=time.time()
print("elapsed for 8 files:", t1-t0)
