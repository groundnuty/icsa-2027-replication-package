import numpy as np
x = np.arange(1, 122, dtype=float)  # 1..121
q = 0.9
for m in ["hazen","linear","weibull","averaged_inverted_cdf","median_unbiased","inverted_cdf"]:
    print(m, np.nanquantile(x, q, method=m))
# hand: hazen vi=(n+1)q-1
n = 121
vi = (n+1)*q - 1
print("hazen hand:", vi, "->", np.floor(vi)+ (vi-np.floor(vi))*(121))  # x[vi+1]...
i = int(np.floor(vi)); g = vi - i
print("hazen interp:", x[i] + g*(x[i+1]-x[i]))
print("122*0.9 =", repr((n+1)*q))
print("121*0.9 =", repr(n*q))
