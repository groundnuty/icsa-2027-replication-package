import numpy as np
hot = np.load('/work/hot.npy'); mask = np.load('/work/mask.npy')
T, C = hot.shape
c = 438

prev = np.empty(T, bool); prev[0] = False; prev[1:] = hot[:, c][:-1]
nxt  = np.empty(T, bool); nxt[-1] = False; nxt[:-1] = hot[:, c][1:]
starts1 = hot[:, c] & ~prev
ends1 = hot[:, c] & ~nxt
print("starts:", np.flatnonzero(starts1), "ends:", np.flatnonzero(ends1))

end_idx_c = np.where(ends1, np.arange(T), 0)
run_id_start_c = np.maximum.accumulate(np.where(starts1, np.arange(T), 0))
run_id_end_c = np.minimum.accumulate(end_idx_c[::-1])[::-1]
runlen_c = run_id_end_c - run_id_start_c + 1
R_c = (runlen_c >= 5) & hot[:, c]
print("R days:", np.flatnonzero(R_c).tolist())
print("runlen around 25-33:", runlen_c[23:36].tolist())
