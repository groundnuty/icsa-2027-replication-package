import numpy as np, pickle
hot = np.load("/tmp/hot.npy"); mask = np.load("/tmp/mask_lit.npy"); fin = np.load("/tmp/fin_all.npy")
# land cells must be 0 in mask
print("land cells hot anywhere:", mask[:, ~fin].sum())

# active days: any SEA cell in MHW
act = mask[:, fin].any(axis=1)
print("active days:", act.sum(), "of", mask.shape[0])
dd = np.diff(np.concatenate([[0], act.view(np.int8), [0]]))
st = np.where(dd==1)[0]; en = np.where(dd==-1)[0]-1
events = [(int(a), int(b)) for a, b in zip(st, en)]
t0 = np.datetime64('2005-06-01')
print("regional events:", len(events))
for s, e in events:
    print(f"  onset {t0 + np.timedelta64(s,'D')}  end {t0 + np.timedelta64(e,'D')}  len {e-s+1}")

# diagnostics: hot cells per day (sea cells only)
hp = hot[:, fin].mean(axis=1)
mc = mask[:, fin].sum(axis=1)
print("\nday-by-day (day# date, hot frac, n cells in MHW):")
for i in range(0, 92, 2):
    print(f"  {i:3d} {t0+np.timedelta64(i,'D')}  hot {hp[i]:.2f}  mhw {mc[i]:5d}")
# per-cell event counts
import collections
cnt = collections.Counter()
for c in range(3600):
    h = hot[:, c]
    d2 = np.diff(np.concatenate([[0], h.view(np.int8), [0]]))
    s2 = np.where(d2==1)[0]; e2 = np.where(d2==-1)[0]-1
    ev = [(a,b) for a,b in zip(s2,e2) if b-a+1>=5]
    # join literal
    out=[]
    for e in ev:
        if out:
            gs,ge = out[-1][1]+1, e[0]-1
            if 1<=e[0]-out[-1][1]-1<=2 and not h[gs:ge+1].any():
                out[-1]=(out[-1][0],e[1]); continue
        out.append(e)
    cnt[len(out)] += 1
print("\nper-cell event count distribution:", dict(cnt))
