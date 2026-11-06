
import os
os.makedirs('intermediate', exist_ok=True)
os.makedirs('output', exist_ok=True)

# Check if we have any intermediate results saved already
for f in os.listdir('intermediate'):
    print(f, os.path.getsize(f'intermediate/{f}'))
