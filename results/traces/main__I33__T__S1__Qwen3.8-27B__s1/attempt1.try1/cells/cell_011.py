
import os
for p in ['/var/tmp', '~', '~', '/opt', '/srv', '/mnt', '~']:
    try:
        os.makedirs(p+'/wtest_x', exist_ok=True)
        print(p, "writable")
        os.rmdir(p+'/wtest_x')
    except Exception as e:
        print(p, "no:", type(e).__name__)
