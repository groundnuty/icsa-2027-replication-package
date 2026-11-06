import numpy as np
z = np.load('/work/interim.npz'); tc = np.load('/work/thr_clim.npz')
sst_t, sst_b, sea, li, oi = z['sst_t'], z['sst_b'], z['sea'], z['li'], z['oi']
thr, thr_s = tc['thr'], tc['thr_s']
NC=3600
origin = np.datetime64('1991-12-27','D')
def d2i(d64): return int((d64 - origin) // np.timedelta64(1,'D'))

c = 5
print("saved thr[doy153 idx152] cell5:", thr[152].reshape(NC)[c])
print("saved thr[doy200 idx199] cell5:", thr[199].reshape(NC)[c])
print("saved thr[doy10 idx9] cell5:", thr[9].reshape(NC)[c])
print("sea flag cell5:", bool(sea.reshape(NC)[c]))

# correct mapping
def doy_to_md_good(d):
    leap = d >= 61
    days = [31,29,31,30,31,30,31,31,30,31,30,31] if leap else [31,28,31,30,31,30,31,31,30,31,30,31]
    for m, nd in enumerate(days):
        if d <= nd: return m+1, d
        d -= nd
# broken mapping (always non-leap)
def doy_to_md_broken(d):
    days = [31,28,31,30,31,30,31,31,30,31,30,31]
    for m, nd in enumerate(days):
        if d <= nd: return m+1, d
        d -= nd

for d in [1, 59, 61, 153, 244, 365, 366]:
    mg, dg = doy_to_md_good(d); mb, db = doy_to_md_broken(d)
    nfin_g = 0; nfin_b = 0
    for y in range(1992, 2003):
        big = d2i(np.datetime64(f'{y:04d}-{mg:02d}-{dg:02d}','D'))
        nib = d2i(np.datetime64(f'{y:04d}-{mb:02d}-{db:02d}','D'))
        nfin_g += int(np.isfinite(sst_b[big-5:big+6].reshape(11, NC)[:, c]).sum())
        nfin_b += int(np.isfinite(sst_b[nib-5:nib+6].reshape(11, NC)[:, c]).sum())
    print(f"d={d}: good md=({mg},{dg}) nfin={nfin_g} | broken md=({mb},{db}) nfin={nfin_b}")
