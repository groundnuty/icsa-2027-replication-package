
import numpy as np

# Test with 10 data points
np.random.seed(42)
data = np.arange(1, 11, dtype=np.float64)  # 1,2,...,10
print("Data:", data)

for p in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99, 1.0]:
    result = np.quantile(data, p, method='hazen')
    print(f"p={p}: hazen = {result}")

# Manual calculation
def hazen_manual(data, p):
    data = np.sort(data)
    n = len(data)
    h = (n - 1) * p + 1  # 1-indexed position
    
    if h < 1:
        return data[0]
    if h >= n:
        return data[-1]
    
    j = int(np.floor(h))
    f = h - j
    # 1-indexed: data[j-1] and data[j]
    return (1 - f) * data[j-1] + f * data[j]

print("\nManual:")
for p in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99, 1.0]:
    result = hazen_manual(data, p)
    print(f"p={p}: hazen = {result}")
