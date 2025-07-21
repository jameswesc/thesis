import warnings

import numpy as np
import xarray as xr
from pandas import DataFrame
from xarray import Dataset
from xarray.groupers import BinGrouper

# TODO SELECT METHOD AS A PARAMETERi


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

    points["Weighted"] = 1 / points["NumberOfReturns"]

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
                "all": ds["index"].count(),
                "first": (ds["ReturnNumber"] == 1).sum(),
                "last": (ds["ReturnNumber"] == ds["NumberOfReturns"]).sum(),
                "weighted": ds["Weighted"].sum(),
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
            xr.ufuncs.log(voxels_in["all"] / voxels_out["all"]) * (1 / dz) * (1 / k)
        )
        # LAD for first returns
        lad_first = (
            xr.ufuncs.log(voxels_in["first"] / voxels_out["first"]) * (1 / dz) * (1 / k)
        )
        lad_last = (
            xr.ufuncs.log(voxels_in["last"] / voxels_out["last"]) * (1 / dz) * (1 / k)
        )
        lad_weighted = (
            xr.ufuncs.log(voxels_in["weighted"] / voxels_out["weighted"])
            * (1 / dz)
            * (1 / k)
        )

    # eLAD

    # use np.isfinite to remove infinities that occur when there
    # are 0 points in
    voxels["lad_all"] = lad_all.where(np.isfinite(lad_all))
    voxels["lad_weighted"] = lad_weighted.where(np.isfinite(lad_weighted))
    voxels["lad_first"] = lad_first.where(np.isfinite(lad_first))
    voxels["lad_last"] = lad_last.where(np.isfinite(lad_last))

    # eLAI

    # Calculate LAI by summing LAD across z dimension
    # min_count = 1 so columns with all na stay na and not 0
    voxels["lai_all"] = voxels["lad_all"].sum(dim="z", min_count=1)
    voxels["lai_first"] = voxels["lad_first"].sum(dim="z", min_count=1)
    voxels["lai_last"] = voxels["lad_last"].sum(dim="z", min_count=1)
    voxels["lai_weighted"] = voxels["lad_weighted"].sum(dim="z", min_count=1)

    # PLAD

    # Calculate proportional LAD (PLAD) - LAD normalized by LAI
    with np.errstate(divide="ignore", invalid="ignore"):
        voxels["plad_all"] = voxels["lad_all"] / voxels["lai_all"]
        voxels["plad_first"] = voxels["lad_first"] / voxels["lai_first"]
        voxels["plad_last"] = voxels["lad_last"] / voxels["lai_last"]
        voxels["plad_weighted"] = voxels["lad_weighted"] / voxels["lai_weighted"]

    # Replace inf/nan with NaN for cleaner data
    voxels["plad_all"] = voxels["plad_all"].where(np.isfinite(voxels["plad_all"]))
    voxels["plad_first"] = voxels["plad_first"].where(np.isfinite(voxels["plad_first"]))
    voxels["plad_last"] = voxels["plad_last"].where(np.isfinite(voxels["plad_last"]))
    voxels["plad_weighted"] = voxels["plad_weighted"].where(
        np.isfinite(voxels["plad_weighted"])
    )

    voxels.attrs["crs"] = "EPSG:7855"

    return voxels


