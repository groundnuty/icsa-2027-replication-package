
import numpy as np
import os

# Check memory
print("Checking memory...")
try:
    import psutil
    print(f"Available memory: {psutil.virtual_memory().available / 1e9:.2f} GB")
except:
    print("psutil not available")

# Check disk space
print(f"Disk space in current dir: {os.statvfs('.').f_bavail * os.statvfs('.').f_frsize / 1e9:.2f} GB")
print(f"Current dir: {os.getcwd()}")
