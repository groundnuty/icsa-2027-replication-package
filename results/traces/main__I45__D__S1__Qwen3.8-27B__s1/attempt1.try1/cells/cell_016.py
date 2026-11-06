import numpy as np, os
root = os.path.dirname(np.__file__)
path = f"{root}/lib/_function_base_impl.py"
lines = open(path).read().splitlines()
print("\n".join(lines[100:175]))
# find where h is computed for interpolation: search 'h = ' patterns near _quantile_ functions
import re
for i, l in enumerate(lines):
    if 'def _quantile_' in l or '_get_isfinite' in l:
        print(i, l)
# print the generic interpolation helper
idx = [i for i,l in enumerate(lines) if 'def _quantile_interpolation' in l or 'interpolation' in l and 'def ' in l]
print(idx[:10])
