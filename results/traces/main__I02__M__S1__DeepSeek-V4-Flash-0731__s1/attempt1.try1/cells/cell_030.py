
import numpy as np

# Test with 121 values (matching pool size)
np.random.seed(42)
data = np.random.randn(121) * 2 + 15
data = np.sort(data)

# Compute 90th percentile with different methods
q_hazen = np.quantile(data, 0.9, method='hazen')
q_linear = np.quantile(data, 0.9, method='linear')

# Manual type 5 (Hazen)
def hazen_manual(data, p):
    data = np.sort(data)
    n = len(data)
    h = (n - 1) * p + 1  # 1-indexed
    
    if h < 1:
        return data[0]
    if h >= n:
        return data[-1]
    
    j = int(np.floor(h))
    f = h - j
    return (1 - f) * data[j-1] + f * data[j]

q_manual = hazen_manual(data, 0.9)

print(f"Data: {len(data)} values, min={data[0]:.4f}, max={data[-1]:.4f}")
print(f"numpy hazen: {q_hazen:.6f}")
print(f"numpy linear: {q_linear:.6f}")
print(f"manual type 5: {q_manual:.6f}")

# Check if hazen == manual type 5 for larger arrays
print(f"hazen == manual: {np.isclose(q_hazen, q_manual)}")
print(f"hazen == linear: {np.isclose(q_hazen, q_linear)}")
print(f"linear == manual: {np.isclose(q_linear, q_manual)}")
