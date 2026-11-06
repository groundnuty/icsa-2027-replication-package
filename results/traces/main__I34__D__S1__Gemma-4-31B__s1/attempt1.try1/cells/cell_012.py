import shutil
total, used, free = shutil.disk_usage("/work")
print(f"Total: {total / 1e9:.2f} GB")
print(f"Used: {used / 1e9:.2f} GB")
print(f"Free: {free / 1e9:.2f} GB")
