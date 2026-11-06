import numpy, os
base = os.path.dirname(numpy.__file__)
print(base)
import subprocess
out = subprocess.run(["grep","-rn","hazen", base, "--include=*.py"], capture_output=True, text=True)
print(out.stdout[:3000])
