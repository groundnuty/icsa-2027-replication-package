
import os
# Check what files are in /work
for f in os.listdir('/work'):
    path = os.path.join('/work', f)
    size = os.path.getsize(path)
    print(f"{f}: {size/1e9:.2f} GB")
