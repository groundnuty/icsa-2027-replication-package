import os
print("cwd:", os.getcwd())
print("writable cwd:", os.access(os.getcwd(), os.W_OK))
os.makedirs("output", exist_ok=True)
print("created:", os.path.abspath("output"))
