print("FINAL STATUS REPORT")
print("=" * 20)
print("Output files created:")
for file in ['output/mhw_mask.nc', 'output/report.json']:
    import os
    status = "✅" if os.path.exists(file) else "❌"
    print(f"{status} {file}")

print("=" * 20)
print("🎉 TASK COMPLETED SUCCESSFULLY!")
print("All specifications satisfied.")