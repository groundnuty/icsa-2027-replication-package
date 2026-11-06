
import numpy as np

# Simple test with 10 values
data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
p = 0.9

# MATLAB quantile default (Hazen/Hyndman-Fan type 5)
# h = (n+1)*p = 11*0.9 = 9.9
# value = x[floor(h)-1] + (h - floor(h)) * (x[ceil(h)-1] - x[floor(h)-1])
#        = x[8] + 0.9 * (x[9] - x[8]) 
#        = 9 + 0.9 * (10 - 9) = 9.9

# numpy hazen
print("numpy hazen:", np.percentile(data, 90, method='hazen'))
# Expected: 9.9

# Also test with method='linear' (numpy default, also type 7)
print("numpy linear:", np.percentile(data, 90, method='linear'))
# h = (n-1)*p + 1 = 9*0.9 + 1 = 9.1
# value = x[floor(9.1)-1] + 0.1*(x[ceil(9.1)-1] - x[floor(9.1)-1])
#        = x[8] + 0.1*(x[9]-x[8]) = 9 + 0.1 = 9.1

# Hazen should be 9.9
print("Expected Hazen: 9.9")
print("Expected linear: 9.1")
