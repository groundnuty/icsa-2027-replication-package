
import numpy as np

# Test numpy's hazen method with various arrays
arr5 = np.array([1, 2, 3, 4, 5], dtype=np.float64)
print("N=5, p=0.9:", np.percentile(arr5, 90, method='hazen'))
print("N=5, p=0.5:", np.percentile(arr5, 50, method='hazen'))

arr10 = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)
print("N=10, p=0.9:", np.percentile(arr10, 90, method='hazen'))
print("N=10, p=0.5:", np.percentile(arr10, 50, method='hazen'))

# What does MATLAB give?
# For N=5, p=0.9: m = 0.9*4+1 = 4.6, k=4, Q = 4 + 0.6*(5-4) = 4.6
# For N=5, p=0.5: m = 0.5*4+1 = 3, k=3, Q = 3 (the median)
# For N=10, p=0.9: m = 0.9*9+1 = 9.1, k=9, Q = 9 + 0.1*1 = 9.1
# For N=10, p=0.5: m = 0.5*9+1 = 5.5, k=5, Q = 5 + 0.5*1 = 5.5

print("\nMATLAB expected values:")
print("N=5, p=0.9: 4.6")
print("N=5, p=0.5: 3.0")
print("N=10, p=0.9: 9.1")
print("N=10, p=0.5: 5.5")

print("\nnumpy hazen:")
print("N=5, p=0.9:", np.percentile(arr5, 90, method='hazen'))
print("N=5, p=0.5:", np.percentile(arr5, 50, method='hazen'))
print("N=10, p=0.9:", np.percentile(arr10, 90, method='hazen'))
print("N=10, p=0.5:", np.percentile(arr10, 50, method='hazen'))
