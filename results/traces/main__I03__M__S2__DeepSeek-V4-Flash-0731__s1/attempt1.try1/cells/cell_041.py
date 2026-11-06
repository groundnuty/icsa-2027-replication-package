
import os
print("Output directory contents:")
for f in os.listdir('output'):
    full_path = os.path.join('output', f)
    print(f"  {f}: {os.path.getsize(full_path)} bytes")
