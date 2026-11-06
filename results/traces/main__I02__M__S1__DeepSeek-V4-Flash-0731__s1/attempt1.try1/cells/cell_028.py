
import numpy as np

# More detailed test
arr = np.array([1.0, 2.0, 3.0, 4.0])
for p in [0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0]:
    result = np.quantile(arr, p, method='hazen')
    print(f"p={p}: hazen result = {result}")

# Compare with other methods
for method in ['linear', 'hazen', 'inverted_cdf', 'averaged_inverted_cdf']:
    result = np.quantile(arr, 0.9, method=method)
    print(f"Method '{method}': {result}")

# Manual type 5 calculation
print("\nManual type 5 (Hazen):")
def type5(data, p):
    n = len(data)
    h = (n - 1) * p + 1
    idx = int(np.floor(h))
    frac = h - idx
    if idx < 1:
        return data[0]
    if idx >= n:
        return data[-1]
    return data[idx-1] + frac * (data[idx] - data[idx-1])

for p in [0.9]:
    print(f"p={p}: {type5(np.sort(arr), p)}")

print(f"\nnumpy version: {np.__version__}")
print(f"\nHelp for hazen:")
import inspect
help_str = str(np.quantile.__doc__)[:2000]
print(help_str[:1500])
