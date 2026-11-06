
import os
for f in os.listdir('/work'):
    if f.endswith('.npy'):
        print(f, os.path.getsize(f'/work/{f}'))
