import os, shutil
# check disk usage
for p in ['/work', '/tmp']:
    try:
        st = shutil.disk_usage(p)
        print(p, "total %.1fG used %.1fG free %.1fG" % (st.total/2**30, st.used/2**30, st.free/2**30))
    except Exception as e:
        print(p, e)
# remove the big memmaps
for fn in ['/work/me/sst_target.npy', '/work/me/sst_base.npy']:
    if os.path.exists(fn):
        os.remove(fn)
        print("removed", fn)
print(os.listdir('/work/me'))
