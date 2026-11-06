
import os
for f in sorted(os.listdir('intermediate')):
    size = os.path.getsize(f'intermediate/{f}')
    print(f"{f}: {size/1e6:.2f} MB")
