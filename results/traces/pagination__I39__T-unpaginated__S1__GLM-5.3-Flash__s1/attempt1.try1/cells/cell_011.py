import os
print('/tmp marker exists:', os.path.exists('/tmp/mhwtest/marker.txt'))
if os.path.exists('/tmp/mhwtest/marker.txt'):
    print(open('/tmp/mhwtest/marker.txt').read())
print('cwd marker exists:', os.path.exists('output/persist_marker.txt'))
if os.path.exists('output/persist_marker.txt'):
    print(open('output/persist_marker.txt').read())
# and cleanup marker
if os.path.exists('output/persist_marker.txt'):
    os.remove('output/persist_marker.txt')
    print('cleaned')
