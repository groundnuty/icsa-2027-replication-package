# Final cleanup and confirmation
import os
import shutil

# Show final file status
print("Final output files:")
for root, dirs, files in os.walk('output'):
    for file in files:
        filepath = os.path.join(root, file)
        size = os.path.getsize(filepath)
        print(f"  {filepath}: {size} bytes")

print("\nTask completed successfully!")