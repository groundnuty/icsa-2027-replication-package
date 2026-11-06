
import os, fsspec, datetime, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# free space: remove raw files
n=0
for f in os.listdir('/work/mhw'):
    os.remove(f'/work/mhw/{f}'); n+=1
os.rmdir('/work/mhw')
print("removed", n, "raw files")
u = __import__('shutil').disk_usage('/work')
print("work free now: %.2fG" % (u.free/1e9))
