
import numpy as np

lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

print("lat_vals:", lat_vals)
print("lon_vals:", lon_vals)
print("lat_vals dtype:", lat_vals.dtype)
print("lon_vals dtype:", lon_vals.dtype)
print("n_lat:", len(lat_vals), "n_lon:", len(lon_vals))
