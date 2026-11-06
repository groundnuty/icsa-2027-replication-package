import os, shutil
print("cwd:", os.getcwd())
print(os.listdir("."))
for p in ["/tmp", ".", "/data"]:
    try:
        s = shutil.disk_usage(p)
        print(p, f"total={s.total/1e9:.1f}GB free={s.free/1e9:.1f}GB")
    except Exception as e:
        print(p, "err", e)
os.makedirs("/tmp/mhw", exist_ok=True)
os.makedirs("output", exist_ok=True)
print("dirs ok")
