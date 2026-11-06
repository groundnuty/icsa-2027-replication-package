import h5py, numpy as np, os, time, multiprocessing
print('cpus:', multiprocessing.cpu_count())
DIR = '/data/icsa2027_data_20261101T090944Z/s1z'
files = sorted(os.listdir(DIR))
t0 = time.time()
n = 0
for name in files[:40]:
    with h5py.File(os.path.join(DIR, name), 'r') as f:
        sub = f['analysed_sst'][0, 130:190, 78:138]
        n += 1
dt = time.time() - t0
print(f'{n} files in {dt:.2f}s -> {dt/n*1000:.1f} ms/file; est 4200 files: {dt/n*4200/60:.1f} min single-proc')
