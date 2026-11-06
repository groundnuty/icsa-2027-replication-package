import h5py, time, numpy as np
base = "/data/icsa2027_data_20261101T090944Z/s1z"
f = h5py.File(f"{base}/sst_20120701.nc", "r")
v = f['analysed_sst']
print("chunks", v.chunks, "compression", v.compression)
li = np.arange(330, 390); lo = np.arange(551, 611)
t0 = time.time(); a = v[:, 330:390, 551:611][0]; t1 = time.time()
print("hyperslab ms:", (t1-t0)*1000)
t0 = time.time(); a2 = v[0][:]; t1 = time.time()
print("full row ms:", (t1-t0)*1000)
print("equal:", np.array_equal(a, a2[330:390, 551:611]))
f.close()
import os
print("cpus:", os.cpu_count())
import multiprocessing as mp
print("mp start methods:", mp.get_all_start_methods() if hasattr(mp,'get_all_start_methods') else 'n/a')
