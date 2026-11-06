import numpy as np, datetime as dt, os, pickle, time
print("persist:", os.path.exists('/tmp/persist_test.npy'), os.path.exists('/tmp/base_sst.npy'))

base_sst = np.load('/tmp/base_sst.npy')
targ_sst = np.load('/tmp/targ_sst.npy')
with open('/tmp/meta.pkl','rb') as f:
    meta = pickle.load(f)
base_dates = [dt.date.fromisoformat(s) for s in meta['base_dates']]
targ_dates = [dt.date.fromisoformat(s) for s in meta['targ_dates']]
print("loaded", base_sst.shape, targ_sst.shape)

def doy366(d):
    if d.month == 2 and d.day == 29:
        return 60
    if d.month <= 2:
        return (d - dt.date(d.year,1,1)).days + 1
    return 61 + (d - dt.date(d.year,3,1)).days

B0, B1 = dt.date(1992,1,1), dt.date(2002,12,31)
pool_idx = {}
total = 0
for xi, X in enumerate(base_dates):
    for off in range(-5, 6):
        B = X + dt.timedelta(days=off)
        if B0 <= B <= B1:
            d = doy366(B)
            if d != 60:
                pool_idx.setdefault(d, []).append(xi)
                total += 1
print("total assignments:", total, "(expected 44165 = 365*121)")
sizes = np.array([len(v) for v in pool_idx.values()])
print("n pools:", len(pool_idx), "has 60:", 60 in pool_idx, "pool sizes min/max/unique:", sizes.min(), sizes.max(), np.unique(sizes))
dmissing = [d for d in range(1,367) if d not in pool_idx]
print("missing d:", dmissing)

# structural check: pool 153 = May 27 - Jun 6 of each baseline year
expect = []
for y in range(1992, 2003):
    for off in range(-5, 6):
        expect.append((dt.date(y,6,1) + dt.timedelta(days=off)).isoformat())
got = sorted(base_dates[i].isoformat() for i in pool_idx[153])
print("pool 153 matches May27-Jun6 windows:", sorted(expect) == got, "n:", len(got))

# Feb 29 values in pools 55-59, 61-65 only
feb29_idx = [i for i,X in enumerate(base_dates) if (X.month,X.day)==(2,29)]
print("Feb29 dates:", [base_dates[i].isoformat() for i in feb29_idx])
for i in feb29_idx:
    ds = sorted(d for d,v in pool_idx.items() if i in v)
    print("  Feb29", base_dates[i].year, "in pools:", ds[:12], "... count:", len(ds), "contains 60:", 60 in ds)

# spillover membership
i911227 = base_dates.index(dt.date(1991,12,27)); i911231 = base_dates.index(dt.date(1991,12,31))
i030101 = base_dates.index(dt.date(2003,1,1)); i030105 = base_dates.index(dt.date(2003,1,5))
print("1991-12-27 in pools:", sorted(d for d,v in pool_idx.items() if i911227 in v))
print("1991-12-31 in pools:", sorted(d for d,v in pool_idx.items() if i911231 in v))
print("2003-01-01 in pools:", sorted(d for d,v in pool_idx.items() if i030101 in v))
print("2003-01-05 in pools:", sorted(d for d,v in pool_idx.items() if i030105 in v))

# sea cells
sea = np.isfinite(targ_sst.astype(np.float64)).all(axis=0)
print("sea cells:", sea.sum())
bs64 = base_sst.astype(np.float64)
fin_base_all = np.isfinite(bs64).all(axis=0)
print("sea cells finite on all baseline-window days:", (fin_base_all & sea).sum(), "== sea:", (fin_base_all & sea).sum()==sea.sum())
print("cells finite in target but not all baseline days:", int((sea & ~fin_base_all).sum()))
