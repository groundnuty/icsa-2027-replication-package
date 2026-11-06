# Final verification that both required files were created
import os

files_created = []
if os.path.exists('output/report.json'):
    files_created.append('output/report.json')
if os.path.exists('output/mhw_mask.nc'):
    files_created.append('output/mhw_mask.nc')

print(f"Successfully created {len(files_created)} out of 2 required files:")
for f in files_created:
    print(f"  - {f}")

if len(files_created) == 2:
    print("\n✅ Task completed successfully!")
else:
    print(f"\n⚠️  Missing {2-len(files_created)} file(s)")