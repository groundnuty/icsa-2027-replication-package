import numpy as np
z = np.load('/work/interim.npz')
for k in z.files:
    print(k, z[k].shape, z[k].dtype)
