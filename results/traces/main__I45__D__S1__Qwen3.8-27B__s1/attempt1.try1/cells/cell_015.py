import numpy as np, os, subprocess
root = os.path.dirname(np.__file__)
r = subprocess.run(['grep','-rn','hazen',root,'--include=*.py'], capture_output=True, text=True)
for line in r.stdout.splitlines()[:40]:
    print(line)
