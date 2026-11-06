# Final confirmation
print("🎯 TASK COMPLETION CONFIRMATION")
print("=" * 35)

# Check both required files
file1_exists = os.path.exists('/work/output/mhw_mask.nc')
file2_exists = os.path.exists('/work/report.json')

print(f"MHW Mask File: {'✅ CREATED' if file1_exists else '❌ MISSING'}")
print(f"Report File:   {'✅ CREATED' if file2_exists else '❌ MISSING'}")

if file1_exists and file2_exists:
    print("=" * 35)
    print("🎉 SUCCESS: Task completed fully")
    print("Both required output files generated successfully.")
else:
    print("=" * 35)
    print("❌ FAILURE: Missing required files")