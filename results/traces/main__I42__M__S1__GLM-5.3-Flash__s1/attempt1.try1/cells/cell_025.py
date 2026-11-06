import numpy as np
lr = np.zeros((60,60), dtype=int)
hot_finite = np.load("/work/hot_finite.npy")
def longest_run(m1):
    best=0; cur=0
    for v in m1:
        cur = cur+1 if v else 0
        best = max(best, cur)
    return best
for ii in range(60):
    for jj in range(60):
        lr[ii,jj] = longest_run(hot_finite[:,ii,jj])
rows, cols = np.where(lr >= 5)
print("cells with run >=5:")
for r, c in zip(rows, cols):
    # print the hot-day pattern
    m = hot_finite[:, r, c]
    idx = np.where(m)[0]
    print(f"  cell({r},{c}): days {list(idx)}")
