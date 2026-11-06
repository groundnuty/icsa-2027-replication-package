import numpy as np, os
block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
sea_cells = np.load("/tmp/sea_cells.npy")
thr = np.load("/tmp/thr_smooth.npy")
clim = np.load("/tmp/clim_smooth.npy")
nb = 4028
target_days = alldays[nb:]; nt = len(target_days)
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of(s):
    m, d = int(s[5:7]), int(s[8:10]); return cum_before[m-1] + d
sst = block[nb:].astype(np.float64)
tdoy = np.array([doy_of(s) for s in target_days])
thr_t = thr[tdoy - 1]
mhw = np.load("/tmp/mhw_mask.npy")
# sample values inside the event
t = target_days.index("2004-08-09")
cells = np.argwhere(mhw[t])
print("event day 2004-08-09, sample cells:")
for r, l in cells[:6]:
    print(f"  lat-idx {r} lon-idx {l}: SST={sst[t,r,l]:.3f} K  thr={thr_t[t,r,l]:.3f} K  clim={clim[tdoy[t]-1,r,l]:.3f} K  anom={sst[t,r,l]-clim[tdoy[t]-1,r,l]:.3f} K")
# a non-event day for contrast
t2 = target_days.index("2004-07-15")
hotc = np.argwhere(sst[t2] >= thr_t[t2])
print("2004-07-15: hot cells:", len(hotc), "| mhw cells:", int(mhw[t2].sum()))
r, l = cells[0]
print("same cell on 2004-07-15: SST=%.3f thr=%.3f" % (sst[t2,r,l], thr_t[t2,r,l]))
print("cwd:", os.getcwd())
