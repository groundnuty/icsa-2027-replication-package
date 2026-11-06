import numpy as np
times = np.load('/work/times.npy').astype('datetime64[D]')
i0 = int(np.searchsorted(times, np.datetime64('2012-06-01')))
i1 = int(np.searchsorted(times, np.datetime64('2012-08-31')))
print("target idx:", i0, i1, "days:", i1-i0+1)
b_end = int(np.searchsorted(times, np.datetime64('2003-01-05')))
print("baseline idx: 0 ..", b_end-1, "=> count", b_end)
