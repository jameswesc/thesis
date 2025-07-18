# %%
import numpy as np
import pandas as pd
import pdal
import xarray as xr
from xarray.groupers import BinGrouper

# %% Dummy to stuff ruff removing
np  # pyright: ignore
pd  # pyright: ignore
xr  # pyright: ignore
pdal  # pyright: ignore

# print(points_ds.to_pandas().head())

# pixel_group = points_ds.groupby(
#     X=BinGrouper(
#         bins=x_edges,
#         labels=x_coords,
#     ),
#     Y=BinGrouper(
#         bins=y_edges,
#         labels=y_coords,
#     ),
# )

# voxel_group = points_ds.groupby(
#     X=BinGrouper(bins=x_edges, labels=x_coords, include_lowest=False),
#     Y=BinGrouper(bins=y_edges, labels=y_coords, include_lowest=False),
#     Z=BinGrouper(bins=z_edges, labels=z_coords, include_lowest=True),
# )

# z_group = points_ds.groupby(
#     Z=BinGrouper(bins=z_edges, labels=z_coords, include_lowest=True),
# )


# # %%
# pl = (
#     pdal.Reader("data/sites/lidar/AGG_O_01.copc.laz", type="readers.copc")
#     | pdal.Filter(type="filters.range", limits="HeightAboveGround[0:]")
#     | pdal.Filter(type="filters.ferry", dimensions="HeightAboveGround => Z")
# )

# count = pl.execute()
# print(f"Successfully read {count} points")
# # %%
# columns = pd.Series(["X", "Y", "Z", "ReturnNumber", "NumberOfReturns"])
# points = pd.DataFrame(
#     pl.arrays[0],
#     columns=columns,
# )
# points["Weight"] = 1 / points["NumberOfReturns"]
# points.head()

# # %% Voxel Resolution
# dx, dy, dz = (1.0, 1.0, 1.0)


# # %%
# x_min, x_max = (points.X.min(), points.X.max())
# y_min, y_max = (points.Y.min(), points.Y.max())
# z_min, z_max = (points.Z.min(), points.Z.max())


# # %%
# x_bins = np.arange(np.floor(x_min / dx) * dx, x_max + dx, dx)
# y_bins = np.arange(np.floor(y_min / dy) * dy, y_max + dy, dy)
# z_bins = np.arange(np.floor(z_min / dz) * dz, z_max + dz, dz)

# # %%
# all_xyz = np.column_stack((points.X, points.Y, points.Z))
# all_hist, _ = np.histogramdd(all_xyz, bins=(x_bins, y_bins, z_bins))
# all_hist = all_hist.astype(np.uint16)

# # %%
# first_returns = points[points.ReturnNumber == 1]
# first_returns_xyz = np.column_stack((first_returns.X, first_returns.Y, first_returns.Z))
# first_returns_hist, _ = np.histogramdd(first_returns_xyz, bins=(x_bins, y_bins, z_bins))
# first_returns_hist = first_returns_hist.astype(np.uint16)

# # first_returns = points[points.ReturnNumber == 1]
# # first_returns_xyz = np.column_stack((first_returns.X, first_returns.Y, first_returns.Z))

# # %%
# # Center reference coordinates
# # i.e. coordinates are the center point of a voxel
# x_coords = ((x_bins[:-1] + x_bins[1:]) / 2).astype(np.float32)
# y_coords = ((y_bins[:-1] + y_bins[1:]) / 2).astype(np.float32)
# z_coords = ((z_bins[:-1] + z_bins[1:]) / 2).astype(np.float32)


# # %%
# voxels = xr.DataArray(
#     all_hist, dims=("x", "y", "z"), coords=(x_coords, y_coords, z_coords)
# )
# voxels.attrs["long_name"] = "Returns per voxel"
# voxels.attrs["units"] = "Returns"

# voxels.x.attrs["long_name"] = "Easting"
# voxels.x.attrs["units"] = "metres"

# voxels.y.attrs["long_name"] = "Northing"
# voxels.y.attrs["units"] = "metres"

# # %%


# # %%
# fr_voxels = xr.DataArray(
#     first_returns_hist,
#     dims=("x", "y", "z"),
#     coords=(x_coords, y_coords, z_coords),
# )
# fr_voxels.attrs["long_name"] = "First returns per voxel"
# fr_voxels.attrs["units"] = "Returns"

# fr_voxels.x.attrs["long_name"] = "Easting"
# fr_voxels.x.attrs["units"] = "metres"

# fr_voxels.y.attrs["long_name"] = "Northing"
# fr_voxels.y.attrs["units"] = "metres"
# # %%
# voxels_in = voxels.cumsum(dim="z")
# voxels_out = voxels_in.shift(z=1)

