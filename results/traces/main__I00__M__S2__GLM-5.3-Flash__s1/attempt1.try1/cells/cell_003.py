import numpy as np, sys, os, psutil, pickle
print("numpy", np.__version__, "| python", sys.version.split()[0])
print("has method='hazen':", np.lib.NumpyVersion(np.__version__) >= "1.22.0")
try:
    import psutil
    vm = psutil.virtual_memory()
    print(f"RAM: total {vm.total/1e9:.1f} GB, avail {vm.available/1e9:.1f} GB")
except Exception as e:
    print("psutil n/a:", e)
print("cwd:", os.getcwd())
os.makedirs("output", exist_ok=True)
os.makedirs("/tmp/mhw_work", exist_ok=True)
with open("/tmp/mhw_work/persist_test.txt", "w") as f:
    f.write("ok")
print("wrote persistence test file")
