import numpy as np

# Let me create a simple test
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
print("numpy hazen 90th:", np.percentile(data, 90, method='hazen'))

# Manual: n=10, p=0.9, h=(10+1)*0.9=9.9
# sorted = [1,2,3,4,5,6,7,8,9,10]
# position 9.9 (1-indexed), interpolate between pos 9 and 10
# = 9 + 0.9*(10-9) = 9.9
print("Expected: 9.9")

# Another test with different values
data2 = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0])
print("\nnumpy hazen 90th:", np.percentile(data2, 90, method='hazen'))
# n=10, p=0.9, h=9.9
# sorted = [10,20,...,100]
# = 90 + 0.9*(100-90) = 99
print("Expected: 99.0")
