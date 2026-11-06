import numpy as np

# simple test
x = np.arange(1, 13, dtype=float)  # 1..12, n=12
print("n=12, p=0.9:")
print(" quantile hazen:", np.quantile(x, 0.9, method="hazen"))
print(" nanpercentile hazen:", np.nanpercentile(x, 0.9, method="hazen"))
print(" percentile hazen:", np.percentile(x, 90, method="hazen"))
# expected: v = n*q - 0.5 = 10.8 -> x[10] + 0.8*(x[11]-x[10]) = 11 + 0.8 = 11.8

x2 = np.arange(1, 122, dtype=float)  # 1..121
print("n=121, p=0.9:")
print(" quantile hazen:", np.quantile(x2, 0.9, method="hazen"))   # v = 108.9-0.5=108.4 -> x[108]+0.4*(x[109]-x[108]) = 109+0.4 = 109.4
print(" nanpercentile hazen:", np.nanpercentile(x2, 0.9, method="hazen"))

# with NaNs present
x3 = x2.copy()
x3[5] = np.nan
print("n=121 (1 nan), p=0.9:")
print(" nanpercentile hazen:", np.nanpercentile(x3, 0.9, method="hazen"))
print(" nanquantile hazen:", np.nanquantile(x3, 0.9, method="hazen"))
