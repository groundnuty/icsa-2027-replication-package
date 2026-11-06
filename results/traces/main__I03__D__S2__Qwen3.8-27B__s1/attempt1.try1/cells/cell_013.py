import numpy, os, subprocess
p = os.path.dirname(numpy.__file__)
print(p)
# search for hazen in any .c/.pyx/.py files
import glob
hits = subprocess.run(['grep','-rIl','hazen', p], capture_output=True, text=True).stdout
print(hits)
