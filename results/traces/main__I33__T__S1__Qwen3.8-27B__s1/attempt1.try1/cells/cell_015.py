
import shutil, os
for p in ['/trace', '/dev/shm', '/media', '/run']:
    try:
        u = shutil.disk_usage(p)
        print(p, "total=%.2fG free=%.2fG" % (u.total/1e9, u.free/1e9))
        try:
            os.makedirs(p+'/wt', exist_ok=True); print("  writable")
            os.rmdir(p+'/wt')
        except Exception as e:
            print("  not writable:", type(e).__name__)
    except Exception as e:
        print(p, "err", e)
