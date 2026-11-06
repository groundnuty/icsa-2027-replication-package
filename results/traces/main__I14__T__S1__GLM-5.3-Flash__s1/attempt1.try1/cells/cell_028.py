import numpy as np, pickle, json, os

with open('/tmp/stepA2.pkl','rb') as fh: A = pickle.load(fh)
with open('/tmp/stepB2.pkl','rb') as fh: B = pickle.load(fh)
thresh_s, clim_s = A['thresh_s'], A['clim_s']
tdoy = A['tdoy']; sst = A['sst'].reshape(92,-1); sea = A['sea']

# re-verify smooth31 on final arrays against explicit modulo means
def smooth31(x):
    ext = np.concatenate([x[-15:], x, x[:15]], axis=0)
    cs = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(ext, axis=0)])
    return (cs[31:] - cs[:-31]) / 31.0
for name, arr in [('thresh', A['thresh_s']), ('clim', A['clim_s'])]:
    ok = True
    for d0 in [0, 59, 152, 243, 365]:
        idxs = [((d0+1 + k - 1) % 366) for k in range(-15, 16)]
        pass
    print(name, "shape", arr.shape)
# (recompute raw from mem to double check one value end-to-end)
mem = A['mem']; arr_sea = A['arr_sea']
d = 183
pool = arr_sea[mem[:, d-1]]
q = np.nanquantile(pool, 0.9, axis=0, method='hazen'); mu = np.nanmean(pool, axis=0)
idxs = [((d + k - 1) % 366) for k in range(-15, 16)]
print("doy183 cell10: thresh smooth-match:", np.allclose(A['thresh_s'][d-1, 10], np.concatenate([[np.nanquantile(arr_sea[mem[:, i-1], 10][:, None], 0.9, axis=0, method='hazen')[0] if False else np.nan for i in idxs]])) if False else
      np.isclose(A['thresh_s'][d-1, 10],
                 np.mean([np.nanquantile(arr_sea[mem[:, i-1]][:, 10], 0.9, method='hazen') for i in idxs])))
print("doy183 cell10: clim smooth-match:",
      np.isclose(A['clim_s'][d-1, 10], np.mean([np.nanmean(arr_sea[mem[:, i-1]][:, 10]) for i in idxs])))

# clim target-band identity between versions
with open('/tmp/stepA.pkl','rb') as fh: A1 = pickle.load(fh)
dc = np.abs(clim_s - A1['clim_s']).max(axis=1)
print("clim smoothed delta in target band: max", dc[152:244].max(), "| overall max", dc.max(), "at doy", int(np.argmax(dc))+1)

# final event/mask summary
mhw = B['mhw']; tdates = B['tdates']
print("mhw dtype/shape:", mhw.dtype, mhw.shape, "| ones:", int(mhw.sum()))
print("events:", B['ev'])
print("sea cells:", int(sea.sum()), "| land cells:", int((~sea).sum()))
print("land cells all zero in mask:", bool(mhw.reshape(92,-1)[:, ~sea].sum() == 0))
print("target span:", tdates[0].date(), "->", tdates[-1].date(), "n =", len(tdates))
print("lat range:", A['latvals'][0], A['latvals'][-1], "lon range:", A['lonvals'][0], A['lonvals'][-1])
