
import numpy as np

# Test numpy hazen method with more values to understand the formula
x = np.arange(1, 122, dtype=np.float64)  # 121 values, 1 to 121
N = len(x)

# Standard formula: h = (N-1)*p + 1 (1-based)
h_std = (N-1)*0.9 + 1
print(f"N={N}, standard h (1-based): {h_std}")
print(f"Standard result: {np.percentile(x, 90, method='linear')}")
print(f"numpy hazen result: {np.percentile(x, 90, method='hazen')}")

# Try to figure out what formula numpy hazen uses
# Let's test with various N values
for N_test in [5, 10, 20, 50, 100, 121]:
    x_test = np.arange(1, N_test+1, dtype=np.float64)
    hazen = np.percentile(x_test, 90, method='hazen')
    linear = np.percentile(x_test, 90, method='linear')
    # What h (0-based) would give this result?
    h_0based = (hazen - 1)  # Since x[i] = i+1, hazen = h_0based + 1
    print(f"N={N_test}: hazen={hazen}, linear={linear}, h_0based={h_0based}")

print()
# Also test with non-sequential values
np.random.seed(42)
x_rand = np.random.rand(121) * 10
print("Random values test:")
print(f"  hazen: {np.percentile(x_rand, 90, method='hazen'):.6f}")
print(f"  linear: {np.percentile(x_rand, 90, method='linear'):.6f}")

# Compute what MATLAB would give
x_sorted = np.sort(x_rand)
h_std = (len(x_rand)-1)*0.9 + 1  # 1-based
idx_floor = int(np.floor(h_std)) - 1  # 0-based
g = h_std - np.floor(h_std)
matlab_result = (1-g)*x_sorted[idx_floor] + g*x_sorted[idx_floor+1]
print(f"  MATLAB formula: {matlab_result:.6f}")
