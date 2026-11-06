import numpy as np, inspect
# find the module defining _quantile_hazen or the methods dict
import numpy
for name in ['_methods', '_quantile_hazen']:
    pass
# search by looking at np.quantile's module
print(np.quantile.__module__)
q = np.lib._npy_include_impl if False else None
import numpy.core as core
# just grep site-packages
import subprocess, glob, os
root = os.path.dirname(np.__file__)
print(root)
hits = subprocess.run(['grep','-rl','def _quantile_hazen',root], capture_output=True, text=True).stdout
print("grep hits:", hits)
