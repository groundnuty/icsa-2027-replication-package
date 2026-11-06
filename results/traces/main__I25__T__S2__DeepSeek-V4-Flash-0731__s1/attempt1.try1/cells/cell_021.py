
import numpy as np
import pickle
import os

# Create a comprehensive script that saves intermediate results

# First, let me check memory availability
import resource
print(f"Memory limit: {resource.getrlimit(resource.RLIMIT_AS)}")

import psutil
print(f"Available memory: {psutil.virtual_memory().available / 1e9:.2f} GB")
