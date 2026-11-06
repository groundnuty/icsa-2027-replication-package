
import fsspec
fs = fsspec.filesystem('onedata')
client = fs.client
space = 'icsa2027_data_20261101T090944Z'

# List all children with pagination
result = client.list_children(space, file_path='s1z', limit=1000, attributes=["name", "type"])
children = result["children"]
print("First batch:", len(children))
print("Children names first 5:", [c["name"] for c in children[:5]])
print("Children names last 5:", [c["name"] for c in children[-5:]])
print("Next token:", result.get("nextPageToken"))

# Follow pagination
token = result.get("nextPageToken")
batch_count = 1
all_names = [c["name"] for c in children]
while token:
    result = client.list_children(space, file_path='s1z', limit=1000, attributes=["name", "type"], continuation_token=token)
    children = result["children"]
    batch_count += 1
    all_names.extend([c["name"] for c in children])
    print(f"Batch {batch_count}: {len(children)} children, token={result.get('nextPageToken')}")
    token = result.get("nextPageToken")
    if batch_count > 10:
        print("Too many batches, stopping")
        break

print(f"\nTotal files: {len(all_names)}")
print(f"First 5: {all_names[:5]}")
print(f"Last 5: {all_names[-5:]}")
