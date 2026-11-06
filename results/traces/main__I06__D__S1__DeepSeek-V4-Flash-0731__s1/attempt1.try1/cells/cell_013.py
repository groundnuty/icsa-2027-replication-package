
import os
# Check available disk space
stat = os.statvfs('/work')
print(f"Available: {stat.f_bavail * stat.f_frsize / 1e9:.1f} GB")
print(f"Block size: {stat.f_frsize}")
print(f"Total blocks: {stat.f_blocks}")
print(f"Free blocks: {stat.f_bfree}")
print(f"Avail blocks: {stat.f_bavail}")
