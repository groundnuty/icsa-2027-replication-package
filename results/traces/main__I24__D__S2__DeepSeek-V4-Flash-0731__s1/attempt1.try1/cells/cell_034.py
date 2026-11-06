
import numpy as np

# Verify numpy's hazen (type 5) against the standard Hyndman-Fan type 5 formula
# Type 5 (Hazen): h = n*p + 0.5
# j = floor(h) - 1 (0-based), gamma = h - floor(h)
# Q = (1-gamma)*y[j] + gamma*y[j+1] (with clipping)

def hazen_manual(x, p):
    x_sorted = np.sort(x)
    n = len(x_sorted)
    h = n * p + 0.5
    j = int(np.floor(h)) - 1
    gamma = h - np.floor(h)
    j = max(0, min(j, n-2))
    return (1-gamma)*x_sorted[j] + gamma*x_sorted[j+1]

# Test
x = np.array([1.0, 2.0, 3.0, 4.0])
print("Manual hazen [1,2,3,4] p=0.9:", hazen_manual(x, 0.9))
print("Numpy hazen [1,2,3,4] p=0.9:", np.quantile(x, 0.9, method='hazen'))

x2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("\nManual hazen [1,2,3,4,5] p=0.9:", hazen_manual(x2, 0.9))
print("Numpy hazen [1,2,3,4,5] p=0.9:", np.quantile(x2, 0.9, method='hazen'))

x3 = np.array([1.0, 2.0, 3.0])
print("\nManual hazen [1,2,3] p=0.9:", hazen_manual(x3, 0.9))
print("Numpy hazen [1,2,3] p=0.9:", np.quantile(x3, 0.9, method='hazen'))

# Random test
np.random.seed(42)
for _ in range(5):
    data = np.random.randn(20)
    p = np.random.random()
    manual = hazen_manual(data, p)
    numpy_res = np.quantile(data, p, method='hazen')
    print(f"\nRandom test p={p:.3f}: manual={manual:.6f}, numpy={numpy_res:.6f}, diff={abs(manual-numpy_res):.2e}")
