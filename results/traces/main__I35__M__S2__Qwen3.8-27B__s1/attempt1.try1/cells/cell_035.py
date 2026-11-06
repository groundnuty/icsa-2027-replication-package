import numpy as np
sea = np.load("/tmp/sea.npy")
print("sea shape:", sea.shape, "dtype:", sea.dtype, "sum:", int(sea.sum()))
li, oi = np.where(sea)
print("first 8 pairs:", list(zip(li[:8].tolist(), oi[:8].tolist())))
print("pair 400:", li[400], oi[400])
print("li[360:370]:", li[360:370].tolist())
# is li monotonically non-decreasing (row-major)?
print("row-major:", bool((np.diff(li) >= 0).all()))
# where are the ones in row 6?
print("count row 6:", int(sea[6].sum()))
