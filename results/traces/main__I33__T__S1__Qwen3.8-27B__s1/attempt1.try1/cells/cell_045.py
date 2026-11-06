
import numpy as np, pickle, datetime
# ---- independent re-derivation for cell (20, 30) regional coords ----
S_base = np.load('/work/work/S_base.npy')
S_t    = np.load('/work/work/S_t.npy')
TH_s = np.load('/work/work/TH_s.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
base_dates, target_dates, sea = D['base'], D['target'], D['sea']
with open('/work/work/pool_idx.pkl','rb') as f: pool_idx = pickle.load(f)

ml = [31,29,31,30,31,30,31,31,30,31,30,31]
lc = np.zeros(13, int)
for m in range(12): lc[m+1] = lc[m] + ml[m]
def doy(dt): return int(lc[dt.month-1] + dt.day)

i, j = 20, 30
ci = int(np.where((sea[:,0]==i)&(sea[:,1]==j))[0][0])
print("cell index:", ci, "is sea:", ci < len(sea))

# independent pool build for doy 215 (2014-08-02): collect baseline dates with doy 215, take +-5
target_doy = 215
pool_vals = []
B = datetime.date(1992,1,1)
while B <= datetime.date(2002,12,31):
    if doy(B) == target_doy:
        for k in range(-5, 6):
            t = B + datetime.timedelta(days=k)
            idx = base_dates.index(t)
            v = S_base[idx, i, j]
            if np.isfinite(v): pool_vals.append(float(v))
    B += datetime.timedelta(days=1)
print("pool size:", len(pool_vals), "(expect 121)")
q90 = float(np.quantile(np.array(pool_vals), 0.9, method='hazen'))
mean = float(np.mean(pool_vals))
print("independent q90:", q90, " vs saved TH[214,ci]:", TH_s[214, ci], " (pre-smooth TH_raw):")
TH = np.load('/work/work/TH_raw.npy')
print("  TH_raw[214,ci]:", TH[214, ci], " match:", np.isclose(q90, TH[214, ci]))
print("  CL check:", np.isclose(mean, np.load('/work/work/CL_s.npy')[214,ci] if False else TH[214,ci] and 0))  # placeholder
CL = np.load('/work/work/CL_s.npy')
# CL raw not saved; recompute smoothed from TH? No - recompute CL quickly for this cell
CLraw = np.empty(366)
for d in list(range(1,367)):
    if d == 60: continue
    pv = []
    B = datetime.date(1992,1,1)
    while B <= datetime.date(2002,12,31):
        if doy(B) == d:
            for k in range(-5, 6):
                v = S_base[base_dates.index(B + datetime.timedelta(days=k)), i, j]
                if np.isfinite(v): pv.append(float(v))
        B += datetime.timedelta(days=1)
    CLraw[d-1] = np.mean(pv)
CLraw[59] = 0.5*(CLraw[58]+CLraw[60])
offs = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
CLsm = CLraw[offs].mean(axis=1)
print("independent CL smoothed[214]:", CLsm[214], " saved:", CL[214, ci], " match:", np.isclose(CLsm[214], CL[214,ci]))
print("independent TH smoothed[214]:", end=" ")
THraw = TH[:, ci]
THsm = THraw[offs].mean(axis=1)
print(THsm[214], " saved:", TH_s[214, ci], " match:", np.isclose(THsm[214], TH_s[214, ci]))

# independent MHW for this cell
T = S_t[:, i, j]
dys = np.array([doy(t) for t in target_dates])
hotc = T >= TH_s[dys-1, ci]
Mref = np.zeros(92, bool)
r0 = []
kk = 0
while kk < 92:
    if hotc[kk]:
        z = kk
        while z+1 < 92 and hotc[z+1]: z += 1
        if z-kk+1 >= 5: r0.append((kk,z))
        kk = z+1
    else: kk += 1
merged = []
for r in r0:
    if merged and r[0]-merged[-1][1]-1 <= 2:  # gap<=2 (all-nonhot automatic)
        merged[-1] = (merged[-1][0], r[1])
    else:
        merged.append(r)
for (a,b) in merged: Mref[a:b+1] = True
Ma = np.load('/work/work/M_a.npy')
print("cell MHWs:", merged, " matches saved M_a:", np.array_equal(Mref, Ma[:, ci]))
