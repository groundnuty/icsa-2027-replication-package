import numpy as np, pickle, time, warnings
warnings.filterwarnings("ignore")

with open("/tmp/data.pkl","rb") as f:
    D = pickle.load(f)
data = D["data"]

# ---------- corrected day-of-year mapping: leap-year calendar by (month, day) ----------
# Jan1=1, Feb28=59, Feb29=60, Mar1=61, ..., Dec31=366 in EVERY year; non-leap years skip day 60.
CUM_LEAP = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # days before month m (leap calendar)
def doy_map(dates):  # dates: datetime64[D] array
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int)  # 0..11
    dd = (dates - dates.astype('datetime64[M]') + np.timedelta64(1,'D')).astype(int)
    return CUM_LEAP[m] + dd

chk = {'1992-02-28':59,'1992-02-29':60,'1992-03-01':61,'1993-02-28':59,'1993-03-01':61,
       '1993-12-31':366,'1996-12-31':366,'2000-02-29':60,'2001-01-01':1,'2005-06-01':153,
       '2005-08-31':244,'1992-01-01':1,'1992-12-31':366,'2002-12-31':366}
ok = all(int(doy_map(np.datetime64(s))[0] if np.ndim(doy_map(np.datetime64(s))) else doy_map(np.datetime64(s)))==v for s,v in chk.items())
arr = np.array([np.datetime64(s) for s in chk]); res = doy_map(arr)
ok = all(int(r)==v for r,v in zip(res, chk.values()))
print("doy mapping spot checks:", "OK" if ok else "FAIL")
print(dict(zip([str(a) for a in arr], res.tolist())))

# ---------- 1991..2003 values ----------
years_b = list(range(1991, 2004))
dates_list, vals_list = [], []
for y in years_b:
    nd = data[y].shape[0]
    dates_list.append(np.arange(np.datetime64(f"{y}-01-01"), np.datetime64(f"{y}-01-01")+np.timedelta64(nd,'D')))
    vals_list.append(data[y].reshape(nd, -1))
dates = np.concatenate(dates_list); vals = np.concatenate(vals_list, axis=0)
doys = doy_map(dates); yrs = dates.astype('datetime64[Y]').astype(int) + 1970
N = dates.size
print("dates:", N, dates[0], "->", dates[-1])

# ---------- pool masks per doy (baseline 1992-2002 dates with mapped doy d, windows +-5 calendar days) ----------
base = (yrs >= 1992) & (yrs <= 2002)
pool = {}
for d in range(1, 367):
    if d == 60: continue
    bdates = dates[base & (doys == d)]
    dif = np.abs((dates[:, None] - bdates[None, :]).astype('timedelta64[D]').astype(int))
    pool[d] = (dif <= 5).any(axis=1)
used = np.zeros(N, bool)
for d, m in pool.items(): used |= m
print("pool span:", dates[used].min(), "->", dates[used].max())
print("doy1 pool:", pool[1].sum(), "doy59:", pool[59].sum(), "doy61:", pool[61].sum(), "doy365:", pool[365].sum(), "doy366:", pool[366].sum())
feb29 = np.isin(dates, np.array(['1992-02-29','1996-02-29','2000-02-29'], dtype='datetime64[D]'))
for fd, i in zip(['1992-02-29','1996-02-29','2000-02-29'], np.where(feb29)[0]):
    print(fd, "in pools of doys:", [d for d in range(1,367) if d!=60 and pool[d][i]])
print("doy60 has own pool:", 60 in pool)
# spot windows
def inpool(dstr, d): return bool(pool[d][np.where(dates==np.datetime64(dstr))[0][0]])
print("doy61: 1993-02-24 in?", inpool('1993-02-24',61), "| 1993-03-06 in?", inpool('1993-03-06',61), "| 1993-02-23 in?", inpool('1993-02-23',61), "| 1993-03-07 in?", inpool('1993-03-07',61))
print("doy1: 1991-12-27 in?", inpool('1991-12-27',1), "| 1992-01-06 in?", inpool('1992-01-06',1), "| 1991-12-26 in?", inpool('1991-12-26',1))
print("doy366: 2003-01-05 in?", inpool('2003-01-05',366), "| 2003-01-06 in?", inpool('2003-01-06',366), "| 2002-12-26 in?", inpool('2002-12-26',366))
np.save("/tmp/vals.npy", vals)
with open("/tmp/pool2.pkl","wb") as f:
    pickle.dump({"pool": pool, "dates": dates, "doys": doys}, f, protocol=4)
print("stage1 done")
