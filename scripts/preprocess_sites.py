from os import path

import geopandas
import pdal


def preprocess(input_file: str, output_file: str, polygon_wkt: str | None = None):
    pipeline = (
        pdal.Reader(input_file)
        | pdal.Filter(type="filters.reprojection", out_srs="EPSG:7855")
        | pdal.Filter(type="filters.crop", polygon=polygon_wkt)
        | pdal.Filter(
            type="filters.outlier", method="statistical", mean_k=6, multiplier=10
        )
        | pdal.Filter(type="filters.range", limits="Classification[0:5]")
        | pdal.Filter(type="filters.hag_nn", allow_extrapolation=False, count=1)
        | pdal.Writer(
            output_file, type="writers.copc", forward="scale,offset", extra_dims="all"
        )
    )

    point_count = pipeline.execute()
    return point_count, pipeline


data_dir = "data"
sites_file = path.join(data_dir, "sites/sites.geo.json")
sites_gdf = geopandas.read_file(sites_file).set_index("site")

for site, feature in sites_gdf.iterrows():
    input_file = path.join(data_dir, "sites/lidar-MGA94", f"{site}.laz")
    output_file = path.join(data_dir, "sites/lidar", f"{site}.copc.laz")
    wkt = feature.polygon_wkt
    print(f"Processing {site}")
    (point_count, _) = preprocess(input_file, output_file, wkt)
    print(f"\tprocessed {point_count:,d} points.")
