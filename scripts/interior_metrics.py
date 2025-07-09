import json

import geopandas
import numpy as np
import pandas as pd
import pdal
import shapely
from pandas import Series

plots = geopandas.read_file("data/plots/plots.geo.json")
sites = geopandas.read_file("data/sites/sites.geo.json")


def calculate_interior_metrics(row: Series):
    site_plot_id = row.site_plot_id
    assert isinstance(site_plot_id, str), "A plot must have a site plot ID"

    print(f"Calculating metrics for {site_plot_id}")

    site = row.site
    assert isinstance(site, str), "A plot must have a site"

    geometry = row.geometry
    assert isinstance(geometry, shapely.Polygon), "A plots geometry must be a polygon"

    polygon_wkt = shapely.to_wkt(geometry, 2)
    input_file = f"data/sites/lidar/{site}.copc.laz"

    pl = (
        pdal.Reader(input_file, type="readers.copc", polygon=polygon_wkt)
        | pdal.Filter(type="filters.ferry", dimensions="HeightAboveGround => Z")
        # Height cutoff 0.5 m
        | pdal.Filter(type="filters.range", limits="Z[0.5:]")
    )
    pl.execute()

    points = pl.arrays[0]
    assert isinstance(points, np.ndarray), "Points should be a numpy array"

    Z = points["Z"]

    z_mean = np.mean(Z)
    z_std = np.std(Z)
    z_coeff_var = z_std / z_mean

    # chm_file_name = f"data/sites/raster/{site}_chm.tif"

    # with rasterio.open(chm_file_name) as chm:
    #     masked_data, masked_transform = mask(
    #         chm, [geometry], crop=True, nodata=chm.nodata
    #     )

    #     chm_data = masked_data[0]

    #     # Remove nodata pixels
    #     chm_data = chm_data[chm_data != chm.nodata]

    #     # Gaps are points below height threshold
    #     gaps_05 = chm_data[chm_data <= 0.5]
    #     gaps_2 = chm_data[chm_data <= 2]

    #     deep_gap_fraction_05 = len(gaps_05) / len(chm_data)
    #     deep_gap_fraction_2 = len(gaps_2) / len(chm_data)

    metrics = {
        "sd_of_height": z_std,
        "coeff_var_of_height": z_coeff_var,
        "fhd": -999,
        "gini_coeff_index": -999,
        "mean_of_sd_of_height": -999,
        "sd_of_sd_of_height": -999,
    }

    return pd.Series(metrics, dtype=float)


interior_metrics = plots.apply(calculate_interior_metrics, axis=1)
plots_with_interior_metrics = pd.concat([plots, interior_metrics], axis=1).drop(
    columns="geometry"
)
plots_with_interior_metrics.to_json(
    "data/plots/interior_metrics.json", orient="records", indent=4
)
interior_metrics_metadata = {
    "sd_of_height": "Standard deviation of vegetation points (Unit: m)",
    "coeff_var_of_height": "Coefficient of variation of height. SDH / MH. (Unit: unitless)",
}
json.dump(
    interior_metrics_metadata,
    open("data/plots/interior_metrics_metadata.json", "w"),
    indent=4,
)
