
# Verify smooth_circular with a simple test
def smooth_circular(arr):
    n = 366
    padded = np.concatenate([arr[-15:], arr, arr[:15]])
    result = np.zeros(n)
    for i in range(n):
        result[i] = np.mean(padded[i:i+31])
    return result

# Test with constant array
test = np.ones(366)
result = smooth_circular(test)
print("Constant array smoothed:", result[0], result[100], result[365])
assert np.allclose(result, 1.0)

# Test with simple ramp
test2 = np.arange(366, dtype=np.float64)
result2 = smooth_circular(test2)
# For day i (0-indexed), should be average of (i-15) to (i+15) mod 366
# For interior points (15 <= i <= 350), it should be mean of i-15 to i+15 = i
print("Ramp interior:", result2[50], "(expected ~50)")
print("Ramp edge 0:", result2[0], "(expected mean of 351-365 and 0-15)")
expected_edge = np.mean(np.concatenate([test2[351:], test2[:16]]))
print("Expected edge 0:", expected_edge)
