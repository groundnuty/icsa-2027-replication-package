import numpy as np
# emulate n=121, p=0.9 with a strictly increasing array v[i] = i+1 (1..121)
v = np.arange(1, 122, dtype=np.float64)
for meth in ("hazen", "linear"):
    print(meth, np.quantile(v, 0.9, method=meth))
# hand formulas
n = 121
h5 = (n + 1) * 0.9     # 109.8  -> type5: interp between v[109] and v[110] (1-based)
print("type5 hand:", (110 - h5) * v[108] + (h5 - 109) * v[109])  # 0-based idx 108,109
# what value does numpy hazen imply?
q = np.quantile(v, 0.9, method="hazen")
print("numpy hazen value:", q, " -> 1-based position:", q)
