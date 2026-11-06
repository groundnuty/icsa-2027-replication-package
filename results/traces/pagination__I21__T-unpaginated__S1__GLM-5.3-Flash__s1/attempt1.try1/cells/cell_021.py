import numpy as np
x = np.arange(1, 11, dtype=float)  # 1..10
for p in [0.5, 0.9, 0.05]:
    q = np.quantile(x, p, method='hazen')
    n = len(x)
    # candidate formulas (0-based virtual index)
    cands = {
      'HF5: (n-1)p+0.5-1 = (n-1)p-0.5': (n-1)*p - 0.5,
      'hazenPP: np+0.5-1': n*p + 0.5 - 1,
      'type7: (n-1)p': (n-1)*p,
      'type6: (n+1)p-1': (n+1)*p - 1,
    }
    def interp(pos):
        lo = int(np.floor(pos)); site_g = pos - lo
        return x[lo] + site_g*(x[lo+1]-x[lo])
    print(f"p={p}: numpy={q}")
    for k, pos in cands.items():
        print(f"   {k} -> pos={pos:.3f} -> {interp(pos):.5f}")
