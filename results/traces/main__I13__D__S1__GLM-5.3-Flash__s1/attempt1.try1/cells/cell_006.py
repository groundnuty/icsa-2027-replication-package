import inspect
import onedatafilerestclient.onedata_file_rest_client as m
src = inspect.getsource(m.OnedataFileRESTClient.list_children)
print(src[:3000])
