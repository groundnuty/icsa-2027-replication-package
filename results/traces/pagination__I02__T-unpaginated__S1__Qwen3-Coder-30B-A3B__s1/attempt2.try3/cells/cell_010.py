# Final verification that files were created
import os

# Check if output directory exists and contains the expected files
if os.path.exists('output'):
    files = os.listdir('output')
    print("Output directory contents:")
    for f in files:
        print(f"  {f}")
else:
    print("Output directory not found")