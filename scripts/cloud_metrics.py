import numpy as np
from pandas import DataFrame, Series
from shapely import Polygon

cloud_metrics_metadata = {
    # Height
    "mean_veg_height": {
        "title": "Mean Vegetation Height",
        "description": "Mean height above ground of points avove (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "mean_veg_height_first_return": {
        "title": "Mean Vegetation Height (First Returns)",
        "description": "Mean height above ground of first return points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "median_veg_height": {
        "title": "Median Vegetation Height",
        "description": "Median height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "max_veg_height": {
        "title": "Maximum Vegetation Height",
        "description": "Maximum height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "q99_veg_height": {
        "title": "99th Percentile Vegetation Height",
        "description": "99th percentile height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "q95_veg_height": {
        "title": "95th Percentile Vegetation Height",
        "description": "95th percentile height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "q75_veg_height": {
        "title": "75th Percentile Vegetation Height",
        "description": "75th percentile height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "q50_veg_height": {
        "title": "50th Percentile Vegetation Height",
        "description": "50th percentile (median) height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "q25_veg_height": {
        "title": "25th Percentile Vegetation Height",
        "description": "25th percentile height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "q5_veg_height": {
        "title": "5th Percentile Vegetation Height",
        "description": "5th percentile height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "q1_veg_height": {
        "title": "1st Percentile Vegetation Height",
        "description": "1st percentile height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    "min_veg_height": {
        "title": "Minimum Vegetation Height",
        "description": "Minimum height above ground of points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "height",
        "metric_type": "cloud",
    },
    # Interior
    "sd_veg_height": {
        "title": "Standard Deviation of Vegetation Height",
        "description": "Standard deviation of height above ground for points above (>) veg cutoff (default 0.5 m)",
        "unit": "m",
        "category": "interior",
        "metric_type": "cloud",
    },
    "cv_veg_height": {
        "title": "Coefficient of Variation of Vegetation Height",
        "description": "Coefficient of variation (SD/mean) of height above ground for points above (>) veg cutoff (default 0.5 m)",
        "unit": "ratio",
        "category": "interior",
        "metric_type": "cloud",
    },
    "gini_coeff_index_veg": {
        "title": "Gini Coefficient of Vegetation Height",
        "description": "Gini coefficient index measuring inequality in vegetation height distribution",
        "unit": "index",
        "category": "interior",
        "metric_type": "cloud",
    },
    # Cover
    "prop_above_2m": {
        "title": "Proportion of Points Above 2m",
        "description": "Proportion of all points with height above ground > 2m",
        "unit": "proportion",
        "category": "cover",
        "metric_type": "cloud",
    },
    "prop_veg": {
        "title": "Proportion of Vegetation Points",
        "description": "Proportion of all points with height above ground > veg cutoff (default 0.5 m)",
        "unit": "proportion",
        "category": "cover",
        "metric_type": "cloud",
    },
    # Ancillary
    "mean_elevation": {
        "title": "Mean Ground Elevation",
        "description": "Mean altitude of ground points (Z = 0)",
        "unit": "m",
        "category": "ancillary",
        "metric_type": "cloud",
    },
    "plot_area": {
        "title": "Plot Area",
        "description": "Area of the plot geometry",
        "unit": "m²",
        "category": "ancillary",
        "metric_type": "cloud",
    },
    "pulse_density": {
        "title": "Pulse Density",
        "description": "Number of first returns divided by plot area",
        "unit": "pulses per m²",
        "category": "ancillary",
        "metric_type": "cloud",
    },
    "point_density": {
        "title": "Point Density",
        "description": "Number of all returns divided by plot area",
        "unit": "points per m²",
        "category": "ancillary",
        "metric_type": "cloud",
    },
    "scan_angle_half_width": {
        "title": "Scan Angle Half Width",
        "description": "Scan angle swath width. Calculated as max(abs(min_scan_angle), abs(max_scan_angle))",
        "unit": "degrees",
        "category": "ancillary",
        "metric_type": "cloud",
    },
}


