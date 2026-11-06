import shutil, os
print(shutil.disk_usage('/work') if os.path.isdir('/work') else shutil.disk_usage('/'))
print(os.listdir('/work') if os.path.isdir('/work') else 'no /work')
