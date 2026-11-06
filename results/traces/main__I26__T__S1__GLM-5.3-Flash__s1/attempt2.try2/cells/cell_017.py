import fsspec, io, time, numpy as np, h5py
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
data = fs.cat([f'{base}/sst_19920601.nc', f'{base}/sst_19920602.nc', f'{base}/sst_19920603.nc'])
t1=time.time()
for p,b in data.items():
    f = h5py.File(io.BytesIO(b),'r')
    arr = f['analysed_sst'][0, 217:277, 421:481]
    f.close()
    break
t2=time.time()
print('cat3:', round(t1-t0,2), 'decode1:', round(t2-t1,2))
