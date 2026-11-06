import numpy as np, os
root = os.path.dirname(np.__file__)
lines = open(f"{root}/lib/_function_base_impl.py").read().splitlines()
import re
m = re.search(r'def _compute_virtual_index', "\n".join(lines))
i = next(i for i,l in enumerate(lines) if 'def _compute_virtual_index' in l)
print("\n".join(lines[i:i+30]))
