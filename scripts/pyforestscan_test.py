# %%
from pyforestscan.filters import filter_hag
from pyforestscan.handlers import read_lidar

file_path = "../data/plots/lidar/AGG_O_01_P1.copc.laz"
arrays = read_lidar(file_path, "EPSG:7855", hag=False)
arrays = filter_hag(arrays)
points = arrays[0]
# %%
points.dtype

# %%
p1 = points[1]

# %%
p1.dtype
