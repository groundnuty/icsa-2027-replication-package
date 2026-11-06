
# Test if sandbox files persist between calls
with open('/tmp/test.txt', 'w') as f:
    f.write('hello')
print("Wrote test file")
