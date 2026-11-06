
import numpy as np, pickle, time
t0 = time.time()
hot = np.load('/work/work/hot.npy') if False else None
S_t = np.load('/work/work/S_t.npy')
TH_s = np.load('/work/work/TH_s.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates, sea = D['target'], D['sea']
ml = [31,29,31,30,31,30,31,31,30,31,30,31]
leap_cum = np.zeros(13, int)
for m in range(12): leap_cum[m+1] = leap_cum[m] + ml[m]
def doy(dt): return int(leap_cum[dt.month-1] + dt.day)

cells = sea; n = cells.shape[0]; Dn = 92
T = S_t[:, cells[:,0], cells[:,1]]
dys = np.array([doy(t) for t in target_dates])
hot = T >= TH_s[dys - 1]
print("hot cell-days:", int(hot.sum()))

M = np.zeros_like(hot)
for j in range(n):
    hcol = hot[:, j]; i = 0
    while i < Dn:
        if hcol[i]:
            j2 = i
            while j2+1 < Dn and hcol[j2+1]: j2 += 1
            if j2 - i + 1 >= 5: M[i:j2+1, j] = True
            i = j2 + 1
        else:
            i += 1

idx = np.arange(Dn)
it = 0
while True:
    it += 1
    Hp = np.pad(M, ((1,2),(0,0)), mode='constant', constant_values=False)
    L1 = Hp[idx];      L2 = Hp[idx-1]
    R1 = Hp[idx+2];    R2 = Hp[idx+3]
    fill = (~M) & (L1 | L2) & (R1 | R2)
    if not fill.any(): break
    M |= fill
print("join iterations:", it, " MHW cell-days:", int(M.sum()))

n_init5 = 0
for j in range(n):
    hcol = hot[:, j]; i = 0
    while i < Dn:
        if hcol[i]:
            j2 = i
            while j2+1 < Dn and hcol[j2+1]: j2 += 1
            if j2 - i + 1 >= 5: n_init5 += 1
            i = j2 + 1
        else: i += 1
def count_runs(b):
    c = 0; i = 0
    while i < len(b):
        if b[i]: c += 1; i += 1
        else: i += 1
    return c
n_fin = sum(count_runs(M[:, j]) for j in range(n))
print("initial runs>=5:", n_init5, " final per-cell MHWs:", n_fin, " cells with MHW:", int((M.sum(0)>0).sum()))

active = M.any(axis=1)
print("active days:", int(active.sum()), "of 92")
events = []
i = 0
while i < len(active):
    if active[i]:
        j2 = i
        while j2+1 < len(active) and active[j2+1]: j2 += 1
        events.append((target_dates[i].isoformat(), target_dates[j2].isoformat(), j2-i+1))
        i = j2 + 1
    else:
        i += 1
print("events:")
for e in events: print("  ", e)

np.save('/work/work/M.npy', M)
np.save('/work/work/active.npy', active)
np.save('/work/work/hot.npy', hot)
with open('/work/work/events.pkl','wb') as f: pickle.dump(events, f)
print("done", round(time.time()-t0,1))
