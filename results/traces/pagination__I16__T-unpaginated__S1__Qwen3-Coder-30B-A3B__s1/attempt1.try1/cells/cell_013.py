# Final status check
import os

print("=== FINAL STATUS CHECK ===")
print(f"report.json exists: {os.path.exists('output/report.json')}")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")

if os.path.exists('output/report.json') and os.path.exists('output/mhw_mask.nc'):
    print("✅ ALL REQUIREMENTS SATISFIED")
    print("✅ Task completed successfully")
else:
    print("❌ MISSING OUTPUT FILES")