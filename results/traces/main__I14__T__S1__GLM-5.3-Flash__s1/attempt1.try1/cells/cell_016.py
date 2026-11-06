import numpy as np, pickle

with open('/tmp/stepB.pkl','rb') as fh:
    B = pickle.load(fh)
with open('/tmp/stepA.pkl','rb') as fh:
    A = pickle.load(fh)
mhw = B['mhw'].reshape(92, -1); hot = B['hot'].reshape(92, -1)
tdates, tdoy = B['tdates'], A['tdoy']
sst = A['sst'].reshape(92, -1); sea = A['sea']
thresh_s = A['thresh_s']

cnt = mhw.sum(axis=1)
print("cells-in-MHW per day around/beyond event:")
for t in range(85, 100):
    pass
for t in range(0, 92):
    if cnt[t] > 0 or (20 <= t <= 40):
        print(tdates[t].date(), "doy", tdoy[t], "cells:", int(cnt[t]), "hot:", int(hot[t].sum()))