def calculate_cloud_metrics(points: DataFrame, polygon: Polygon, veg_cutoff=0.5):
    # Assert that points has the required columns
    assert "Z" in points.columns, "Points dataframe must have 'Z' column"
    assert "ReturnNumber" in points.columns, (
        "Points dataframe must have 'ReturnNumber' column"
    )
    assert "ScanAngleRank" in points.columns, (
        "Points dataframe must have 'ScanAngleRank' column"
    )

    first_returns = points[points["ReturnNumber"] == 1]
    veg_points = points[points["Z"] > veg_cutoff]
    veg_first_returns = first_returns[first_returns["Z"] > veg_cutoff]

    assert isinstance(first_returns, DataFrame), (
        "Derived first returns should be a dataframe"
    )
    assert isinstance(veg_points, DataFrame), "Derived veg points should be a dataframe"
    assert isinstance(veg_first_returns, DataFrame), (
        "Derived veg first returns should be a dataframe"
    )

    # ---- Height Metrics ----

    veg_heights = veg_points["Z"]
    assert isinstance(veg_heights, Series), "Derived veg heights should be a series"

    mean_veg_height = veg_heights.mean()
    mean_veg_height_first_return = veg_first_returns["Z"].mean()
    median_veg_height = veg_heights.median()

    veg_height_quantiles = {
        "max_veg_height": veg_heights.max(),
        "q99_veg_height": veg_heights.quantile(0.99),
        "q95_veg_height": veg_heights.quantile(0.95),
        "q75_veg_height": veg_heights.quantile(0.75),
        "q50_veg_height": veg_heights.quantile(0.50),
        "q25_veg_height": veg_heights.quantile(0.25),
        "q5_veg_height": veg_heights.quantile(0.5),
        "q1_veg_height": veg_heights.quantile(0.1),
        "min_veg_height": veg_heights.min(),
    }

    # Gini Coefficient
    # Taken from https://github.com/pysal/inequality/blob/main/inequality/gini.py
    x = np.array(veg_heights.values)
    n = len(x)
    x_sum = x.sum()
    n_x_sum = n * x_sum
    x = x.ravel()  # ensure shape is (n,)
    r_x = (2.0 * np.arange(1, len(x) + 1) * x[np.argsort(x)]).sum()
    gini_coeff_index_veg = (r_x - n_x_sum - x_sum) / n_x_sum

    height_metrics = {
        "mean_veg_height": mean_veg_height,
        "mean_veg_height_first_return": mean_veg_height_first_return,
        "median_veg_height": median_veg_height,
        **veg_height_quantiles,
    }

    # ---- Interior Metrics ----

    sd_veg_height = veg_heights.std()
    coeffvar_veg_height = sd_veg_height / mean_veg_height
    interior_metrics = {
        "sd_veg_height": sd_veg_height,
        "cv_veg_height": coeffvar_veg_height,
        "gini_coeff_index_veg": gini_coeff_index_veg,
    }

    # ---- Cover Metrics ----

    count_all_points = len(points)
    count_above_2m = len(points[points["Z"] > 2])
    cover_metrics = {
        "prop_above_2m": count_above_2m / count_all_points,
        "prop_veg": len(veg_points) / count_all_points,
    }

    # ---- Ancillary Metrics ----
    ground_points = points[points["Z"] == 0]
    count_pulses = len(first_returns)

    min_scan = points["ScanAngleRank"].min()
    max_scan = points["ScanAngleRank"].max()
    scan_angle_half_width = max(abs(min_scan), abs(max_scan))

    ancillary_metrics = {
        "mean_elevation": ground_points["Altitude"].mean(),
        "pulse_density": count_pulses / polygon.area,
        "point_density": count_all_points / polygon.area,
        "plot_area": polygon.area,
        "scan_angle_half_width": scan_angle_half_width,
    }

    return {**height_metrics, **interior_metrics, **cover_metrics, **ancillary_metrics}
