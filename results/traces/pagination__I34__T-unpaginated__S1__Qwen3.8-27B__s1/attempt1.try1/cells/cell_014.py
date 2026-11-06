import numpy as np
rng = np.random.default_rng(0)
x = rng.standard_normal((1, 366))

ext = np.concatenate([x[:, -15:], x, x[:, :15]], axis=1)
c = np.cumsum(ext, axis=1)
c = np.concatenate([np.zeros((x.shape[0], 1)), c], axis=1)
out = (c[:, 31:] - c[:, :-31]) / 31.0

for d in (0, 1, 15, 16, 59, 364, 365):
    lo = (d - 15) % 366; hi = (d + 15) % 366
    if lo <= hi:
        naive = x[0, lo:hi+1].mean()
    else:
        naive = np.concatenate([x[0, lo:], x[0, :hi+1]]).mean()
    print(d, "out", out[0, d], "naive", naive, "match", abs(out[0, d]-naive) < 1e-9)
