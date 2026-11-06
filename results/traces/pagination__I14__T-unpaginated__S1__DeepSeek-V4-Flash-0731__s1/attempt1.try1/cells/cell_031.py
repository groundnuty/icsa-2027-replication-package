
import numpy as np

# Test: verify hazen method matches MATLAB quantile
# MATLAB's quantile default is type 5 (Hyndman-Fan), which numpy calls "hazen"
data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

# numpy method='hazen'
q_hazen = np.quantile(data, 0.9, method='hazen')
q_linear = np.quantile(data, 0.9, method='linear')

print(f"numpy hazen (type 5): {q_hazen}")
print(f"numpy linear (type 7): {q_linear}")

# Verify: for MATLAB type 5 (hazen), the quantile is computed as:
# h = (N-1)*p + 1 for 1-based, or (N-1)*p for 0-based interpolation
# For N=10, p=0.9: h = 9*0.9 = 8.1, so value = data[8] + 0.1*(data[9]-data[8])
# = 9 + 0.1*(10-9) = 9.1
print(f"Expected hazen: 9.1")
