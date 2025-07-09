import geopandas
import numpy as np
import pandas as pd
import pdal
import shapely
from numpy.typing import NDArray

interior_metrics_metadata = {
    "sd_of_height": {
        "title": "Standard Deviation of Height",
        "description": "Standard deviation of vegetation points",
        "unit": "m",
        "category": "interior",
    },
    "coeff_var_of_height": {
        "title": "Coefficient of Variation of Height",
        "description": "Coefficient of variation of height. SDH / MH",
        "unit": "unitless",
        "category": "interior",
    },
    "fhd": {
        "title": "Foliage Height Diversity",
        "description": "Foliage Height Diversity",
        "unit": "unitless",
        "category": "interior",
    },
    "gini_coeff_index": {
        "title": "Gini Coefficient Index",
        "description": "Gini coefficient index",
        "unit": "unitless",
        "category": "interior",
    },
    "mean_of_sd_of_height": {
        "title": "Mean of Standard Deviation of Height",
        "description": "Mean of standard deviation of height",
        "unit": "m",
        "category": "interior",
    },
    "sd_of_sd_of_height": {
        "title": "Standard Deviation of Standard Deviation of Height",
        "description": "Standard deviation of standard deviation of height",
        "unit": "m",
        "category": "interior",
    },
}


def calculate_interior_metrics(points: NDArray):
    points = points[points["HeightAboveGround"] >= 0.5]
    Z = points["HeightAboveGround"]

    z_mean = np.mean(Z)
    z_std = np.std(Z)
    z_coeff_var = z_std / z_mean

    # TODO: Calculate FHD, Gini coefficient, and other metrics
    # For now, using placeholder values
    metrics = {
        "sd_of_height": z_std,
        "coeff_var_of_height": z_coeff_var,
        "fhd": -999,  # Placeholder
        "gini_coeff_index": -999,  # Placeholder
        "mean_of_sd_of_height": -999,  # Placeholder
        "sd_of_sd_of_height": -999,  # Placeholder
    }

    return pd.Series(metrics, dtype=float)


if __name__ == "__main__":
    plots = geopandas.read_file("data/plots/plots.geo.json")
    plot = plots.iloc[0]
    site = plot.site
    geometry = plot.geometry
    polygon_wkt = shapely.to_wkt(geometry, 2)
    lidar_file = f"data/sites/lidar/{site}.copc.laz"
    chm_file = f"data/sites/raster/{site}_chm.tif"

    pl = pdal.Reader(lidar_file, type="readers.copc", polygon=polygon_wkt).pipeline()
    pl.execute()
    points = pl.arrays[0]

    print(calculate_interior_metrics(points=points))
