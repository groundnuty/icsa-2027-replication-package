
# test persistence across calls
with open("/tmp/persist_test.txt", "w") as f:
    f.write("hello")
print("written")
