import numpy as np

thr_raw = np.load("/tmp/thr_raw.npy")   # (366,60,60)
clim_raw = np.load("/tmp/clim_raw.npy")

def circ_moving_mean(arr, window=31):
    # arr: (366, ...) ; day d averages days d-15..d+15 modulo 366
    half = window // 2
    out = np.empty_like(arr)
    idx = [(np.arange(366) - off) % 366 for off in range(-half, half+1)]
    idx = np.array(idx)          # (31, 366)
    acc = np.zeros_like(arr)
    for k in range(window):
        acc += arr[idx[k]]
    return acc / window

thr = circ_moving_mean(thr_raw)
clim = circ_moving_mean(clim_raw)
np.save("/tmp/thr.npy", thr)
np.save("/tmp/clim.npy", clim)

c = 30, 30
print("cell(30,30) thr doy150-160:", np.round(thr[149:160, 30, 30], 4))
print("cell(30,30) clim doy150-160:", np.round(clim[149:160, 30, 30], 4))
print("all finite thr:", np.isfinite(thr).all(), "clim:", np.isfinite(clim).all())

# target analysis
tgt = np.load("/tmp/tgt.npy")
tt = np.load("/tmp/tgt_times.npy")
EPOCH = np.datetime64("1970-01-01")
tdates = EPOCH + tt.astype("timedelta64[D]")
years = tdates.astype("datetime64[Y]").astype(int) + 1970
doy_std = (tdates - (years-1970).astype("datetime64[Y]")).astype(int) + 1
leap = (years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))
doy_t = np.where(leap | (doy_std < 60), doy_std, doy_std + 1)
print("target doys:", doy_t[:5], doy_t[-5:])

hot = tgt >= thr[doy_t - 1]     # (92, 60, 60)
print("hot days frac:", hot.mean())
np.save("/tmp/hot.npy", hot)
