import os
print(os.listdir("/tmp"))
for f in os.listdir("/tmp"):
    p = os.path.join("/tmp", f)
    print(p, os.path.getsize(p))
