
import numpy as np
a = np.random.rand(366, 1200)
ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
print("ext", ext.shape)
blk = ext[:, 0:1200]
w = np.lib.stride_tricks.sliding_window_view(blk, 31, axis=0)
print("w", w.shape)
print("w.sum(axis=1)", w.sum(axis=1).shape)
v = np.where(np.isfinite(w), w, 0.0)
print("v", v.shape, "v.sum(axis=1)", v.sum(axis=1).shape)
cnt = np.isfinite(w).sum(axis=1)
print("cnt", cnt.shape)
r = np.where(cnt > 0, v.sum(axis=1) / np.maximum(cnt, 1), np.nan)
print("r", r.shape)
