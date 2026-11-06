import os
import xarray as xr
import numpy as np
import pandas as pd
import json

# Dataset path
dataset_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
files = os.listdir(dataset_dir)
print("Files in dataset directory:", files)
