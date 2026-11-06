import numpy as np, pickle, datetime as dt

D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
B, T = D["B"], D["T"]
nb, nlat, nlon = B.shape
masks = pickle.load(open("/tmp/mhw_masks.pkl","rb"))["masks"]

sea = np.all(np.isfinite(T), axis=0)
cells = np.argwhere(sea); n_sea = cells.shape[0]
V = B[:, cells[:,0], cells[:,1]].T
assert np.isfinite(V).all()

mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mstart = [0]
for m in mlen: mstart.append(mstart[-1]+m)
def doy(d): return mstart[d.month-1] + d.day
tdays = D["tgt_dates"]
tdoys = np.array([doy(d) for d in tdays])

def quantile_all(P, method):
    Xs = np.sort(P, axis=1)
    n = P.shape[1]
    h0 = (n*0.9 - 0.5) if method == "hazen" else ((n-1)*0.9)
    j = int(np.floor(h0)); g = h0 - j
    return Xs[:, j] if g == 0 else Xs[:, j] + g*(Xs[:, j+1] - Xs[:, j])

def smooth31(A):
    idx = np.array([[(d-15+k) % 366 for k in range(31)] for d in range(366)])
    return A.take(idx, axis=1).mean(axis=2)   # (n,366)

# sanity check smoothing with wraparound
test = np.zeros((1,366)); test[0,0] = 31.0   # day 1 gets 31 spread over 31 days
s = smooth31(test)
print("smooth sanity: sum over d of s[d] should be 31 ->", s[0].sum(), " max:", s[0].max())

def pipeline(method):
    Th = np.empty((n_sea,366)); Cl = np.empty((n_sea,366))
    for d in range(1,367):
        if d == 60: continue
        P = V[:, masks[d]]
        Th[:,d-1] = quantile_all(P, method)
        Cl[:,d-1] = P.mean(axis=1)
    Th[:,59] = (Th[:,58]+Th[:,60])/2.0
    Cl[:,59] = (Cl[:,58]+Cl[:,60])/2.0
    Ths = smooth31(Th); Cls = smooth31(Cl)
    msk = np.zeros((92, nlat, nlon), dtype=np.uint8)
    for ci, (i, j) in enumerate(cells):
        h = T[:, i, j] >= Ths[ci, tdoys-1]
        runs = []
        k = 0
        while k < 92:
            if h[k]:
                l = k
                while l+1 < 92 and h[l+1]: l += 1
                if l-k+1 >= 5: runs.append([k, l])
                k = l+1
            else:
                k += 1
        merged = []
        for s_, e_ in runs:
            if merged and s_ - merged[-1][1] - 1 <= 2:
                merged[-1][1] = e_
            else:
                merged.append([s_, e_])
        for s_, e_ in merged:
            msk[s_:e_+1, i, j] = 1
    active = (msk.sum(axis=(1,2)) > 0)
    evs = []
    k = 0
    while k < 92:
        if active[k]:
            l = k
            while l+1 < 92 and active[l+1]: l += 1
            evs.append((str(tdays[k]), str(tdays[l])))
            k = l+1
        else:
            k += 1
    return Ths, Cls, msk, evs

res_h = pipeline("hazen")
res_l = pipeline("linear")
print("hazen events: ", res_h[3])
print("linear events:", res_l[3])
print("mask equal:", bool((res_h[2]==res_l[2]).all()),
      " diff cells*days:", int((res_h[2]!=res_l[2]).sum()))
print("total mhw cell-days (hazen):", int(res_h[2].sum()),
      " active days:", int((res_h[2].sum(axis=(1,2))>0).sum()))
pickle.dump({"Ths_h":res_h[0],"Cl_h":res_h[1],"Ths_l":res_l[0],"Cl_l":res_l[1],
             "msk_h":res_h[2],"msk_l":res_l[2],"evs_h":res_h[3],"evs_l":res_l[3],
             "tdoys":tdoys}, open("/tmp/mhw_results.pkl","wb"))
print("saved")