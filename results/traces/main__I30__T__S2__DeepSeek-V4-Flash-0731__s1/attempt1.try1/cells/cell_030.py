
import numpy as np

# Test Hazen method more carefully
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

for p in [0, 10, 25, 50, 75, 90, 100]:
    val = np.percentile(x, p, method='hazen')
    print(f"p={p}%: {val}")

# Also check with even more points
print()
x2 = np.array([float(i) for i in range(1, 101)])
for p in [10, 25, 50, 75, 90, 95]:
    val = np.percentile(x2, p, method='hazen')
    print(f"p={p}% of 1..100: {val}")
