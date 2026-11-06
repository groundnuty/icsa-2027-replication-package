import numpy as np, pickle

with open('/tmp/stepB.pkl','rb') as fh:
    B = pickle.load(fh)
with open('/tmp/stepA.pkl','rb') as fh:
    A = pickle.load(fh)
mhw = B['mhw'].reshape(92, -1); hot = B['hot'].reshape(92, -1)
tdates, tdoy = A['tdates'], A['tdoy']
sst = A['sst'].reshape(92, -1); sea = A['sea']
thresh_s = A['thresh_s']; latvals, lonvals = A['latvals'], A['lonvals']

t0, t1 = 30, 38   # Jun 30 .. Jul 8
# cell in MHW on Jul 1 (first active day)
c_on = np.where(mhw[31])[0]
print("cells in MHW on Jul 1:", c_on, "-> (lat,lon):", [(round(latvals[c//60],3), round(lonvals[c%60],3)) for c in c_on])
c_end = np.where(mhw[38])[0]
print("cells in MHW on Jul 8:", c_end, "-> (lat,lon):", [(round(latvals[c//60],3), round(lonvals[c%60],3)) for c in c_end])

for c in list(c_on) + list(c_end):
    print(f"\ncell {c} (lat {latvals[c//60]:.2f}, lon {lonvals[c%60]:.2f}) days Jun28-Jul10:")
    for t in range(27, 41):
        d = tdates[t].date()
        print(f"  {d} doy {tdoy[t]:3d} sst {sst[t,c]:8.3f} thr {thresh_s[tdoy[t]-1,c]:8.3f} "
              f"hot={int(hot[t,c])} mhw={int(mhw[t,c])}")

# longest run (length 7) location
def bf_runs(col):
    runs=[]; i=0; Tn=len(col)
    while i<Tn:
        if col[i]:
            j=i
            while j+1<Tn and col[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    return runs
sevens = [(c,s,e) for c in range(3600) for (s,e) in bf_runs(hot[:,c]) if e-s+1==7]
print("\nlength-7 runs:", [(c, str(tdates[s].date()), str(tdates[e].date()), round(latvals[c//60],2), round(lonvals[c%60],2)) for c,s,e in sevens])
