
import numpy as np

y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

# Test all methods
for method in ['linear', 'lower', 'higher', 'nearest', 'midpoint', 'hazen', 'weibull', 'median_unbiased', 'normal_unbiased']:
    try:
        val = np.percentile(y, 90, method=method)
        print(f'{method}: {val}')
    except:
        print(f'{method}: error')

# Let me check the position computation manually
# numpy.percentile with method='hazen'
# The documentation says:
# 'hazen': Type 5
#   if g = 0: Q(p) = x[j]
#   else: Q(p) = (1-g)x[j] + g x[j+1]
#   where j = floor((N+1)p) and g = (N+1)p - j
# Wait, but this would give j=9, g=0.9, value = 0.1*9 + 0.9*10 = 9.9
# But numpy gives 9.5. Let me check what numpy actually does.

# Let me try with a smaller example
x = np.array([1.0, 2.0, 3.0, 4.0])
for p in [0.25, 0.5, 0.75, 0.9]:
    val = np.percentile(x, p*100, method='hazen')
    print(f'hazen p={p} of [1,2,3,4]: {val}')
