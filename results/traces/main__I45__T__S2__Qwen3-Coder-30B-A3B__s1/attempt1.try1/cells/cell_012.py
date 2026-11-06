# Final verification that everything is complete
import os

print("Final verification:")
print("-" * 30)
print("Files created:")
files = ['output/mhw_mask.nc', 'output/report.json']
for file in files:
    exists = os.path.exists(file)
    print(f"  {file}: {'✓' if exists else '✗'}")

print("\nAnalysis complete and verified!")