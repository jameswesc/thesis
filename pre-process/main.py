import os
import json
import pdal
import click
from shapely.geometry import shape
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon

@click.group()
def cli():
    """Pre-processing and merging tools for LAZ files."""
    pass

@cli.command()
@click.option('--input-dir', required=True, help='Input directory')
@click.option('--output-dir', required=True, help='Output directory')
def preprocess(input_dir, output_dir):
    """
    Pre process all laz files in input_dir and save them to output_dir.
    Pre-processing includes reprojecting to EPSG:7855 and normalising height.
    """
    pipeline_filters = [
        {
            "type": "filters.range",
            "limits": "Classification[0:5]"
        },
        {
            "type": "filters.reprojection",
            "out_srs": "EPSG:7855"
        },
        {
            "type": "filters.ferry",
            "dimensions": "Z => originalZ",
        },
        {
            "type": "filters.hag_nn",
        },
        {
            "type":"filters.ferry",
            "dimensions":"HeightAboveGround=>Z"
        },
    ]

    input_laz_files = [f for f in os.listdir(input_dir) if f.endswith(".laz") ]

    if not input_laz_files:
        print(f"No .laz files found in {input_dir}")
        return

    # Create output directory if it doesn't exist
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    print(f'Found {len(input_laz_files)} .laz files in {input_dir}')

    for i, laz_file in enumerate(input_laz_files):
        pipeline_config = [
            os.path.join(input_dir, laz_file),
            *pipeline_filters,
            {
                "type": "writers.copc",
                "filename": os.path.join(output_dir, laz_file.replace(".laz", ".copc.laz"))
            }
        ]
        print(f'Processing {i + 1} of {len(input_laz_files)}')
        pipeline = pdal.Pipeline(json.dumps(pipeline_config))
        count = pipeline.execute()
        print(f'\tFinished processing {laz_file} with {count} points.')



@cli.command()
@click.option('--input-dir', required=True, help='Input directory containing COPC LAZ files')
@click.option('--output-file', required=True, help='Output file path for the merged COPC LAZ file')
def merge(input_dir, output_file):
    """
    Merge all COPC LAZ files in input_dir into a single output file.
    Only works with COPC LAZ files.
    """
    # Find all COPC LAZ files in the input directory
    copc_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir)
                 if f.endswith(".copc.laz")]

    if not copc_files:
        print(f"No COPC LAZ files found in {input_dir}")
        return

    print(f'Found {len(copc_files)} COPC LAZ files in {input_dir}')

    # Create a PDAL pipeline to merge the files
    pipeline_config = [
        *copc_files,
        {
          "type": "filters.merge"
        },
        {
            "type": "writers.copc",
            "filename": output_file
        }
    ]

    print(f'Merging {len(copc_files)} files into {output_file}')
    pipeline = pdal.Pipeline(json.dumps(pipeline_config))
    count = pipeline.execute()
    print(f'Finished merging files. Output file contains {count} points.')

@cli.command()
@click.option('--input-file', required=True, help='Input COPC laz file')
@click.option('--output-dir', required=True, help='Output directory')
@click.option('--plots', required=True, help='GeoJSON containing plots')
def clip_plots(input_file, output_dir, plots):
    """
        Creates a new point cloud for each plot.
        Input file must be a height normalised COPC laz file.
        Plots must be a geojson of polygons.
        Does not check for CRS but they must be the same.
    """
    # Load the GeoJSON containing the plots
    with open(plots, 'r') as f:
        geojson_data = json.load(f)

    # Create output directory if it doesn't exist
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    features = geojson_data.get('features', [])
    print(f"Found {len(features)} plots in GeoJSON")

    # Process each plot polygon
    for idx, feature in enumerate(features):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})

        site = properties.get('site', 'unknown')
        plot_id = properties.get('plot_id', f'plot_{idx}')

        output_filename = f"{site}__{plot_id}.copc.laz"
        output_path = os.path.join(output_dir, output_filename)

        # Convert geometry to a shapely object
        shapely_geometry = shape(geometry)

        assert isinstance(shapely_geometry, Polygon) or isinstance(shapely_geometry, MultiPolygon)

        # If it's a MultiPolygon, extract the first polygon
        if isinstance(shapely_geometry, MultiPolygon):
            shapely_geometry = list(shapely_geometry.geoms)[0]

        # Ensure it's a Polygon
        if not isinstance(shapely_geometry, Polygon):
            raise ValueError(f"Geometry is not a Polygon or MultiPolygon: {shapely_geometry.geom_type}")

        # Convert to WKT string
        geometry_wkt = shapely_geometry.wkt

        # Create a pipeline to clip the point cloud using the polygon
        pipeline_config = [
            input_file,
            {
                "type": "filters.crop",
                "polygon": geometry_wkt
            },
            {
                "type": "writers.copc",
                "filename": output_path
            }
        ]

        print(f"Processing plot {idx+1}/{len(features)}: {site}__{plot_id}")
        try:
            pipeline = pdal.Pipeline(json.dumps(pipeline_config))
            count = pipeline.execute()
            if count > 0:
                print(f"\tClipped {count} points to {output_filename}")
            else:
                print(f"\tNo points found in plot {site}__{plot_id}")
        except Exception as e:
            print(f"\tError processing plot {site}__{plot_id}: {str(e)}")

    print("Finished processing all plots")

if __name__ == '__main__':
    cli()