# # Use numpy's errstate context manager with xarray
# with np.errstate(divide="ignore", invalid="ignore"):
#     lad_all = xr.ufuncs.log(voxels_in / voxels_out) * (1 / dz)
#     lad_all = lad_all.where(np.isfinite(lad_all))  # This sets non-finite values to NaN


# # %%
# fr_in = fr_voxels.cumsum(dim="z")
# fr_out = fr_in.shift(z=1)
# with np.errstate(divide="ignore", invalid="ignore"):
#     lad_fr = xr.ufuncs.log(fr_in / fr_out) * (1 / dz)
#     lad_fr = lad_fr.where(np.isfinite(lad_fr))

# # %%
# ds = xr.Dataset(
#     {
#         "all_returns": voxels,
#         "first_returns": fr_voxels,
#         "lad_all": lad_all,
#         "lad_fr": lad_fr,
#     }
# )
# ds
# # %%
# ds.to_zarr("data/sites/voxels/AGG_O_01.zarr", zarr_format=2, mode="w")
# ds.to_netcdf("data/sites/voxels/AGG_O_01.nc")
# # %%
# lad_fr = ds.lad_fr

# # %%
# figure(figsize=(12, 6), dpi=120)
# lad_fr.sum(dim="z").T.plot().axes.set_aspect("equal")

# # %%
# figure(figsize=(12, 6), dpi=120)
# lad_fr.sum(dim="z").T.plot().axes.set_aspect("equal")

# # %%
# figure(figsize=(12, 6), dpi=120)
# ds.lad_all.sum(dim="z").T.plot().axes.set_aspect("equal")


# %%
pl = (
    pdal.Reader("data/sites/lidar/AGG_O_01.copc.laz", type="readers.copc")
    | pdal.Filter(type="filters.range", limits="HeightAboveGround[0:]")
    | pdal.Filter(type="filters.ferry", dimensions="HeightAboveGround => Z")
)

count = pl.execute()
print(f"Successfully read {count} points")
# %%
columns = pd.Series(["X", "Y", "Z", "ReturnNumber", "NumberOfReturns"])
points = pd.DataFrame(
    pl.arrays[0],
    columns=columns,
)
points["Weight"] = 1 / points["NumberOfReturns"]
points.head()

# %% Define voxel resolution and bins
dx, dy, dz = (1, 1, 1)

x_min, x_max = (points.X.min(), points.X.max())
y_min, y_max = (points.Y.min(), points.Y.max())
z_min, z_max = (points.Z.min(), points.Z.max())

x_bins = np.arange(np.floor(x_min / dx) * dx, x_max + dx, dx)
y_bins = np.arange(np.floor(y_min / dy) * dy, y_max + dy, dy)
z_bins = np.arange(np.floor(z_min / dz) * dz, z_max + dz, dz)

x_coords = (x_bins[:-1] + x_bins[1:]) / 2
y_coords = (y_bins[:-1] + y_bins[1:]) / 2
z_coords = (z_bins[:-1] + z_bins[1:]) / 2
# %%
# Convert to xarray Dataset
points_ds = xr.Dataset.from_dataframe(points.reset_index())
points_ds

# %%
# Each group has the indices of all points in that voxel
voxel_group = points_ds.groupby(
    X=BinGrouper(bins=x_bins, right=False, labels=x_coords),
    Y=BinGrouper(bins=y_bins, right=False, labels=y_coords),
    Z=BinGrouper(bins=z_bins, right=False, labels=z_coords),
)

# %%
# THIS IS A FAIR BIT SLOWER BUT GIVES YOU ACCESS TO ALL THE DATA
# SIMILAR TO WHAT I IMAGINE YOU GET FOR voxel_metrics in lidR
voxels = voxel_group.map(
    lambda ds: xr.Dataset(
        {
            "all_count": ds["index"].count(),
            "first_returns_count": (ds["ReturnNumber"] == 1).sum(),
            "weighted_count": ds["Weight"].sum(),
        }
    )
)


# %%
voxels = voxels.rename({"X_bins": "x", "Y_bins": "y", "Z_bins": "z"})
voxels
# %%
voxels.weighted_count.sel(z=1.5).T.plot()


# %%
# A pixel group is the same but just on x, y
pixel_group = points_ds.groupby(
    x=BinGrouper(bins=x_bins),
    y=BinGrouper(bins=y_bins),
)

# %%
pixel_group.max().z.T.plot()


# %%
list(voxel_group)
# %%
og_ds = xr.open_dataset("data/sites/voxels/AGG_O_01.nc")
og_ds
