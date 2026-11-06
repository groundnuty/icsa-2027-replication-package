import numpy as np
print("hazen median 1..10:", np.quantile(np.arange(1.,11.), 0.5, method="hazen"))
print("hazen q0.9 of [1,2,3,4]:", np.quantile(np.array([1.,2,3,4]), 0.9, method="hazen"))
print("hazen q0.9 of 1..10:", np.quantile(np.arange(1.,11.), 0.9, method="hazen"))
print("hazen q0.9 of 1..11:", np.quantile(np.arange(1.,12.), 0.9, method="hazen"))
print("linear(default) q0.9 of [1,2,3,4]:", np.quantile(np.array([1.,2,3,4]), 0.9))
