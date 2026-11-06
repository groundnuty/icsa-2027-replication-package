import numpy as np, pandas as pd, h5py, os, warnings, time
import xarray as xr

p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
I0, I1, J0, J1 = 182, 241, 690, 749
NI, NJ = I1-I0+1, J1-J0+1
t0 = time.time()

ds = xr.open_dataset(p, engine="h5netcdf")
times = pd.DatetimeIndex(ds["time"].values)
bidx = np.where((times >= "1991-12-27") & (times <= "2003-01-05"))[0]
bdates = times[bidx]
b0 = bdates[0]
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # leap scale: 29 Feb=60
bdoy = cum[bdates.month-1] + bdates.day
core = (bdates >= pd.Timestamp("1992-01-01")) & (bdates <= pd.Timestamp("2002-12-31"))
print("read span:", bdates[0].date(), "->", bdates[-1].date(), "| core baseline:", int(core.sum()), "days")

f = h5py.File(p, "r"); dvar = f["analysed_sst"]
B = np.empty((len(bidx), NI, NJ), dtype="float64")
for s in range(0, len(bidx), 250):
    e = min(s+250, len(bidx))
    B[s:e] = dvar[bidx[0]+s : bidx[0]+e, I0:I1+1, J0:J1+1].astype("float64")
print("baseline read", round(time.time()-t0,1), "s")

def pool_positions(d):
    """(A): +/-5 calendar days around each CORE baseline date with doy d."""
    centers = np.where(core & (bdoy == d))[0]
    return np.concatenate([np.arange(c-5, c+6) for c in centers])

def brute_positions(d):
    """Independent calendar-arithmetic construction of the same pool."""
    md = bdates[core & (bdoy == d)]
    dates = set()
    for c in md:
        for o in range(-5, 6):
            dates.add(c + pd.Timedelta(days=int(o)))
    return np.sort(np.array([ (dt - b0).days for dt in sorted(dates) ]))

# structural checks of interpretation (A)
pos1 = pool_positions(1)
print("d=1  pool:", bdates[pos1].min().date(), "..", bdates[pos1[pos1<pos1.max()-10]].max().date(), "+ next-year windows; n =", len(pos1))
print("     includes 1991-12-27..31:", bool(np.all(np.isin(np.arange((pd.Timestamp('1991-12-27')-b0).days, (pd.Timestamp('1991-12-31')-b0).days+1), pos1))))
for dd in (361, 362, 363, 364, 365):
    posd = pool_positions(dd)
    n2003 = int((bdates[posd] >= "2003-01-01").sum())
    print(f"d={dd}: reaches to {bdates[posd].max().date()}, n(2003 days)={n2003}")
pos366 = pool_positions(366)
print("d=366 pool dates:", [str(x.date()) for x in bdates[pos366]])
feb29 = (pd.Timestamp('1996-02-29') - b0).days
for dd in (55, 56, 57, 58, 59, 61, 62, 63, 64, 65, 366):
    print(f"  1996-02-29 in window(d={dd}):", bool(feb29 in pool_positions(dd)))
print("  1996-02-29 in window(d=60/1/365/2/364):",
      [bool(feb29 in pool_positions(dd)) for dd in (60, 1, 365, 2, 364)])

# validator agreement across many doys
ok = True
for dd in [1,2,3,4,5,6,31,55,58,59,60,61,65,101,152,200,243,300,356,360,361,364,365,366]:
    a, b = pool_positions(dd), brute_positions(dd)
    same = (len(a) == len(b)) and bool(np.all(a == b))
    ok &= same
    if not same: print("MISMATCH at doy", dd, len(a), len(b))
print("pool_positions == brute_positions for all tested doys:", bool(ok))
np.save("/work/B.npy", B)
print("B cached;", round(time.time()-t0,1), "s")
