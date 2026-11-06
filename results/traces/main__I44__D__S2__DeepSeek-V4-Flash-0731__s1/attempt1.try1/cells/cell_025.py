
import os
print("Current working directory:", os.getcwd())
print("\nFiles in cwd:")
for root, dirs, files in os.walk('.'):
    for f in files:
        path = os.path.join(root, f)
        print(f"  {path}")
    for d in dirs:
        path = os.path.join(root, d)
        print(f"  {path}/")
