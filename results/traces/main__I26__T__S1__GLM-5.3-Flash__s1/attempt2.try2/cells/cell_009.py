import fsspec, io, time, numpy as np, h5py
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
dates = ['1992%02d%02d'%(6,d) for d in range(1,11)]
t0=time.time()
data = fs.cat([f'{base}/sst_{d}.nc' for d in dates])
t1=time.time()
t2=t1
outs=[]
for d in dates:
    f = h5py.File(io.BytesIO(data[f'{base}/sst_{d}.nc']),'r')
    arr = f['analysed_sst'][0]
    outs.append(arr)
    f.close()
t3=time.time()
print('cat:', t1-t0, 'read:', t3-t2)
# slice region from float32 before converting
lat = np.arange(53.5, 66.0001, 0.02)
lon = np.arange(9.0, 30.0001, 0.02)
i0 = int(round((57.83-53.5)/0.02)); i1 = int(round((59.03-53.5)/0.02))
j0 = int(round((17.41-9.0)/0.02)); j1 = int(round((18.61-9.0)/0.02))
print('slice idx', i0,i1,j0,j1, 'shape', (i1-i0+1, j1-j0+1))
arr = outs[0][0, i0:i1+1, j0:j1+1].astype('float64')
print(arr.shape, np.nanmean(arr), np.isfinite(arr).mean())
