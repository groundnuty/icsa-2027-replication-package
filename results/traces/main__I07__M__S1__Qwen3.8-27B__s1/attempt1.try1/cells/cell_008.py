import numpy as np
for p in [0.1,0.25,0.5,0.75]:
    a = np.arange(1, 11, dtype=float)  # n=10
    print("p",p, np.quantile(a,p,method="hazen"))
# fit: h = (n+c)p + d, with 0.9c+d=0.5 from n=10,p=0.9 -> 9.5
# test candidate known HF type 6 (hazen): h = (n+0.35)p + 0.65? n=10: 10.35*.9+.65 = 9.965 no
# try h = (n+1)p - 0.6: 9.9-0.6=9.3 no
# h = p*(n - 1) + 1 - 0.1: 9.9+0.9=... let me just compute candidates
