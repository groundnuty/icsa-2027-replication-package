import fsspec
import xarray as xr
import numpy as np
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Try to list what's available
try:
    root_contents = fs.ls('/')
    print("Root contents:", root_contents)
except Exception as e:
    print("Error listing root:", e)

# Let's try a more direct approach to see what we can access
print("Available spaces:")
try:
    spaces = fs.ls('/', detail=False)
    print(spaces)
except Exception as e:
    print("Error accessing spaces:", e)