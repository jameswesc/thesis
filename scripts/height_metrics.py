import json

import geopandas
import numpy as np
import pandas as pd
import pdal
import rasterio
import shapely
from pandas import Series
from rasterio.mask import mask

plots = geopandas.read_file("data/plots/plots.geo.json")
sites = geopandas.read_file("data/sites/sites.geo.json")


def calculate_height_metrics(row: Series):
    site_plot_id = row.site_plot_id
    assert isinstance(site_plot_id, str), "A plot must have a site plot ID"

    print(f"Calculating height metrics for {site_plot_id}")

    site = row.site
    assert isinstance(site, str), "A plot must have a site"

    geometry = row.geometry
    assert isinstance(geometry, shapely.Polygon), "A plots geometry must be a polygon"

    polygon_wkt = shapely.to_wkt(geometry, 2)
    input_file = f"data/sites/lidar/{site}.copc.laz"

    pl = (
        pdal.Reader(input_file, type="readers.copc", polygon=polygon_wkt)
        | pdal.Filter(type="filters.ferry", dimensions="HeightAboveGround => Z")
        # Cut off height for vegetation at 0.5 m
        | pdal.Filter(type="filters.range", limits="Z[0.5:]")
    )
    pl.execute()

    points = pl.arrays[0]
    assert isinstance(points, np.ndarray), "Points should be a numpy array"

    Z = points["Z"]

    metrics = {
        "mean_height": np.mean(Z),
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

    chm_file_name = f"data/sites/raster/{site}_chm.tif"

    with rasterio.open(chm_file_name) as chm:
        masked_data, masked_transform = mask(
            chm, [geometry], crop=True, nodata=chm.nodata
        )

        chm_data = masked_data[0]
        # Remove nodata pixels
        chm_data = chm_data[chm_data != chm.nodata]
        metrics["mean_canopy_height"] = np.mean(chm_data)

    return pd.Series(metrics, dtype=float)


height_metrics = plots.apply(calculate_height_metrics, axis=1)
plots_with_height_metrics = pd.concat([plots, height_metrics], axis=1).drop(
    columns="geometry"
)
plots_with_height_metrics.to_json(
    "data/plots/height_metrics.json", orient="records", indent=4
)

height_metrics_metadata = {
    "mean_height": "Mean height above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q100": "Maximum height (100th percentile) above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q99": "99th percentile height above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q95": "95th percentile height above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q75": "75th percentile height above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q50": "Median height above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q25": "25th percentile height above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q5": "5th percentile height above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q1": "1st percentile height above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "q0": "Minimum height (0th percentile) above ground of vegetation points (points >= 0.5 m) (Unit: m)",
    "mean_canopy_height": "Mean pixel from 1m² canopy height model (CHM). CHM is defined as maximum height within 1m² cell. (Unit: m)",
}

json.dump(
    height_metrics_metadata,
    open("data/plots/height_metrics_metadata.json", "w"),
    indent=4,
)
