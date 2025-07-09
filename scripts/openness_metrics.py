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


def calculate_openness_metrics(row: Series):
    site_plot_id = row.site_plot_id
    assert isinstance(site_plot_id, str), "A plot must have a site plot ID"

    print(f"Calculating metrics for {site_plot_id}")

    site = row.site
    assert isinstance(site, str), "A plot must have a site"

    geometry = row.geometry
    assert isinstance(geometry, shapely.Polygon), "A plots geometry must be a polygon"

    polygon_wkt = shapely.to_wkt(geometry, 2)
    input_file = f"data/sites/lidar/{site}.copc.laz"

    pl = pdal.Reader(
        input_file, type="readers.copc", polygon=polygon_wkt
    ) | pdal.Filter(type="filters.ferry", dimensions="HeightAboveGround => Z")
    pl.execute()

    points = pl.arrays[0]
    assert isinstance(points, np.ndarray), "Points should be a numpy array"

    Z = points["Z"]
    Z_above_2 = points[points["Z"] > 2]

    proportion_above_2 = len(Z_above_2) / len(Z)

    chm_file_name = f"data/sites/raster/{site}_chm.tif"

    with rasterio.open(chm_file_name) as chm:
        masked_data, masked_transform = mask(
            chm, [geometry], crop=True, nodata=chm.nodata
        )

        chm_data = masked_data[0]

        # Remove nodata pixels
        chm_data = chm_data[chm_data != chm.nodata]

        # Gaps are points below height threshold
        gaps_05 = chm_data[chm_data <= 0.5]
        gaps_2 = chm_data[chm_data <= 2]

        deep_gap_fraction_05 = len(gaps_05) / len(chm_data)
        deep_gap_fraction_2 = len(gaps_2) / len(chm_data)

    metrics = {
        "proportion_above_2": proportion_above_2,
        "deep_gap_fraction_05": deep_gap_fraction_05,
        "deep_gap_fraction_2": deep_gap_fraction_2,
        "gap_fraction_profile": -999,
    }

    return pd.Series(metrics, dtype=float)


openness_metrics = plots.apply(calculate_openness_metrics, axis=1)
plots_with_openness_metrics = pd.concat([plots, openness_metrics], axis=1).drop(
    columns="geometry"
)
plots_with_openness_metrics.to_json(
    "data/plots/openness_metrics.json", orient="records", indent=4
)
openness_metrics_metadata = {
    "proportion_above_2": "Number of points with height above ground > 2, divided by total number of points. (Unit: unitless fraction)",
    "deep_gap_fraction_05": "Number of gap pixels in CHM divided by total number of pixel. A gap is a pixel with a height <= 0.5 m. (Unit: unitless fraction)",
    "deep_gap_fraction_2": "Number of gap pixels in CHM divided by total number of pixel. A gap is a pixel with a height <= 2 m. (Unit: unitless fraction)",
    "gap_fraction_profile": "TODO",
}
json.dump(
    openness_metrics_metadata,
    open("data/plots/openness_metrics_metadata.json", "w"),
    indent=4,
)
