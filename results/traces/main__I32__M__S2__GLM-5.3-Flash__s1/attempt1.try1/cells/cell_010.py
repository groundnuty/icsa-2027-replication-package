import numpy as np, pickle, time, warnings
warnings.filterwarnings("ignore")

with open("/tmp/data.pkl","rb") as f:
    D = pickle.load(f)
data = D["data"]
with open("/tmp/pool2.pkl","rb") as f:
    P = pickle.load(f)
pool, dates = P["pool"], P["dates"]
vals = np.load("/tmp/vals.npy")  # (4748, 3600) float64

# sea cells (finite on every target day)
yr05 = data[2005]
t_idx = np.arange(151, 243)  # 2005-06-01..2005-08-31 within 2005 array (day 0 = Jan 1)
fin_all = np.all(np.isfinite(yr05[t_idx]), axis=0).reshape(-1)
print("sea cells:", fin_all.sum())

# ---- climatology & threshold ----
t0 = time.time()
TH = np.full((366, 3600), np.nan)
CL = np.full((366, 3600), np.nan)
for d in range(1, 367):
    if d == 60: continue
    v = vals[pool[d]]                      # (n, 3600)
    TH[d-1] = np.nanpercentile(v, 90, axis=0, method="hazen")
    CL[d-1] = np.nanmean(v, axis=0)
TH[59] = 0.5*(TH[58] + TH[60])
CL[59] = 0.5*(CL[58] + CL[60])
print("clim/thr computed %.1fs" % (time.time()-t0))
print("NaNs in TH:", np.isnan(TH).sum(), "NaNs in CL:", np.isnan(CL).sum())
print("TH doy 180 mean (region): %.3f K, CL doy 180 mean: %.3f K" % (np.nanmean(TH[179]), np.nanmean(CL[179])))
print("TH doy 15 mean: %.3f K, CL doy 15 mean: %.3f K" % (np.nanmean(TH[14]), np.nanmean(CL[14])))

# ---- circular 31-day moving mean ----
def circ31(A):
    ext = np.vstack([A[-15:], A, A[:15]])          # (396, 3600)
    c = np.vstack([np.zeros((1, A.shape[1])), np.cumsum(ext, axis=0)])
    return (c[31:] - c[:-31]) / 31.0               # (366, 3600)
THS = circ31(TH); CLS = circ31(CL)
print("smoothed. THS doy 180 mean %.3f, CLS doy 180 mean %.3f" % (np.nanmean(THS[179]), np.nanmean(CLS[179])))
# edge check: smoothed doy 1 should equal mean of raw doys 352..366 and 1..15 ... quick numeric check
manual = np.mean(TH[[i-1 for i in list(range(352,367))+list(range(1,16))]], axis=0)
print("smoothing wrap check max|diff|:", np.nanmax(np.abs(manual - THS[0])))

# ---- target period ----
sst = yr05[t_idx].reshape(92, -1)                   # (92, 3600) float64
CUM_LEAP = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
tdoy = CUM_LEAP[5] + 1 + np.arange(92)              # June 1 = 153 ... Aug 31 = 244
print("tdoy:", tdoy[0], tdoy[-1])
hot = sst >= THS[tdoy-1]                            # (92,3600) bool; NaN -> False
print("hot days total:", hot.sum(), "per-cell mean:", hot.mean())
np.save("/tmp/hot.npy", hot); np.save("/tmp/fin_all.npy", fin_all)
with open("/tmp/clim.pkl","wb") as f:
    pickle.dump({"THS": THS, "CLS": CLS, "tdoy": tdoy}, f, protocol=4)

# ---- per-cell events: runs >=5, join variants ----
def events_from_hot(h):  # h: (92,) bool -> list of (s,e) inclusive, 0-based
    d = np.diff(np.concatenate([[0], h.view(np.int8), [0]]))
    st = np.where(d==1)[0]; en = np.where(d==-1)[0]-1
    ev = [(int(a),int(b)) for a,b in zip(st,en) if b-a+1 >= 5]
    return ev

def join_literal(evs, h):  # join iff gap days (1 or 2) are ALL non-hot
    evs = list(evs); out = []
    for e in evs:
        if out:
            gap = e[0] - out[-1][1] - 1
            gs, ge = out[-1][1]+1, e[0]-1
            if 1 <= gap <= 2 and not h[gs:ge+1].any():
                out[-1] = (out[-1][0], e[1]); continue
        out.append(e)
    return out

def join_hobday(evs):  # join any gap of 1-2 days
    evs = list(evs); out = []
    for e in evs:
        if out and 1 <= e[0]-out[-1][1]-1 <= 2:
            out[-1] = (out[-1][0], e[1]); continue
        out.append(e)
    return out

mask_lit = np.zeros_like(hot); mask_hob = np.zeros_like(hot)
n_ev_lit = n_ev_hob = 0
n_cells_with_ev = 0
for c in range(3600):
    ev = events_from_hot(hot[:, c])
    if not ev: continue
    n_cells_with_ev += 1
    jl = join_literal(ev, hot[:, c]); jh = join_hobday(ev)
    n_ev_lit += len(jl); n_ev_hob += len(jh)
    for s,e in jl: mask_lit[s:e+1, c] = 1
    for s,e in jh: mask_hob[s:e+1, c] = 1
print("cells with per-cell MHW:", n_cells_with_ev, "| events literal:", n_ev_lit, "| events hobday:", n_ev_hob)
print("masks identical:", np.array_equal(mask_lit, mask_hob))
diff = (mask_lit != mask_hob).sum()
print("differing cell-days:", diff)
np.save("/tmp/mask_lit.npy", mask_lit); np.save("/tmp/mask_hob.npy", mask_hob)
