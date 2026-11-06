
import os
print(f"Current working directory: {os.getcwd()}")
print(f"Output dir: {os.path.abspath('output')}")
print(f"Files in output: {os.listdir('output')}")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"report.json exists: {os.path.exists('output/report.json')}")
