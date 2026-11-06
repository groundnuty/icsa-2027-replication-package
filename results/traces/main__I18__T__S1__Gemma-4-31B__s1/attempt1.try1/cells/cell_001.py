import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(base_dir)
print(files)
