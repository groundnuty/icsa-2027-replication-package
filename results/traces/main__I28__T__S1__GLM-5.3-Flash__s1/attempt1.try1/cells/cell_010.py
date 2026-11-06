try:
    print(persist_test)
except Exception as e:
    print("not persisted:", e)
import time, fsspec
print("time module available:", 'time' in dir())
