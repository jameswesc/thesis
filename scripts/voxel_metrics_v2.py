import numpy as np
import xarray as xr
from pandas import DataFrame
from xarray import Dataset
from xarray.groupers import BinGrouper


def create_voxel_dataset(points: DataFrame, voxel_size=(1.0, 1.0, 1.0), k=1):
    x_min, x_max = (points.X.min(), points.X.max())
    y_min, y_max = (points.Y.min(), points.Y.max())
    z_min, z_max = (points.Z.min(), points.Z.max())

    dx, dy, dz = voxel_size

    # Minus one more voxel unit from x and y edges so we don't need to include
    # lowest. Each cell is (low_edge, high_edge] . Likely lowest bin for x
    # and y will always be empty. That's ok.
    x_edges = np.arange(np.floor(x_min / dx) * dx, x_max + dx, dx)
    y_edges = np.arange(np.floor(y_min / dy) * dy, y_max + dy, dy)
    z_edges = np.arange(np.floor(z_min / dz) * dz, z_max + dz, dz)

    x_coords = (x_edges[:-1] + x_edges[1:]) / 2
    y_coords = (y_edges[:-1] + y_edges[1:]) / 2
    z_coords = (z_edges[:-1] + z_edges[1:]) / 2

    points_ds = xr.Dataset.from_dataframe(points.reset_index())

    voxel_group = points_ds.groupby(
        X=BinGrouper(
            bins=x_edges,
            labels=x_coords,
        ),
        Y=BinGrouper(
            bins=y_edges,
            labels=y_coords,
        ),
        Z=BinGrouper(bins=z_edges, labels=z_coords, include_lowest=True),
    )

    voxels = voxel_group.map(
        lambda ds: xr.Dataset(
            {
                "all_count": ds["index"].count(),
                "fr_count": (ds["ReturnNumber"] == 1).sum(),
            }
        )
    )

    voxels = voxels.rename({"X_bins": "x", "Y_bins": "y", "Z_bins": "z"})

    # Calculate LAD for each voxel
    voxels_in = voxels.cumsum(dim="z")
    voxels_out = voxels_in.shift(z=1)

    # Calculate LAD with proper error handling
    with np.errstate(divide="ignore", invalid="ignore"):
        # LAD for all points
        lad_all = (
            xr.ufuncs.log(voxels_in["all_count"] / voxels_out["all_count"])
            * (1 / dz)
            * (1 / k)
        )
        # LAD for first returns
        lad_fr = (
            xr.ufuncs.log(voxels_in["fr_count"] / voxels_out["fr_count"])
            * (1 / dz)
            * (1 / k)
        )

    # use np.isfinite to remove infinities that occur when there
    # are 0 points in
    voxels["lad_all_count"] = lad_all.where(np.isfinite(lad_all))
    voxels["lad_fr_count"] = lad_fr.where(np.isfinite(lad_fr))

    # Calculate LAI by summing LAD across z dimension
    # min_count = 1 so columns with all na stay na and not 0
    voxels["lai_all_count"] = voxels["lad_all_count"].sum(dim="z", min_count=1)
    voxels["lai_fr_count"] = voxels["lad_fr_count"].sum(dim="z", min_count=1)

    # Calculate proportional LAD (PLAD) - LAD normalized by LAI
    with np.errstate(divide="ignore", invalid="ignore"):
        voxels["plad_all_count"] = voxels["lad_all_count"] / voxels["lai_all_count"]
        voxels["plad_fr_count"] = voxels["lad_fr_count"] / voxels["lai_fr_count"]

    # Replace inf/nan with NaN for cleaner data
    voxels["plad_all_count"] = voxels["plad_all_count"].where(
        np.isfinite(voxels["plad_all_count"])
    )
    voxels["plad_fr_count"] = voxels["plad_fr_count"].where(
        np.isfinite(voxels["plad_fr_count"])
    )

    voxels.attrs["crs"] = "EPSG:7855"

    return voxels


voxel_metrics_metadata = {}


# Takes as input the voxels
# Reduces that to a summary metric
def calculate_voxel_metrics(voxels: Dataset):
    return {
        # "n_all": voxels["all_count"].count().item(),
        # "points": voxels["all_count"].sum().item(),
        # "mean_count": voxels["all_count"].mean().item(),
        # "max_count": voxels["all_count"].max().item(),
        # "mean_fr_count": voxels["fr_count"].mean().item(),
        # "max_fr_count": voxels["fr_count"].max().item(),
        # ALL LAI
        "mean_lai_all": voxels["lai_all_count"].mean().item(),
        "max_lai_all": voxels["lai_all_count"].max().item(),
        "sd_lai_all": voxels["lai_all_count"].std().item(),
        # FR LAI
        "mean_lai_fr": voxels["lai_fr_count"].mean().item(),
        "max_lai_fr": voxels["lai_fr_count"].max().item(),
        "sd_lai_fr": voxels["lai_fr_count"].std().item(),
    }
