
import shutil
for p in ['/tmp', '/', '/var/tmp', '~', '~', '/data', '/workspace']:
    try:
        u = shutil.disk_usage(p)
        print(p, "total=%.1fG free=%.1fG" % (u.total/1e9, u.free/1e9))
    except Exception as e:
        print(p, "err", e)
import os
print("tmp files:", len([f for f in os.listdir('/tmp/mhw') if os.path.getsize(f'/tmp/mhw/{f}')>1000]))
