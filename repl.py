# %%
from time import time

import geopandas as gpd
import numpy as np
import pandas as pd
import pdal
import xarray as xr

# %% Dummy to stuff ruff removing
np  # pyright: ignore
pd  # pyright: ignore
xr  # pyright: ignore
pdal  # pyright: ignore
gpd  # pyright: ignore

# %%
site_plot_id = "NRO_138_P2"
start = time()
pl = (
    pdal.Reader(f"data/plots/lidar/{site_plot_id}.copc.laz")
    | pdal.Filter("filters.sort", dimension="HeightAboveGround", order="DESC")
    | pdal.Filter("filters.litree", min_points=20, min_height=0.5, radius=100)
    | pdal.Writer(
        f"data/plots/lidar_litree/{site_plot_id}.copc.laz",
        type="writers.copc",
        extra_dims="all",
    )
)
pl.execute()
end = time()
print(f"Time taken: {end - start:,} seconds")
# %%
points = pd.DataFrame(pl.arrays[0])
# %%
points["ClusterID"]
