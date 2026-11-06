import numpy as np, warnings
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
def daterange(a,b):
    o=[]
    while a<=b: o.append(a); a+=timedelta(days=1)
    return o
base_dates = daterange(date(1991,12,27), date(2003,1,5))
base_all   = daterange(date(1992,1,1), date(2002,12,31))
dmap = {x: i for i, x in enumerate(base_dates)}
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd

ri, ck = 0, 0
def pool_dates_for(dd):
    s = set()
    for b in base_all:
        if doyf(b.month, b.day) == dd:
            for off in range(-5, 6):
                tt = b + timedelta(days=off)
                if date(1991,12,27) <= tt <= date(2003,1,5):
                    s.add(tt)
    return s

def hazen_p90(vals):
    v = sorted(vals); n = len(v)
    pos = min(max((n+1)*0.9 - 0.5, 0.0), n-1)
    lo = int(pos); site_g = pos-lo
    return v[lo] + (v[lo+1]-v[lo])*site_g if lo+1 < n else v[lo]

mord  = np.array([x.toordinal() for x in base_dates])
bords = np.array([x.toordinal() for x in base_all])
bdoy  = np.array([doyf(x.month, x.day) for x in base_all])

print(" doy  raw_pipeline   raw_indep     diff")
for dd in range(156, 187):
    b = bords[bdoy == dd]
    mask = np.zeros(4028, dtype=bool)
    for bo in b: mask |= (mord >= bo-5) & (mord <= bo+5)
    vals_vec = master[mask, ri, ck]
    q_pipe = np.nanquantile(vals_vec, 0.9, method="hazen")
    vals_ind = sorted(v for v in (master[dmap[tt], ri, ck] for tt in pool_dates_for(dd)) if np.isfinite(v))
    q_ind = hazen_p90(vals_ind)
    print(" %3d  %.9f  %.9f  %+.2e" % (dd, q_pipe, q_ind, q_pipe - q_ind))
    if dd == 158:
        # check pool identity
        set_vec = set()
        idx = np.where(mask)[0]
        for ix in idx: set_vec.add(base_dates[ix])
        print("   pool equal:", set_vec == pool_dates_for(dd), "sizes:", len(set_vec), len(pool_dates_for(dd)))
        print("   n finite pipe:", np.isfinite(vals_vec).sum(), " n finite ind:", len(vals_ind))
