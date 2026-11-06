
import numpy as np
print("NumPy version:", np.__version__)

# Check the actual hazen implementation
# Let me look at the source
import inspect
from numpy.lib import function_base
# Try to find the quantile source
print(inspect.getsource(np.percentile))
