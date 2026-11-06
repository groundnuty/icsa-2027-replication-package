import numpy as np, datetime as dt

def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n

d0 = dt.date(1982,1,1)
b_lo = dt.date(1991,12,27)
bstart = (b_lo - d0).days  # global index of B[0]
baseline = [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
bdoy = {b: doy_of(b) for b in baseline}

def correct_pool_indices(d):
    """global date indices of pool dates for doy d (None if d==60)"""
    if d == 60: return None
    centers = [b for b in baseline if bdoy[b] == d]
    idxs = []
    for c in centers:
        ci = (c - d0).days
        idxs.extend(range(ci-5, ci+6))
    return np.array(sorted(set(idxs)))

def mask_pool_indices(d):
    """my previous (wrong) approach: baseline dates with doy in [d-5, d+5]"""
    if d == 60: return None
    idxs = [ (b - d0).days for b in baseline if abs(bdoy[b] - d) <= 5 ]
    return np.array(sorted(idxs))

# compare for several doys
for d in [1, 56, 60, 61, 153, 244, 366]:
    ci = correct_pool_indices(d)
    mi = mask_pool_indices(d)
    if ci is None:
        print("doy", d, ": no pool of its own"); continue
    same = (len(ci)==len(mi)) and np.array_equal(ci, mi)
    # convert to dates for a human check
    cd = [d0+dt.timedelta(days=int(i)) for i in ci[:3]]
    print(f"doy {d:3d}: correct n={len(ci)} range {cd[0]}..{d0+dt.timedelta(days=int(ci[-1]))} | mask n={len(mi)} | identical: {same}")
    if not same:
        only_correct = set(ci)-set(mi); only_mask = set(mi)-set(ci)
        ex = sorted(only_correct)[:2]; exm = sorted(only_mask)[:2]
        print("   e.g. in correct only:", [str(d0+dt.timedelta(days=int(i))) for i in ex],
              "| in mask only:", [str(d0+dt.timedelta(days=int(i))) for i in exm])
