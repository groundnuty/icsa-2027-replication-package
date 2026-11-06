
import os
stat = os.statvfs('/work')
print(f"Available: {stat.f_bavail * stat.f_frsize / 1e9:.2f} GB")
print(f"Total: {stat.f_blocks * stat.f_frsize / 1e9:.2f} GB")
print(f"Used: {(stat.f_blocks - stat.f_bfree) * stat.f_frsize / 1e9:.2f} GB")

# Check s2 file size more precisely
print(f"\ns2 size: {os.path.getsize('/work/sst_s2.nc')/1e9:.2f} GB")
print(f"s1z size: {os.path.getsize('/work/sst_19820101.nc')/1e9:.2f} GB")
