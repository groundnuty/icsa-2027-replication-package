
import numpy as np

# Check numpy percentile methods
# Let me look at what "hazen" actually does in numpy
# From numpy docs: https://numpy.org/doc/stable/reference/generated/numpy.percentile.html
# 
# The methods are based on Hyndman and Fan (1996):
# Type 5 (Hazen): h = (n - 1) * p + 1/2

# Wait, let me check - maybe numpy's hazan is actually different from type 5?
# Actually, let me check the numpy source code.

# Looking at the numpy source:
# 'hazen' corresponds to Hyndman-Fan type 5: h = (n - 1) * p + 1/2

# For n=5, p=0.9 (90th percentile):
# h = 4 * 0.9 + 1/2 = 3.6 + 0.5 = 4.1
# This is NOT 4.6.

# Hmm, wait. Let me check the actual numpy definition more carefully.

# Let me look at the methods table:
# hazen: h = (n-1)*p + 1/2

# For [1,2,3,4,5], 90th percentile:
# h = 4*0.9 + 0.5 = 4.1
# floor(h) = 4, so interpolate between x[3]=4 and x[4]=5
# 4 + 0.1*(5-4) = 4.1

# But numpy gives 5.0. That doesn't match.

# Let me try yet another interpretation
print("Testing various methods:")
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
for method in ['linear', 'lower', 'higher', 'nearest', 'midpoint', 'hazen', 'weibull']:
    try:
        p = np.percentile(x, 90, method=method)
        print(f"  method={method}: {p}")
    except:
        pass
