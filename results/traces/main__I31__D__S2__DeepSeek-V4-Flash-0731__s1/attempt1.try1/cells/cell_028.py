
import numpy as np

# Test smooth_wrap
arr = np.arange(366.0).reshape(366, 1, 1)
result = np.zeros_like(arr)
for d in range(366):
    indices = [(d - 15 + i) % 366 for i in range(31)]
    result[d] = np.mean(arr[indices], axis=0)

# Check a few values
# For d=15: indices 0-30, mean = 15
print(f"d=15: {result[15,0,0]:.2f} (expected ~15)")
# For d=0: indices 351-365, 0-15, mean = mean(351..365, 0..15) = (sum(351..365) + sum(0..15)) / 31
val_0 = (sum(range(351,366)) + sum(range(0,16))) / 31
print(f"d=0: {result[0,0,0]:.2f} (expected ~{val_0:.2f})")
# For d=365: indices 350-365, 0-14, mean = mean(350..365, 0..14) = (sum(350..365) + sum(0..14)) / 31
val_365 = (sum(range(350,366)) + sum(range(0,15))) / 31
print(f"d=365: {result[365,0,0]:.2f} (expected ~{val_365:.2f})")

# Verify the total number of indices per day is 31
for d in [0, 15, 100, 365]:
    indices = [(d - 15 + i) % 366 for i in range(31)]
    assert len(indices) == 31
print("Smooth_wrap verification passed")
