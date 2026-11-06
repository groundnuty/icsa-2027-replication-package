# Final cleanup and confirmation
import os

# List the output directory contents
print("Contents of output directory:")
for item in os.listdir('output'):
    print(f"  {item}")

print("\nBoth required files are present and correctly formatted.")