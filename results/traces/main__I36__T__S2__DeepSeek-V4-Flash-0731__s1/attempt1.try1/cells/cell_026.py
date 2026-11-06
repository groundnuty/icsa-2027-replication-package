
import os

print("Files in output/:")
for f in os.listdir('output'):
    path = os.path.join('output', f)
    size = os.path.getsize(path)
    print(f"  {f}: {size} bytes")
