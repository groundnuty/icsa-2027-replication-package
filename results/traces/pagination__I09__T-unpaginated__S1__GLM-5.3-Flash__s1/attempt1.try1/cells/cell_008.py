import numpy as np, json, datetime as dt, warnings, os

stack = np.load('/tmp/base_span.npy')
meta = json.load(open('/tmp/meta.json'))
span = [dt.date.fromisoformat(s) for s in meta['span']]
i0,i1,j0,j1 = meta['idx']
nlat, nlon = i1-i0+1, j1-j0+1
print('stack', stack.shape, '| region cells', nlat, 'x', nlon)

# month/day -> leap-calendar doy (1..366); Feb29=60, Mar1=61
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
doys = np.array([cum[d.month-1] + d.day for d in span], dtype=np.int64)
base_mask = np.array([1992 <= d.year <= 2002 for d in span])
print('baseline days used:', int(base_mask.sum()), '| distinct baseline doys:', len(set(doys[base_mask].tolist())))

T = np.full((366, nlat, nlon), np.nan)
C = np.full((366, nlat, nlon), np.nan)
sizes = []
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60:
            continue
        fwd = (doys - d) % 366
        bwd = (d - doys) % 366
        idx = np.where((fwd <= 5) | (bwd <= 5))[0]
        sizes.append(len(idx))
        pool = stack[idx]
        T[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        C[d-1] = np.nanmean(pool, axis=0)
        if d == 1:
            yrs = sorted({span[k].year for k in idx})
            print('pool(1): n =', len(idx), '| years:', yrs[0], '..', yrs[-1], '| n years:', len(yrs))
        if d == 59:
            n29 = sum(1 for k in idx if span[k].month==2 and span[k].day==29)
            print('pool(59): n =', len(idx), '| Feb29 values included:', n29, '(expect 3: 1992,1996,2000)')
        if d == 65:
            n29 = sum(1 for k in idx if span[k].month==2 and span[k].day==29)
            print('pool(65): n =', len(idx), '| Feb29 values included:', n29)
print('pool sizes: min', min(sizes), 'max', max(sizes))

# day 60 = mean of days 59 and 61
T[59] = 0.5*(T[58] + T[60])
C[59] = 0.5*(C[58] + C[60])

def circ31(A):
    pad = np.concatenate([A[-15:], A, A[:15]], axis=0)
    acc = np.zeros_like(A)
    for i in range(31):
        acc += pad[i:i+366]
    return acc / 31.0

Ts = circ31(T)
Cs = circ31(C)
np.save('/tmp/thr_smooth.npy', Ts)
np.save('/tmp/clim_smooth.npy', Cs)

print('NaN cells in raw threshold (land etc.):', int(np.isnan(T[200]).sum()))
print('NaN cells in smoothed threshold:', int(np.isnan(Ts[200]).sum()))
c = (30,30)
for dd in [1, 60, 153, 200, 244, 366]:
    print(f'doy {dd:3d}: cell(30,30) clim={Cs[dd-1][c]:.3f} K  thr={Ts[dd-1][c]:.3f} K  raw_thr={T[dd-1][c]:.3f} K')
aug = Ts[212:244]  # doys 213..244 (Aug)
fin = np.isfinite(aug)
print('Aug thresholds over cells: min %.3f max %.3f K' % (np.nanmin(aug), np.nanmax(aug)))
print('clim Aug: min %.3f max %.3f K' % (np.nanmin(Cs[212:244]), np.nanmax(Cs[212:244])))