voxel_metrics_metadata = {
    # LAI (Leaf Area Index) metrics
    "mean_lai": {
        "title": "Mean eLAI",
        "description": "Mean effective Leaf Area Index",
        "unit": "m²/m²",
        "category": "cover",
        "metric_type": "voxel",
    },
    "sd_lai": {
        "title": "Standard Deviation of eLAI",
        "description": "Standard deviation of effective Leaf Area Index",
        "unit": "m²/m²",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "voxel",
    },
    # Vertical LAD
    "mean_mean_xy_lad": {
        "title": "Mean of Mean LAD",
        "description": "Mean of the horizontal mean (x, y dimensions) of LAD. Mean of horizontal slices.",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "vertical",
        "metric_type": "voxel",
    },
    "sd_mean_xy_lad": {
        "title": "SD of Mean LAD",
        "description": "Standard deviation of the horizontal mean (x, y dimensions) of LAD. Mean of horizontal slices.",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "vertical",
        "metric_type": "voxel",
    },
    "cv_mean_xy_lad": {
        "title": "CV of Mean LAD",
        "description": "Coefficient of variation of the horizontal mean (x, y dimensions) of LAD. Mean of horizontal slices.",
        "unit": "ratio",
        "category": "complexity",
        "sub_category": "vertical",
        "metric_type": "voxel",
    },
    "mean_cv_xy_lad": {
        "title": "Mean CV of LAD",
        "description": "Mean of the coefficient of variation of LAD along a vertical column.",
        "unit": "ratio",
        "category": "complexity",
        "sub_category": "vertical",
        "metric_type": "voxel",
    },
    # Vertical PLAD
    "mean_mean_xy_plad": {
        "title": "Mean of Mean PLAD",
        "description": "Mean of the horizontal mean (x, y dimensions) of LAD. Mean of horizontal slices.",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "vertical",
        "metric_type": "voxel",
    },
    "sd_mean_xy_plad": {
        "title": "SD of Mean PLAD",
        "description": "Standard deviation of the horizontal mean (x, y dimensions) of LAD. Mean of horizontal slices.",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "vertical",
        "metric_type": "voxel",
    },
    "cv_mean_xy_plad": {
        "title": "CV of Mean PLAD",
        "description": "Coefficient of variation of the horizontal mean (x, y dimensions) of LAD. Mean of horizontal slices.",
        "unit": "ratio",
        "category": "complexity",
        "sub_category": "vertical",
        "metric_type": "voxel",
    },
    "mean_cv_xy_plad": {
        "title": "Mean CV of PLAD",
        "description": "Mean of the coefficient of variation of LAD along a vertical column.",
        "unit": "ratio",
        "category": "complexity",
        "sub_category": "vertical",
        "metric_type": "voxel",
    },
    # Horizontal LAD
    "mean_mean_z_lad": {
        "title": "Mean of mean LAD along a vertical column",
        "description": "",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "voxel",
    },
    "sd_mean_z_lad": {
        "title": "SD of Mean LAD (Vertical Profile)",
        "description": "Standard deviation of mean LAD along a vertical column",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "voxel",
    },
    "cv_mean_z_lad": {
        "title": "CV of Mean LAD (Vertical Profile)",
        "description": "Coefficient of variation of mean LAD along a vertical column",
        "unit": "ratio",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "voxel",
    },
    # Horizontal PLAD
    "mean_mean_z_plad": {
        "title": "Mean of mean PLAD along a vertical column",
        "description": "",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "voxel",
    },
    "sd_mean_z_plad": {
        "title": "SD of Mean PLAD (Vertical Profile)",
        "description": "Standard deviation of mean LAD along a vertical column",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "voxel",
    },
    "cv_mean_z_plad": {
        "title": "CV of Mean PLAD (Vertical Profile)",
        "description": "Coefficient of variation of mean LAD along a vertical column",
        "unit": "ratio",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "voxel",
    },
    # 3D LAD metrics
    "mean_lad": {
        "title": "Mean LAD",
        "description": "Mean Leaf Area Density across all voxels",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "sd_lad": {
        "title": "Standard Deviation of LAD",
        "description": "Standard deviation of Leaf Area Density across all voxels",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "cv_lad": {
        "title": "Coefficient of Variation of LAD",
        "description": "Coefficient of variation of Leaf Area Density across all voxels",
        "unit": "ratio",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "shan_lad": {
        "title": "Shannon Entropy of LAD",
        "description": "Shannon entropy index of LAD using 50 equal sized bins across LAD range.",
        "unit": "index",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "shan_lad_set": {
        "title": "Shannon Entropy of LAD",
        "description": "Shannon entropy index of LAD using 50 equal sized bins between 0 and 4.",
        "unit": "index",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "mean_plad": {
        "title": "Mean PLAD",
        "description": "Mean Leaf Area Density across all voxels",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "sd_plad": {
        "title": "Standard Deviation of PLAD",
        "description": "Standard deviation of Leaf Area Density across all voxels",
        "unit": "m²/m³",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "cv_plad": {
        "title": "Coefficient of Variation of PLAD",
        "description": "Coefficient of variation of Leaf Area Density across all voxels",
        "unit": "ratio",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "shan_plad": {
        "title": "Shannon Entropy of PLAD",
        "description": "Shannon entropy index of PLAD using 50 equal sized bins across LAD range.",
        "unit": "index",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
    "shan_plad_set": {
        "title": "Shannon Entropy of PLAD",
        "description": "Shannon entropy index of PLAD using 50 equal sized bins between 0 and 1",
        "unit": "index",
        "category": "complexity",
        "sub_category": "3D",
        "metric_type": "voxel",
    },
}


# Takes as input the voxels
# Reduces that to a summary metric
def calculate_voxel_metrics(voxels: Dataset):
    lad = voxels["lad_weighted"]
    plad = voxels["plad_weighted"]

    # Vertical LAD
    mean_xy_lad = lad.mean(dim=["x", "y"])
    mean_mean_xy_lad = mean_xy_lad.mean().item()
    sd_mean_xy_lad = mean_xy_lad.std().item()
    cv_mean_xy_lad = sd_mean_xy_lad / mean_mean_xy_lad

    # Verical PLAD
    mean_xy_plad = plad.mean(dim=["x", "y"])
    mean_mean_xy_plad = mean_xy_plad.mean().item()
    sd_mean_xy_plad = mean_xy_plad.std().item()
    cv_mean_xy_plad = sd_mean_xy_plad / mean_mean_xy_plad

    # Your existing code with warning suppression
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Degrees of freedom <= 0 for slice")
        sd_xy_lad = lad.std(dim=["x", "y"])
        sd_xy_plad = plad.std(dim=["x", "y"])

    cv_xy_lad = sd_xy_lad / mean_mean_xy_lad
    cv_xy_plad = sd_xy_plad / mean_mean_xy_plad
    mean_cv_xy_lad = cv_xy_lad.mean().item()
    mean_cv_xy_plad = cv_xy_plad.mean().item()

    # Horizontal LAD
    mean_z_lad = lad.mean(dim="z")
    mean_mean_z_lad = mean_z_lad.mean().item()
    sd_mean_z_lad = mean_z_lad.std().item()
    cv_mean_z_lad = sd_mean_z_lad / mean_mean_z_lad

    # Horizontal PLAD
    mean_z_plad = plad.mean(dim="z")
    mean_mean_z_plad = mean_z_plad.mean().item()
    sd_mean_z_plad = mean_z_plad.std().item()
    cv_mean_z_plad = sd_mean_z_plad / mean_mean_z_plad

    # 3D metrics LAD
    mean_lad = lad.mean().item()
    sd_lad = lad.std().item()
    cv_lad = sd_lad / mean_lad

    lad_bins_count = lad.groupby_bins(lad, bins=50).count()
    lad_bins_count_total = lad_bins_count.sum().item()
    lad_bins_proportion = lad_bins_count / lad_bins_count_total
    shan_lad = -(lad_bins_proportion * np.log(lad_bins_proportion)).sum().item()

    lad_bins_set_count = lad.groupby_bins(lad, np.linspace(0, 4, 51)).count()
    lad_bins_set_count_total = lad_bins_set_count.sum().item()
    lad_bins_set_proportion = lad_bins_set_count / lad_bins_set_count_total
    shan_lad_set = (
        -(lad_bins_set_proportion * np.log(lad_bins_set_proportion)).sum().item()
    )

    # 3D metrics PLAD
    mean_plad = plad.mean().item()
    sd_plad = plad.std().item()
    cv_plad = sd_plad / mean_plad

    plad_bins_count = plad.groupby_bins(plad, bins=50).count()
    plad_bins_count_total = plad_bins_count.sum().item()
    plad_bins_proportion = plad_bins_count / plad_bins_count_total
    shan_plad = -(plad_bins_proportion * np.log(plad_bins_proportion)).sum().item()

    plad_bins_set_count = plad.groupby_bins(plad, np.linspace(0, 1, 51)).count()
    plad_bins_set_count_total = plad_bins_set_count.sum().item()
    plad_bins_set_proportion = plad_bins_set_count / plad_bins_set_count_total
    shan_plad_set = (
        -(plad_bins_set_proportion * np.log(plad_bins_set_proportion)).sum().item()
    )

    return {
        # LAI (Cover)
        "mean_lai": voxels["lai_weighted"].mean().item(),
        "sd_lai": voxels["lai_weighted"].std().item(),
        # Vertical LAD
        "mean_mean_xy_lad": mean_mean_xy_lad,
        "sd_mean_xy_lad": sd_mean_xy_lad,
        "cv_mean_xy_lad": cv_mean_xy_lad,
        "mean_cv_xy_lad": mean_cv_xy_lad,
        # Vertical PLAD metrics
        "mean_mean_xy_plad": mean_mean_xy_plad,
        "sd_mean_xy_plad": sd_mean_xy_plad,
        "cv_mean_xy_plad": cv_mean_xy_plad,
        "mean_cv_xy_plad": mean_cv_xy_plad,
        # Horizontal LAD
        "mean_mean_z_lad": mean_mean_z_lad,
        "sd_mean_z_lad": sd_mean_z_lad,
        "cv_mean_z_lad": cv_mean_z_lad,
        # Horizontal PLAD
        "mean_mean_z_plad": mean_mean_z_plad,
        "sd_mean_z_plad": sd_mean_z_plad,
        "cv_mean_z_plad": cv_mean_z_plad,
        # Voxel Level
        "mean_lad": mean_lad,
        "sd_lad": sd_lad,
        "cv_lad": cv_lad,
        "mean_plad": mean_plad,
        "sd_plad": sd_plad,
        "cv_plad": cv_plad,
        "shan_lad": shan_lad,
        "shan_lad_set": shan_lad_set,
        "shan_plad": shan_plad,
        "shan_plad_set": shan_plad_set,
    }
