
import numpy as np

# Test numpy's hazen method
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("90th percentile with hazen:", np.percentile(x, 90, method='hazen'))
print("90th percentile with linear:", np.percentile(x, 90, method='linear'))

# Verify with a known example
x2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
print("90th percentile with hazen:", np.percentile(x2, 90, method='hazen'))

# MATLAB's quantile is the same as numpy's default which is 'linear' (type 7), 
# but the task says it uses 'hazen' (type 5). Let me verify.
# Actually wait, let me re-read: "computed as MATLAB's quantile does by default, which is numpy's method="hazen" (Hyndman–Fan type 5)"
# Hmm, that seems wrong. MATLAB's default quantile method is type 5 (Hazen), while numpy's default is type 7 (linear).
# But the task explicitly says it uses method="hazen", so let me use that.

# Check what numpy method="hazen" does
print("Test with some values:")
test = np.array([10.0, 20.0, 30.0])
print("  hazen p50:", np.percentile(test, 50, method='hazen'))
