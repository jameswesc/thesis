import numpy as np
import xarray as xr
from pandas import DataFrame
from xarray import Dataset
from xarray.groupers import BinGrouper


def create_pixel_dataset(points: DataFrame, veg_cutoff=0.5, pixel_size=(1.0, 1.0)):
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

    # Takes as input the points for that cell
    # Calculates a metric for each cell
    def pixel_metrics_map(ds: Dataset, veg_cutoff):
        # Create boolean masks for filtering
        veg_mask = ds["Z"] > veg_cutoff
        first_return_mask = ds["ReturnNumber"] == 1
        veg_first_return_mask = veg_mask & first_return_mask

        # Apply masks and calculate metrics
        veg_z = ds["Z"].where(veg_mask)
        veg_first_return_z = ds["Z"].where(veg_first_return_mask)

        # If no veg first returns put canopy height to 0 (not nan)
        # so we can calculate deep gap fraction without needing a shape mask
        veg_first_return_count = veg_first_return_mask.sum()
        canopy_height = veg_first_return_z.max() if veg_first_return_count > 0 else 0

        # Calculate std only if we have 2+ points, otherwise return NaN
        veg_count = veg_mask.sum()
        sd_height = veg_z.std() if veg_count >= 2 else np.nan

        return xr.Dataset(
            {
                "canopy_height": canopy_height,
                "sd_height": sd_height,
            }
        )

    pixels = pixel_group.map(pixel_metrics_map, veg_cutoff=veg_cutoff)
    pixels.attrs["srs"] = "EPSG:7855"

    return pixels


pixel_metrics_metadata = {
    # Height
    "mean_canopy_height": {
        "title": "Mean Canopy Height",
        "description": "Mean value of canopy height pixels. Canopy height is the maximum vegetation point in 1 m grid.",
        "unit": "m",
        "category": "height",
        "metric_type": "pixel",
    },
    # Cover
    "deep_gap_fraction": {
        "title": "Deep Gap Fraction",
        "description": "Fraction of pixels with canopy height below the vegetation cutoff (represented as 0).",
        "unit": "%",
        "category": "cover",
        "metric_type": "pixel",
    },
    # Complexity
    #   - Exterior
    "top_rugosity": {
        "title": "Top Rugosity",
        "description": "Standard deviation of canopy height pixels. Canopy height is the maximum vegetation point in 1 m grid.",
        "unit": "m",
        "category": "complexity",
        "sub_category": "exterior",
        "metric_type": "pixel",
    },
    "rumple_index": {
        "title": "Rumple Index",
        "description": "TODO",
        "unit": "fraction",
        "category": "complexity",
        "sub_category": "exterior",
        "metric_type": "pixel",
    },
    # Complexity
    #   - Horizontal
    "mean_sd_veg_height": {
        "title": "Mean of SD of Veg Height",
        "description": "Mean value of standard deviation of vegetation point height pixels (1m grid).",
        "unit": "m",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "pixel",
    },
    "sd_sd_veg_height": {
        "title": "SD of SD of Veg Height",
        "description": "Standard deviation value of standard deviation of vegetation point height pixels (1m grid).",
        "unit": "m",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "pixel",
    },
    "cv_sd_veg_height": {
        "title": "CV of SD of Veg Height",
        "description": "Coefficient of variation of standard deviation of vegetation point height pixels (1m grid).",
        "unit": "m",
        "category": "complexity",
        "sub_category": "horizontal",
        "metric_type": "pixel",
    },
}


def calculate_pixel_metrics(pixels: Dataset):
    deep_gap_pixels = pixels["canopy_height"].where(pixels["canopy_height"] == 0)
    deep_gap_fraction = deep_gap_pixels.count() / pixels["canopy_height"].count()

    # Gaps in the canopy are set as 0
    canopy_height = pixels["canopy_height"].where(pixels["canopy_height"] > 0)

    mean_sd_veg_height = pixels["sd_height"].mean().item()
    sd_sd_veg_height = pixels["sd_height"].std().item()
    cv_sd_veg_height = sd_sd_veg_height / mean_sd_veg_height

    return {
        # Height
        "mean_canopy_height": canopy_height.mean().item(),
        # Cover
        "deep_gap_fraction": deep_gap_fraction.item(),
        # Complexity
        #   - Exterior
        "top_rugosity": canopy_height.std().item(),
        "rumple_index": -999,
        #   - Horizontal
        "mean_sd_veg_height": mean_sd_veg_height,
        "sd_sd_veg_height": sd_sd_veg_height,
        "cv_sd_veg_height": cv_sd_veg_height,
    }
