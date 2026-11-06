import numpy as np, warnings
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']
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

dd = 159
vals = np.array([master[dmap[tt], ri, ck] for tt in pool_dates_for(dd)])
v = np.sort(vals)
n = len(v)
q_np = np.nanquantile(vals, 0.9, method="hazen")
q_lin = np.nanquantile(vals, 0.9, method="linear")
print("n =", n)
print("numpy hazen:  %.12f" % q_np)
print("numpy linear: %.12f" % q_lin)

def interp(h0):
    h0 = min(max(h0, 0.0), n-1)
    lo = int(h0); site_g = h0 - lo
    return v[lo] + (v[lo+1]-v[lo])*site_g if lo+1 < n else v[lo]

cands = {
 "type6/hazen (n+1)q-0.5": (n+1)*0.9 - 0.5,
 "type4 CIJ (n+1/3)q+1/3": (n+1/3)*0.9 + 1/3 - 1,
 "type7/linear (n-1)q": (n-1)*0.9,
 "weibull n*q": n*0.9,
 "invcdf (n-1)*q...": (n-1)*0.9,
 "(n+1)q": (n+1)*0.9,
 "(n+1)q-1": (n+1)*0.9 - 1,
 "(n-1)*q+?": None,
}
for name, h0 in cands.items():
    if h0 is None: continue
    print("  %-28s h0=%.6f  val=%.12f  diff_from_np=%+.3e" % (name, h0, interp(h0), interp(h0)-q_np))
# brute force: find h0 that reproduces q_np exactly
from scipy.optimize import brentq
f = lambda h: interp(h) - q_np
# search 100..120
import numpy as np2
grid = np.arange(100.0, 121.0, 1e-6)
vals_h = np.array([interp(h) for h in grid])
idx = int(np.argmin(np.abs(vals_h - q_np)))
print("grid-search best h0: %.6f  (residual %.3e)" % (grid[idx], vals_h[idx]-q_np))
