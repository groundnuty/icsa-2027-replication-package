import numpy as np, sys, os
print("numpy", np.__version__, "| python", sys.version.split()[0])
a = np.percentile(np.array([1,2,3,4,5],dtype=float), 90, method="hazen")
print("hazen works:", a)
import os
print("cwd:", os.getcwd())
os.makedirs("output", exist_ok=True)
os.makedirs("/tmp/mhw_work", exist_ok=True)
with open("/tmp/mhw_work/persist_test.txt", "w") as f:
    f.write("ok")
with open("output/persist_test.txt", "w") as f:
    f.write("ok")
print("wrote persistence test files")
import os as _o
print("/tmp listing:", _o.listdir("/tmp/mhw_work"))
print("output listing:", _o.listdir("output"))
