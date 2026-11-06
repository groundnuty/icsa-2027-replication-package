
import numpy as np
lat_vals = 53.5 + 0.02*np.arange(626)
lon_vals = 9.0 + 0.02*np.arange(1051)

# Check which lat values fall in [60.09, 61.29]
lat_in = np.where((lat_vals >= 60.09) & (lat_vals <= 61.29))[0]
print("Lat in region:", lat_vals[lat_in[0]], "to", lat_vals[lat_in[-1]], "count:", len(lat_in))

lon_in = np.where((lon_vals >= 20.01) & (lon_vals <= 21.21))[0]
print("Lon in region:", lon_vals[lon_in[0]], "to", lon_vals[lon_in[-1]], "count:", len(lon_in))
