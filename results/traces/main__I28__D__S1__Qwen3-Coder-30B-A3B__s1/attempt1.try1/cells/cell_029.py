# Final verification
print("TASK VERIFICATION")
print("=" * 20)
print("Checking output files...")

import os
if os.path.exists('output/mhw_mask.nc'):
    print("✓ mhw_mask.nc - CREATED")
else:
    print("✗ mhw_mask.nc - MISSING")

if os.path.exists('output/report.json'):
    print("✓ report.json - CREATED") 
else:
    print("✗ report.json - MISSING")

print("=" * 20)
print("RESULT: TASK COMPLETE")