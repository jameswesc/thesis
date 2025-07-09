import geopandas
import numpy as np
import pandas as pd
import pdal
import shapely
from numpy.typing import NDArray
from shapely.geometry import Polygon

ancillary_metrics_metadata = {
    "plot_area": {
        "title": "Plot Area",
        "description": "Area of the plot geometry",
        "unit": "m²",
        "category": "ancillary",
    },
    "pulse_density": {
        "title": "Pulse Density",
        "description": "Number of first returns divided by plot area",
        "unit": "pulses per m²",
        "category": "ancillary",
    },
    "point_density": {
        "title": "Point Density",
        "description": "Number of all returns divided by plot area",
        "unit": "points per m²",
        "category": "ancillary",
    },
    "min_scan_angle": {
        "title": "Minimum Scan Angle",
        "description": "Minimum scan angle",
        "unit": "degrees",
        "category": "ancillary",
    },
    "max_scan_angle": {
        "title": "Maximum Scan Angle",
        "description": "Maximum scan angle",
        "unit": "degrees",
        "category": "ancillary",
    },
    "scan_angle_half_width": {
        "title": "Scan Angle Half Width",
        "description": "Scan angle swath width. Calculated as max(abs(min_scan_angle), abs(max_scan_angle))",
        "unit": "degrees",
        "category": "ancillary",
    },
}


def calculate_ancillary_metrics(points: NDArray, geometry: Polygon):
    plot_area = geometry.area

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


if __name__ == "__main__":
    plots = geopandas.read_file("data/plots/plots.geo.json")
    plot = plots.iloc[0]
    site = plot.site
    geometry = plot.geometry
    polygon_wkt = shapely.to_wkt(geometry, 2)
    lidar_file = f"data/sites/lidar/{site}.copc.laz"

    pl = pdal.Reader(lidar_file, type="readers.copc", polygon=polygon_wkt).pipeline()
    pl.execute()
    points = pl.arrays[0]

    print(calculate_ancillary_metrics(points=points, geometry=geometry))
