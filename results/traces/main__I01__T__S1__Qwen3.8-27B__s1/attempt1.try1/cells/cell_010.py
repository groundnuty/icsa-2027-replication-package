
import os
print("cwd:", os.getcwd())
for d in [os.getcwd(), '/tmp', '~', '/var/tmp']:
    try:
        os.makedirs(d + '/mhwtest', exist_ok=True)
        print("writable:", d)
        os.rmdir(d + '/mhwtest')
    except Exception as e:
        print("not writable:", d, e)
