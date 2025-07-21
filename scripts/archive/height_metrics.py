import geopandas
import numpy as np
import pandas as pd
import pdal
import rasterio
import shapely
from numpy.typing import NDArray
from rasterio.mask import mask

height_metrics_metadata = {
    "mean_height": {
        "title": "Mean Height",
        "description": "Mean height above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "mean_canopy_height": {
        "title": "Mean Canopy Height",
        "description": "Mean pixel from 1m² canopy height model (CHM). CHM is defined as maximum height within 1m² cell",
        "unit": "m",
        "category": "height",
    },
    "q100": {
        "title": "Maximum Height (Q100)",
        "description": "Maximum height (100th percentile) above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "q99": {
        "title": "99th Percentile Height (Q99)",
        "description": "99th percentile height above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "q95": {
        "title": "95th Percentile Height (Q95)",
        "description": "95th percentile height above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "q75": {
        "title": "75th Percentile Height (Q75)",
        "description": "75th percentile height above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "q50": {
        "title": "Median Height (Q50)",
        "description": "Median height above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "q25": {
        "title": "25th Percentile Height (Q25)",
        "description": "25th percentile height above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "q5": {
        "title": "5th Percentile Height (Q5)",
        "description": "5th percentile height above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "q1": {
        "title": "1st Percentile Height (Q1)",
        "description": "1st percentile height above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
    "q0": {
        "title": "Minimum Height (Q0)",
        "description": "Minimum height (0th percentile) above ground of vegetation points (Z >= 0.5 m)",
        "unit": "m",
        "category": "height",
    },
}


def calculate_height_metrics(points: NDArray, chm: NDArray):
    points = points[points["HeightAboveGround"] >= 0.5]
    Z = points["HeightAboveGround"]

    metrics = {
        "mean_height": np.mean(Z),
        "mean_canopy_height": np.mean(chm),
        "q100": np.percentile(Z, 100),
        "q99": np.percentile(Z, 99),
        "q95": np.percentile(Z, 95),
        "q75": np.percentile(Z, 75),
        "q50": np.percentile(Z, 50),
        "q25": np.percentile(Z, 25),
        "q5": np.percentile(Z, 5),
        "q1": np.percentile(Z, 1),
        "q0": np.percentile(Z, 0),
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
    with rasterio.open(chm_file) as chm_src:
        masked_data, masked_transform = mask(
            chm_src, [geometry], crop=True, nodata=chm_src.nodata
        )

        chm = masked_data[0]
        # Remove nodata pixels
        chm = chm[chm != chm_src.nodata]

    print(calculate_height_metrics(points=points, chm=chm))
