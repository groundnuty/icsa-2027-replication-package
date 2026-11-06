
import fsspec
fs = fsspec.filesystem('onedata')
client = fs.client
space = 'icsa2027_data_20261101T090944Z'

# Continue from where we left off
all_names = []
result = client.list_children(space, file_path='s1z', limit=1000, attributes=["name", "type"])
token = result.get("nextPageToken")
batch_count = 0
while token and batch_count < 30:
    result = client.list_children(space, file_path='s1z', limit=1000, attributes=["name", "type"], continuation_token=token)
    children = result["children"]
    batch_count += 1
    names = [c["name"] for c in children]
    all_names.extend(names)
    print(f"Batch {batch_count}: {len(children)} children, first={names[0] if names else 'none'}, last={names[-1] if names else 'none'}")
    token = result.get("nextPageToken")
    if not token:
        print("No more tokens")
        break

print(f"\nTotal additional: {len(all_names)}")
if all_names:
    print(f"First: {all_names[0]}, Last: {all_names[-1]}")
