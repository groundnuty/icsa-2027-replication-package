
import os
print(os.listdir('output'))
print("File sizes:")
for f in os.listdir('output'):
    print(f"  {f}: {os.path.getsize(os.path.join('output', f))} bytes")
