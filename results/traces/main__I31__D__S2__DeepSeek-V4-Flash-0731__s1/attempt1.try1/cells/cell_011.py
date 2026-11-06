
import numpy as np
# Check numpy percentile methods
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print(np.percentile(x, 90, method='hazen'))
print(np.percentile(x, 90))
# Check numpy version
print(np.__version__)
