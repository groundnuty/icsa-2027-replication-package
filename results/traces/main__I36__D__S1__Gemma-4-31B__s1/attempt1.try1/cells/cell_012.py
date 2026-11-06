import shutil
total, used, free = shutil.disk_usage("/")
print(f"Total: {total // (2**30)} GB, Used: {used // (2**30)} GB, Free: {free // (2**30)} GB")
