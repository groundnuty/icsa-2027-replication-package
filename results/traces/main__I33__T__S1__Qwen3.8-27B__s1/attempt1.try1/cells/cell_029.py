
import numpy as np, pickle, time
t0 = time.time()
S_t = np.load('/work/work/S_t.npy')
TH_s = np.load('/work/work/TH_s.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates, sea = D['target'], D['sea']
ml = [31,29,31,30,31,30,31,31,30,31,30,31]
leap_cum = np.zeros(13, int)
for m in range(12): leap_cum[m+1] = leap_cum[m] + ml[m]
def doy(dt): return int(leap_cum[dt.month-1] + dt.day)

cells = sea
n = cells.shape[0]
T = S_t[:, cells[:,0], cells[:,1]]   # (92, n) float64
dys = np.array([doy(t) for t in target_dates])
thr = TH_s[dys - 1]                  # (92, n)
hot = T >= thr                        # (92, n)
print("hot day counts: min", int(hot.sum(0).min()), "max", int(hot.sum(0).max()), "total hot cells-days:", int(hot.sum()))

# per-cell: runs of >=5 consecutive hot days
def mhw_mask_from_hot(h):
    # h: (D, n) bool. returns (D, n) bool: per-cell MHW membership incl. joined gaps
    Dn, nn = h.shape
    M = np.zeros_like(h)
    # initial runs >=5
    # find run starts/ends per column via diff
    d = np.diff(np.concatenate([np.zeros((1,nn),bool), h, np.zeros((1,nn),bool)], axis=0), axis=0)
    starts = np.where(d == 1)[1:] if False else None
    # simpler: use positions
    starts = np.argwhere(d[:-1] == 1)  # (k, 2): (row-1, col)
    ends   = np.argwhere(d[:-1] == -1) # (k, 2): (row, col)
    # pair them up per column: for each column, starts/ends interleave
    # vectorise: create run-length per (row,col): count consecutive
    # alternative robust approach: iterate columns (n=3290, D=92 -> fine)
    for j in range(nn):
        hcol = h[:, j]
        i = 0
        while i < Dn:
            if hcol[i]:
                j2 = i
                while j2+1 < Dn and hcol[j2+1]: j2 += 1
                if j2 - i + 1 >= 5:
                    M[i:j2+1, j] = True
                i = j2 + 1
            else:
                i += 1
    # join gaps of 1-2 days (iterate to fixpoint)
    def pad(hh):
        return np.pad(hh, ((1,1),(0,0)), mode='constant', constant_values=False)
    Hp = pad(M)
    changed = True; it = 0
    while changed:
        changed = False; it += 1
        L1 = Hp[:-2]; L2 = Hp[:-3]; R1 = Hp[2:]; R2 = Hp[3:]
        fill = (~M) & (L1 | L2) & (R1 | R2)
        if fill.any():
            M |= fill; Hp = pad(M); changed = True
    return M

M = mhw_mask_from_hot(hot)
print("iterations:", it)
print("MHW cell-days:", int(M.sum()))

# per-cell stats
n_mhw_initial = 0
for j in range(n):
    # count initial runs of >=5 in hot[:,j]
    c = 0; i = 0
    while i < 92:
        if hot[i,j]:
            j2 = i
            while j2+1 < 92 and hot[j2+1, j]: j2 += 1
            if j2 - i + 1 >= 5: c += 1
            i = j2 + 1
        else: i += 1
    n_mhw_initial += c
n_mhw_final = 0
for j in range(n):
    c = 0; i = 0
    while i < 92:
        if M[i,j]:
            c += 1; i += 1
        else: i += 1
    n_mhw_final += c
print("initial per-cell MHWs:", n_mhw_initial, " after joining:", n_mhw_final)
print("cells with >=1 MHW:", int((M.sum(0)>0).sum()))

# regional active days & events
active = M.any(axis=1)  # (92,)
print("active days:", int(active.sum()), "of 92")
events = []
i = 0
while i < 92:
    if active[i]:
        j2 = i
        while j2+1 < 92 and active[j2+1]: j2 += 1
        events.append((target_dates[i].isoformat(), target_dates[j2].isoformat(), j2-i+1))
        i = j2 + 1
    else:
        i += 1
print("events:", events)

np.save('/work/work/M.npy', M)
np.save('/work/work/active.npy', active)
np.save('/work/work/hot.npy', hot)
print("done", round(time.time()-t0,1))
