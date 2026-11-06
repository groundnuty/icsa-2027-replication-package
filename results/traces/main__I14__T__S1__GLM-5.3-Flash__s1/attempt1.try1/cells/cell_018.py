import numpy as np, pickle

with open('/tmp/stepB.pkl','rb') as fh:
    B = pickle.load(fh)
with open('/tmp/stepA.pkl','rb') as fh:
    A = pickle.load(fh)
mhw = B['mhw'].reshape(92, -1); hot = B['hot'].reshape(92, -1)
tdates, tdoy = A['tdates'], A['tdoy']
sst = A['sst'].reshape(92, -1)
thresh_s = A['thresh_s']; latvals, lonvals = A['latvals'], A['lonvals']

c_on = np.where(mhw[31])[0]
c_end = np.where(mhw[38])[0]
print("n cells in MHW on Jul1:", len(c_on), "| on Jul8:", len(c_end))
onset_lat = sorted(set(latvals[c//60] for c in c_on))
onset_lon = sorted(set(lonvals[c%60] for c in c_on))
print("Jul1 MHW cells: lat range", onset_lat[0], "-", onset_lat[-1], "lon range", onset_lon[0], "-", onset_lon[-1])
end_lat = sorted(set(latvals[c//60] for c in c_end))
end_lon = sorted(set(lonvals[c%60] for c in c_end))
print("Jul8 MHW cells: lat range", end_lat[0], "-", end_lat[-1], "lon range", end_lon[0], "-", end_lon[-1])

for c in [int(c_on[0]), int(c_on[-1]), int(c_end[0]), int(c_end[-1])]:
    print(f"cell {c} (lat {latvals[c//60]:.2f}, lon {lonvals[c%60]:.2f}):")
    for t in range(29, 40):
        print(f"  {tdates[t].date()} doy {tdoy[t]:3d} sst {sst[t,c]:8.3f} thr {thresh_s[tdoy[t]-1,c]:8.3f} "
              f"hot={int(hot[t,c])} mhw={int(mhw[t,c])}")
