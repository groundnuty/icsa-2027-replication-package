import os, shutil
print("cwd:", os.getcwd())
print("HOME:", os.environ.get('HOME'))
print("free cwd:", shutil.disk_usage(os.getcwd()).free/1e9, "GB")
for d in ['.']:
    try:
        open(os.path.join(d, '.wtest'), 'w').close()
        print("writable:", d)
    except Exception as e:
        print("not writable:", d, e)
