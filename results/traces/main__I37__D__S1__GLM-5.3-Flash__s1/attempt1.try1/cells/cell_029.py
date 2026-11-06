import numpy as np
sst = np.load('/work/sst_cube.npy')
times = np.load('/work/times.npy').astype('datetime64[D]')
print("times[4009] =", times[4009], " times[4010] =", times[4010], " times[4101] =", times[4101], " times[4119] =", times[4119])
