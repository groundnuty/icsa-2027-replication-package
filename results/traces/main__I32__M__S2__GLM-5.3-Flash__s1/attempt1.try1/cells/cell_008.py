import numpy as np, pickle, time, warnings
warnings.filterwarnings("ignore")

with open("/tmp/data.pkl","rb") as f:
    D = pickle.load(f)
data = D["data"]  # year -> (ndays,60,60) float64

# ---------- day-of-year mapping (1..366, leap-aware) ----------
CUM = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
def days_before_month(y, m0):
    n = CUM[m0]
    if m0 >= 2 and (y%4==0 and (y%100!=0 or y%400==0)): n += 1
    return n
def doy_map(dates):  # dates: datetime64[D] array
    y = dates.astype('datetime64[Y]').astype(int) + 1970
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int)
    dd = (dates - dates.astype('datetime64[M]') + np.timedelta64(1,'D')).astype(int)
    return np.array([days_before_month(yy, mm) + d for yy, mm, d in zip(y, m, dd)])

# spot checks
chk = {np.datetime64('1992-02-28'):59, np.datetime64('1992-02-29'):60, np.datetime64('1992-03-01'):61,
       np.datetime64('1993-02-28'):59, np.datetime64('1993-03-01'):61, np.datetime64('1993-12-31'):365,
       np.datetime64('1996-12-31'):366, np.datetime64('2000-02-29'):60, np.datetime64('2001-01-01'):1,
       np.datetime64('2005-06-01'):152, np.datetime64('2005-08-31'):243, np.datetime64('1992-01-01'):1}
arr = np.array(list(chk.keys()))
res = doy_map(arr)
ok = all(int(r)==v for r,v in zip(res, chk.values()))
print("doy mapping spot checks:", "OK" if ok else "FAIL", list(zip([str(a) for a in arr], res.tolist())))

# ---------- assemble 1991..2003 date/value arrays (baseline + spill window years) ----------
years_b = list(range(1991, 2004))
vals_list, dates_list = [], []
for y in years_b:
    nd = data[y].shape[0]
    dates_list.append(np.arange(np.datetime64(f"{y}-01-01"), np.datetime64(f"{y}-01-01")+np.timedelta64(nd,'D')))
    vals_list.append(data[y].reshape(nd, -1))
dates = np.concatenate(dates_list)          # datetime64[D]
vals = np.concatenate(vals_list, axis=0)    # (N, 3600) float64
doys = doy_map(dates)
yrs = dates.astype('datetime64[Y]').astype(int) + 1970
N = dates.size
print("dates 1991-2003:", N, dates[0], dates[-1])

# ---------- pool masks per doy ----------
base = (yrs >= 1992) & (yrs <= 2002)
pool = {}
for d in range(1, 367):
    if d == 60:
        continue
    bdates = dates[base & (doys == d)]
    dif = np.abs((dates[:, None] - bdates[None, :]).astype('timedelta64[D]').astype(int))
    mask = (dif <= 5).any(axis=1)
    pool[d] = mask
# used date span check
used = np.zeros(N, dtype=bool)
for d, m in pool.items(): used |= m
print("pool date span:", dates[used].min(), dates[used].max())
print("all pools within 1991-12-27..2003-01-05:", dates[used].min()>=np.datetime64('1991-12-27') and dates[used].max()<=np.datetime64('2003-01-05'))
print("any 2005/2004 in pools:", bool((yrs[used]>=2004).any()))

# targeted checks
def has(dstr, d): return bool(pool[d][dates==np.datetime64(dstr)])
print("doy1 pool size:", pool[1].sum(), "| 1991-12-27 in doy1:", has('1991-12-27',1), "| 1992-01-06 in doy1:", has('1992-01-06',1), "| 1991-12-26 in doy1:", has('1991-12-26',1), "| 1992-01-07 in doy1:", has('1992-01-07',1))
feb29 = dates == np.array([np.datetime64('1992-02-29'), np.datetime64('1996-02-29'), np.datetime64('2000-02-29')])[:,None].any()
feb29 = np.isin(dates, np.array(['1992-02-29','1996-02-29','2000-02-29'], dtype='datetime64[D]'))
in59 = [int(d) for d in doys[feb29] if d in pool and pool[d][feb29][list(doys[feb29]).index(d)]]
# simpler: for each feb29 date, which doy pools contain it
for fd in ['1992-02-29','1996-02-29','2000-02-29']:
    i = int(np.where(dates==np.datetime64(fd))[0][0])
    ds_in = [d for d in range(1,367) if d!=60 and pool[d][i]]
    print(fd, "in pools of doys:", ds_in)
print("doy365 pool size:", pool[365].sum(), "| 2003-01-05 in doy365:", has('2003-01-05',365), "| 2003-01-06 in doy365:", has('2003-01-06',365))
print("doy366 pool size:", pool[366].sum())
print("doy60 in pool dict:", 60 in pool)
np.save("/tmp/vals.npy", vals)
with open("/tmp/pool.pkl","wb") as f:
    pickle.dump({"pool": pool, "dates": dates, "doys": doys}, f, protocol=4)
print("stage 1 done")
