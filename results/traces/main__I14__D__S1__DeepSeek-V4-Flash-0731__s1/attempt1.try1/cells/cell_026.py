
import numpy as np

# Let me check what numpy's hazen does more carefully
# Test with different sample sizes and quantiles

for n in [2, 3, 4, 5, 10]:
    x = np.arange(1, n+1, dtype=float)
    print(f"\nn={n}, x={x}")
    for p in [0.1, 0.25, 0.5, 0.75, 0.9, 0.95]:
        q = np.percentile(x, p*100, method='hazen')
        # Expected from formula h = (n-0.5)*p + 0.5 (1-indexed)
        h = (n - 0.5) * p + 0.5
        # Interpolate
        h0 = h - 1  # 0-indexed
        i = int(np.floor(h0))
        frac = h0 - i
        if i >= n-1:
            expected = x[-1]
        else:
            expected = x[i] + frac * (x[i+1] - x[i])
        print(f"  p={p}: numpy={q}, expected={expected:.4f}, h={h:.4f}")
