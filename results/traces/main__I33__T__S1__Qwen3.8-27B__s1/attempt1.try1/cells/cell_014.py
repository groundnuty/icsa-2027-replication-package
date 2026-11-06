
import shutil, os
u = shutil.disk_usage('/work')
print("work total=%.1fG free=%.1fG inodes free=%d" % (u.total/1e9, u.free/1e9, u.free))
print("files:", len([f for f in os.listdir('/work/mhw')]))
# test writing a 100MB file
try:
    with open('/work/test100m','wb') as fh:
        fh.seek(100*1024*1024); fh.write(b'\0')
    print("100MB write ok")
    os.remove('/work/test100m')
except Exception as e:
    print("write fail:", e)
