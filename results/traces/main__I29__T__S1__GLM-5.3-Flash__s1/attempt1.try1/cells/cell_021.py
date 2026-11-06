import os
# persistence check
print('persist_test exists:', os.path.exists('persist_test.txt'))
if os.path.exists('persist_test.txt'):
    print(open('persist_test.txt').read())
