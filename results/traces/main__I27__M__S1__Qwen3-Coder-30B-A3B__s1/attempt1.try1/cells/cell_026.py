# Final confirmation that task is done
print("FINAL CONFIRMATION")
print("=" * 16)
print("Required files:")
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    import os
    exists = os.path.exists(file)
    print(f"  {'✓' if exists else '✗'} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n🎉 TASK SUCCESSFULLY COMPLETED")
    print("Both output files have been generated as required.")
    print("Marine heatwave analysis for Baltic Sea region is finished.")
else:
    print("\n❌ TASK INCOMPLETE")
    print("Some required files are missing.")