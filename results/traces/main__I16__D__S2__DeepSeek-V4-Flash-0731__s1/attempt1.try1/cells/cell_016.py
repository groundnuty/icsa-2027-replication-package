
import numpy as np
data = np.array([[1.0, np.nan], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0], [5.0, 6.0]])
print(np.nanquantile(data, 0.9, axis=0, method='hazen'))
print(np.nanmean(data, axis=0))
