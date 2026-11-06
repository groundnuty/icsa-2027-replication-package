
import shutil, os
shutil.rmtree('/tmp/mhw_files', ignore_errors=True)
print(shutil.disk_usage('/tmp'))
print(shutil.disk_usage('/'))
