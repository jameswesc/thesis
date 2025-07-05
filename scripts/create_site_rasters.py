import json
import math

import geopandas
import shapely
from raster import create_rasters

sites_file = "data/sites/sites.geo.json"
sites_gdf = geopandas.read_file(sites_file).set_index("site")

for site, feature in sites_gdf.iterrows():
    # Create file names
    input_file = f"data/sites/lidar/{site}.copc.laz"
    dem_output_file = f"data/sites/raster/{site}_dem.tif"
    dsm_output_file = f"data/sites/raster/{site}_dsm.tif"
    chm_output_file = f"data/sites/raster/{site}_chm.tif"
    pulse_density_output_file = f"data/sites/raster/{site}_pulse_density.tif"
    point_density_output_file = f"data/sites/raster/{site}_point_density.tif"
    scan_angle_output_file = f"data/sites/raster/{site}_scan_angle.tif"

    # Create bounds str
    bounds = shapely.bounds(feature.geometry)
    bounds_bbox = {
        "minx": math.floor(bounds[0]),
        "miny": math.floor(bounds[1]),
        "maxx": math.ceil(bounds[2]),
        "maxy": math.ceil(bounds[3]),
    }
    bounds_str = json.dumps(bounds_bbox)

    # Create rasters
    print(f"Creating rasters for {site}")
    create_rasters(
        input_file,
        dem_output_file=dem_output_file,
        dsm_output_file=dsm_output_file,
        chm_output_file=chm_output_file,
        pulse_density_output_file=pulse_density_output_file,
        point_density_output_file=point_density_output_file,
        scan_angle_output_file=scan_angle_output_file,
        bounds=bounds_str,
    )
