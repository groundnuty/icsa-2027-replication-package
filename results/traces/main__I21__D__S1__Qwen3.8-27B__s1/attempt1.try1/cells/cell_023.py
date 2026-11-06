import numpy as np
z = np.load('/work/doy_stats.npz')
for k in z.files:
    print(k, z[k].shape, z[k].dtype)
