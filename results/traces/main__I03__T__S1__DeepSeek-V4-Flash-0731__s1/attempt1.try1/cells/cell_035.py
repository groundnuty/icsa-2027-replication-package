
import numpy as np
print(np.__version__)

# Test hazen method
data = np.array([1.0, 2.0, 3.0, 4.0])
p50 = np.percentile(data, 50, method='hazen')
print(f"Hazen 50th percentile: {p50}")

# Test with the default
p50_default = np.percentile(data, 50)
print(f"Default 50th percentile: {p50_default}")

# Verify with a more complex example
data2 = np.random.randn(1000)
p90_hazen = np.percentile(data2, 90, method='hazen')
p90_linear = np.percentile(data2, 90)
print(f"Hazen 90th: {p90_hazen:.6f}")
print(f"Linear 90th: {p90_linear:.6f}")
