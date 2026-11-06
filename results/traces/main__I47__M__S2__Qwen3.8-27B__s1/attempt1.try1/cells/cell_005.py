import numpy as np
print("numpy:", np.__version__)
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("hazen q90:", np.quantile(x, 0.9, method="hazen"))  # expect 4.0 + 0.5*(5-4)=4.5? (n-1)*0.9=3.6 -> 4.5
import pandas as pd
print(pd.__version__)
