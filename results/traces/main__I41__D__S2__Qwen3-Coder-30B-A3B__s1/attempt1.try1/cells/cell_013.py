# Final cleanup and confirmation
import os

# List final output files
print("Final output files:")
for file in os.listdir('output'):
    print(f"  {file}")

print("\nTask completed successfully!")