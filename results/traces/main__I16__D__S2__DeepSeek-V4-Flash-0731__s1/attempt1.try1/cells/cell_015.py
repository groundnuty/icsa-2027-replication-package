
import numpy as np
# Check numpy version and hazen method support
print(np.__version__)
# Test quantile with hazen
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print(np.quantile(data, 0.9, method='hazen'))
print(np.quantile(data, 0.9, method='linear'))
