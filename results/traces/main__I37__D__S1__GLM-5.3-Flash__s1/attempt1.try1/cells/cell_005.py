import fsspec, os, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)

# test speed on 10 files
names = ['sst_19920601.nc','sst_19920602.nc','sst_19920603.nc','sst_19920604.nc','sst_19920605.nc',
         'sst_20120601.nc','sst_20120831.nc','sst_19911227.nc','sst_19920101.nc','sst_20021231.nc']
t0 = time.time()
for n in names:
    fs.get(f'{base}/{n}', f'/work/data/{n}')
dt = time.time() - t0
print(f"10 files in {dt:.2f}s -> {dt/10*1000:.0f} ms/file; est for 4100 files: {dt/10*4100/60:.1f} min")
