import numpy as np, netCDF4
nc = netCDF4.Dataset('/work/data/sst_s2.nc', 'r')
t = nc['time']
print("units:", t.units, "calendar:", getattr(t, 'calendar', None))
raw = np.asarray(t[:], dtype=np.float64)
print("raw[:3]:", raw[:3], "raw[3647]:", raw[3647])
dec = np.asarray(t[:], dtype='datetime64[D]')
print("decoded[:3]:", dec[:3])
print("decoded around 1992-01-01:", dec[3650:3655])
print("searchsorted:", int(np.searchsorted(dec, np.datetime64('1992-01-01'))))
nc.close()