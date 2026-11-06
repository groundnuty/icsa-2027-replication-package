
import numpy as np

# Test numpy nanquantile with method="hazen"
x = np.array([1.0, 2.0, 3.0, np.nan, 5.0])
try:
    r = np.nanquantile(x, 0.9, method="hazen")
    print("nanquantile hazen:", r)
except Exception as e:
    print("Error:", e)

# Also test regular quantile with method
try:
    r2 = np.quantile(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 0.9, method="hazen")
    print("quantile hazen:", r2)
except Exception as e:
    print("Error:", e)
