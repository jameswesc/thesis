# %%
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
pl = pdal.Reader("data/plots/lidar/AGG_O_07_P5.copc.laz").pipeline()
pl.execute()
# %%
points = pd.DataFrame(pl.arrays[0])
points.head()

# %%
points["W"] = points["ReturnNumber"] / points["NumberOfReturns"]


# %%
def p_gap(points, z):
    return (
        1
        - (
            points[points["HeightAboveGround"] > z]["W"].sum() / points["W"].sum()
        ).item()
    )
