
import numpy as np
import inspect
from numpy.lib._function_base_impl import _QuantileMethods

# Get more context
import linecache
import sys

# Print the full source of the module around the hazen definition
import numpy.lib._function_base_impl as mod
source = inspect.getsource(mod)
# Find "hazen" in the source
lines = source.split('\n')
for i, line in enumerate(lines):
    if 'hazen' in line.lower():
        for j in range(max(0, i-2), min(len(lines), i+5)):
            print(f"{j}: {lines[j]}")
        print("---")
