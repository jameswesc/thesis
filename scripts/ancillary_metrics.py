import geopandas
import numpy as np
import pandas as pd
import pdal
import shapely
from pandas import Series

plots = geopandas.read_file("data/plots/plots.geo.json")
sites = geopandas.read_file("data/sites/sites.geo.json")

# plots = plots.head(20)


def calculate_ancillary_metrics(row: Series):
    site_plot_id = row.site_plot_id
    assert isinstance(site_plot_id, str), "A plot must have a site plot ID"

    print(f"Calculating height metrics for {site_plot_id}")

    site = row.site
    assert isinstance(site, str), "A plot must have a site"

    geometry = row.geometry
    assert isinstance(geometry, shapely.Polygon), "A plots geometry must be a polygon"

    plot_area = geometry.area

    polygon_wkt = shapely.to_wkt(geometry, 2)
    input_file = f"data/sites/lidar/{site}.copc.laz"

    pl = pdal.Reader(input_file, type="readers.copc", polygon=polygon_wkt).pipeline()
    pl.execute()

    points = pl.arrays[0]
    assert isinstance(points, np.ndarray), "Points should be a numpy array"

    first_returns = points[points["ReturnNumber"] == 1]

    min_scan = np.min(points["ScanAngleRank"])
    max_scan = np.max(points["ScanAngleRank"])
    scan_angle_half_width = max(abs(min_scan), abs(max_scan))

    metrics = {
        "plot_area": plot_area,
        "pulse_density": len(first_returns) / plot_area,
        "point_density": len(points) / plot_area,
        "min_scan_angle": min_scan,
        "max_scan_angle": max_scan,
        "scan_angle_half_width": scan_angle_half_width,
    }

    return pd.Series(metrics, dtype=float)


ancillary_metrics = plots.apply(calculate_ancillary_metrics, axis=1)
plots_with_ancillary_metrics = pd.concat([plots, ancillary_metrics], axis=1).drop(
    columns="geometry"
)
plots_with_ancillary_metrics.to_json(
    "data/plots/ancillary_metrics.json", orient="records", indent=2
)

# print(ancillary_metrics)
