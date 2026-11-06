
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

with fs.open(f'{base}/sst_20040601.nc', 'rb') as fh:
    ds = xr.open_dataset(fh, engine='h5netcdf')
    lat = ds['latitude'].values
    lon = ds['longitude'].values
    
    # Region bounds: lat 57.41-58.61, lon 18.69-19.89
    lat_mask = (lat >= 57.41) & (lat <= 58.61)
    lon_mask = (lon >= 18.69) & (lon <= 19.89)
    
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]
    
    print(f'Latitude range in region: {lat[lat_idx[0]]} to {lat[lat_idx[-1]]}')
    print(f'Longitude range in region: {lon[lon_idx[0]]} to {lon[lon_idx[-1]]}')
    print(f'Number of lat cells: {len(lat_idx)}')
    print(f'Number of lon cells: {len(lon_idx)}')
    
    # Check SST values at a few cells
    sst = ds['analysed_sst'].values
    print(f'SST shape: {sst.shape}')
    print(f'SST sample (first lat/lon in region): {sst[0, lat_idx[0], lon_idx[0]]}')
    print(f'SST sample (last): {sst[0, lat_idx[-1], lon_idx[-1]]}')
    
    # Check NaN
    print(f'NaN count in region: {np.isnan(sst[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]).sum()}')
    
    # Check units
    print(ds['analysed_sst'].attrs)
