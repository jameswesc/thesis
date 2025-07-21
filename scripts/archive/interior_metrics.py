import geopandas
import numpy as np
import pandas as pd
import pdal
import rasterio
import shapely
from numpy.typing import NDArray
from rasterio.mask import mask

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
    # TODO
    "fhd": {
        "title": "Foliage Height Diversity",
        "description": "Foliage Height Diversity",
        "unit": "unitless",
        "category": "interior",
    },
    "gini_coeff_index": {
        "title": "Gini Coefficient Index",
        "description": "Gini coefficient index, taken from https://pysal.org/inequality/generated/inequality.gini.Gini.html. Computed on vegetation points (Z > 0.5). Also see https://www.statsdirect.com/help/nonparametric_methods/gini.htm",
        "unit": "unitless",
        "category": "interior",
    },
    "mean_of_sd_of_height": {
        "title": "Mean of Standard Deviation of height",
        "description": "Mean of pixels from the 1 m² standard deviation of height of vegetation points (Z > 0.5) raster.",
        "unit": "m",
        "category": "interior",
    },
    "sd_of_sd_of_height": {
        "title": "Standard Deviation of Standard Deviation of Height",
        "description": "Standard deviation of pixels from the 1 m² standard deviation of height of vegetation points (Z > 0.5) raster.",
        "unit": "m",
        "category": "interior",
    },
}


def calculate_interior_metrics(points: NDArray, sdh: NDArray):
    points = points[points["HeightAboveGround"] >= 0.5]
    Z = points["HeightAboveGround"]

    z_mean = np.mean(Z)
    z_std = np.std(Z)
    z_coeff_var = z_std / z_mean

    # Gini Coefficient
    # Taken from https://github.com/pysal/inequality/blob/main/inequality/gini.py
    x = Z
    n = len(x)
    x_sum = x.sum()
    n_x_sum = n * x_sum
    x = x.ravel()  # ensure shape is (n,)
    r_x = (2.0 * np.arange(1, len(x) + 1) * x[np.argsort(x)]).sum()
    gini_coefficient = (r_x - n_x_sum - x_sum) / n_x_sum

    metrics = {
        "sd_of_height": z_std,
        "coeff_var_of_height": z_coeff_var,
        "fhd": -999,  # Placeholder
        "gini_coeff_index": gini_coefficient,
        "mean_of_sd_of_height": np.mean(sdh),
        "sd_of_sd_of_height": np.std(sdh),
    }

    return pd.Series(metrics, dtype=float)


if __name__ == "__main__":
    plots = geopandas.read_file("data/plots/plots.geo.json")
    plot = plots.iloc[0]
    site = plot.site
    geometry = plot.geometry
    polygon_wkt = shapely.to_wkt(geometry, 2)
    lidar_file = f"data/sites/lidar/{site}.copc.laz"
    sdh_file = f"data/sites/raster/{site}_sdh.tif"
    with rasterio.open(sdh_file) as sdh_src:
        masked_data, masked_transform = mask(
            sdh_src, [geometry], crop=True, nodata=sdh_src.nodata
        )

        sdh = masked_data[0]
        # Remove nodata pixels
        sdh = sdh[sdh != sdh_src.nodata]

    pl = pdal.Reader(lidar_file, type="readers.copc", polygon=polygon_wkt).pipeline()
    pl.execute()
    points = pl.arrays[0]

    print(calculate_interior_metrics(points=points, sdh=sdh))
