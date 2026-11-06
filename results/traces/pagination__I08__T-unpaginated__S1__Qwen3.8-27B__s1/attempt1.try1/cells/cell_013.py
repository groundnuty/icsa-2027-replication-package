
import numpy as np
a = np.arange(1, 122, dtype=float)  # 1..121, n=121
p = 0.9
n = len(a)
for m in ['hazen','weibull','linear','median_unbiased','normal_unbiased','interpolated_inverted_cdf']:
    print(m, np.quantile(a, p, method=m))
# formulas
print("Type3  0.5+n*p =", 0.5 + n*p)
print("Type4  0.5+(n+0.5)p =", 0.5 + (n+0.5)*p)
print("Type5  (n+1)p-1 =", (n+1)*p - 1)
print("Type7  1+(n-1)p =", 1 + (n-1)*p)
print("Type6  -0.375+(n-0.25)p =", -0.375 + (n-0.25)*p)
print("Type8  1/3+(n+1/3)p =", 1/3 + (n+1/3)*p)
