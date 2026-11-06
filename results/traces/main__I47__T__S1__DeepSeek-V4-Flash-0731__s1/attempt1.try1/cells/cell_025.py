
# Check saved files
import os
for f in ['/tmp/base_data.npy', '/tmp/tgt_data.npy', '/tmp/base_times.npy', 
          '/tmp/tgt_times.npy', '/tmp/lats.npy', '/tmp/lons.npy',
          '/tmp/threshold_smooth.npy', '/tmp/clim_smooth.npy']:
    print(f, os.path.exists(f), os.path.getsize(f) if os.path.exists(f) else '')
