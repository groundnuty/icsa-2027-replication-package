import numpy, scipy
print('numpy', numpy.__version__, 'scipy', scipy.__version__)
# check numpy percentile method='hazen' support
import numpy as np
a = np.array([1.,2,3,4,5,6,7,8,9,10])
print('hazen p90 of 1..10:', np.percentile(a, 90, method='hazen'))
# MATLAB quantile default: type 5. For [1..10], p90: h=(n-1)*p+1=9.1 -> x(9)+0.1*(x(10)-x(9)) = 9.1. Good.
# check np.quantile docstring method names
print(np.percentile.__doc__[:100])
