import numpy as np, pickle

with open('/tmp/stepB.pkl','rb') as fh:
    B = pickle.load(fh)
with open('/tmp/stepA.pkl','rb') as fh:
    A = pickle.load(fh)
mhw = B['mhw'].reshape(92, -1); hot = B['hot'].reshape(92, -1)
tdates, tdoy = A['tdates'], A['tdoy']
sst = A['sst'].reshape(92, -1)
thresh_s = A['thresh_s']; latvals, lonvals = A['latvals'], A['lonvals']

c_on = np.where(mhw[30])[0]   # Jul 1
c_end = np.where(mhw[37])[0]  # Jul 8
print("Jul1 cells:", len(c_on), [f"({latvals[c//60]:.2f},{lonvals[c%60]:.2f})" for c in c_on])
print("Jul8 cells:", len(c_end), [f"({latvals[c//60]:.2f},{lonvals[c%60]:.2f})" for c in c_end])

for c in [int(c_on[0]), int(c_end[0])]:
    print(f"cell {c} (lat {latvals[c//60]:.2f}, lon {lonvals[c%60]:.2f}):")
    for t in range(28, 41):
        print(f"  {tdates[t].date()} doy {tdoy[t]:3d} sst {sst[t,c]:8.3f} thr {thresh_s[tdoy[t]-1,c]:8.3f} "
              f"hot={int(hot[t,c])} mhw={int(mhw[t,c])}")
