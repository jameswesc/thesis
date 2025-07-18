import numpy as np
import pandas as pd
import xarray as xr
from pandas import DataFrame
from shapely import Polygon
from xarray import Dataset
from xarray.groupers import BinGrouper

pixel_metrics_metadata = {
    "mean_canopy_height": {
        "title": "Mean Canopy Height",
        "description": "Mean value of canopy height pixels. Canopy height is the maximum vegetation point in 1 m grid.",
        "unit": "m",
        "category": "height",
        "metric_type": "pixel",
    },
    "top_rugosity": {
        "title": "Top Rugosity",
        "description": "Standard deviation of canopy height pixels. Canopy height is the maximum vegetation point in 1 m grid.",
        "unit": "m",
        "category": "exterior",
        "metric_type": "pixel",
    },
    "mean_sd_veg_height": {
        "title": "Mean of SD of Veg Height",
        "description": "Mean value of standard deviation of vegetation point height pixels (1m grid).",
        "unit": "m",
        "category": "interior",
        "metric_type": "pixel",
    },
    "sd_sd_veg_height": {
        "title": "SD of SD of Veg Height",
        "description": "Standard deviation value of standard deviation of vegetation point height pixels (1m grid).",
        "unit": "m",
        "category": "interior",
        "metric_type": "pixel",
    },
}


def calculate_pixel_metrics(
    points: DataFrame, polygon: Polygon, veg_cutoff=0.5, pixel_size=(1.0, 1.0)
):
    x_min, x_max = (points.X.min(), points.X.max())
    y_min, y_max = (points.Y.min(), points.Y.max())

    dx, dy = pixel_size

    # Minus one more voxel unit from x and y edges so we don't need to include
    # lowest. Each cell is (low_edge, high_edge] . Likely lowest bin for x
    # and y will always be empty. That's ok.
    x_edges = np.arange(np.floor(x_min / dx) * dx, x_max + dx, dx)
    y_edges = np.arange(np.floor(y_min / dy) * dy, y_max + dy, dy)

    x_coords = (x_edges[:-1] + x_edges[1:]) / 2
    y_coords = (y_edges[:-1] + y_edges[1:]) / 2

    points_ds = xr.Dataset.from_dataframe(points.reset_index())
    # print(points_ds.to_pandas().head())

    pixel_group = points_ds.groupby(
        X=BinGrouper(
            bins=x_edges,
            labels=x_coords,
        ),
        Y=BinGrouper(
            bins=y_edges,
            labels=y_coords,
        ),
    )

    pixels = pixel_group.map(pixel_metrics_map, veg_cutoff=veg_cutoff)
    pixel_metrics = pixel_metrics_reduce(pixels)

    return pixel_metrics


# Takes as input the points for that cell
# Calculates a metric for each cell
def pixel_metrics_map(ds: Dataset, veg_cutoff):
    # Points will be a DataFrame similar to what we had for cloud metrics
    # Except that its just the points for each cell
    points = ds.to_pandas()

    veg_points = points[points["Z"] > veg_cutoff]
    veg_first_returns = veg_points[veg_points["ReturnNumber"] == 1]

    return xr.Dataset(
        {
            "canopy_height": veg_first_returns["Z"].max(),
            "sd_height": veg_points["Z"].std(),
        }
    )


# Takes as input the pixels
# Reduces that to a summary metric
def pixel_metrics_reduce(pixels: Dataset):
    return pd.Series(
        {
            "mean_canopy_height": pixels["canopy_height"].mean().item(),
            "top_rugosity": pixels["canopy_height"].std().item(),
            "mean_sd_veg_height": pixels["sd_height"].mean().item(),
            "sd_sd_veg_height": pixels["sd_height"].std().item(),
        }
    )
