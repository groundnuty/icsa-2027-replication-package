import numpy as np
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
d2i = {d: i for i, d in enumerate(dates)}
ext_n = d2i['2003-01-05'] + 1
ext = A[:ext_n]
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
cum = [0]
for m in mdays: cum.append(cum[-1]+m)
def doy(s): return cum[int(s[5:7])-1] + int(s[8:10])
doy_ext = np.array([doy(s) for s in dates[:ext_n]])
base_s, base_e = d2i['1992-01-01'], d2i['2002-12-31'] + 1
b_idx = np.arange(base_s, base_e); b_doy = doy_ext[b_idx]

def pool_dates(d):
    ib = b_idx[b_doy == d]
    starts = np.clip(ib-5, 0, ext_n-1); ends = np.clip(ib+5,0,ext_n-1)+1
    m = np.zeros(ext_n+1, np.int32); np.add.at(m, starts, 1); np.add.at(m, ends, -1)
    mask = np.cumsum(m)[:-1] > 0
    return np.where(mask)[0]

# verify pool date lists for edge cases
for d in [1, 59, 61, 366]:
    idx = pool_dates(d)
    ds_ = [dates[i] for i in idx]
    print(f"d={d}: n={len(ds_)} first={ds_[0]} last={ds_[-1]}")
    # list the year-boundary windows
    print("   windows:", ds_[:11], "...", ds_[-11:])
