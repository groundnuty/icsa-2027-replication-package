import h5py, numpy as np, time
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
n = v.shape[0]
ref = np.array(v[4018])  # 1992-01-01 is day index 4018 (10 years after 1982-01-01: 10*365+2=3652? check)
# Actually 1992-01-01 index: 1982..1991 = 10 years, 2 leap days (1984,1988) => 3652
print("check: 3652 should be 1992-01-01")
t = np.array(f['time'])
print("time units attr:", f['time'].attrs if f['time'].attrs else None)
# find index of 1992-01-01 via units
import datetime
units = f['time'].attrs.get('units')
print("units:", units)
f.close()
