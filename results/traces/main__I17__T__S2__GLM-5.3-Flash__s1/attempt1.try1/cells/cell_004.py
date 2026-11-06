import os
print("hello, mem ok")
with open('/proc/meminfo') as fh:
    print(fh.read(200))
