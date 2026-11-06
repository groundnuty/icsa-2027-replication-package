import numpy as np
for n in [10, 11, 20, 50, 121]:
    v = np.arange(1, n+1, dtype=float)
    q = np.quantile(v, 0.9, method='hazen')
    print(f"n={n}: hazen={q:.6f}   candidates: (n+1)p={(n+1)*0.9:.4f}, np+1={n*0.9+1:.4f}, 1+(n-1)p={1+(n-1)*0.9:.4f}, np={n*0.9:.4f}, (n+1/3)p+1/3={(n+1/3)*0.9+1/3:.4f}")
