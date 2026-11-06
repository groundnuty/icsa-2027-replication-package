import os
p="/tmp/persist_test.txt"
print("content:", open(p).read() if os.path.exists(p) else "GONE")
print("cwd:", os.getcwd(), os.listdir(".")[:10])
import numpy, sys
print("numpy", numpy.__version__, sys.version)
