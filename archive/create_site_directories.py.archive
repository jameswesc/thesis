"""
CLI script for processing lidar files and GeoJSON plots with PDAL.

This script:
1. Creates output directory structure for each lidar site
2. Reprojects and processes lidar files using PDAL
3. Filters and saves site-specific plot GeoJSON files
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict

import click
import pdal  # pyright: ignore[reportMissingImports]


def load_geojson(file_path: Path) -> Dict[str, Any]:
    """Load and parse a GeoJSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def save_geojson(data: Dict[str, Any], file_path: Path) -> None:
    """Save GeoJSON data to file."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def get_lidar_files(lidar_dir: Path) -> Dict[str, Path]:
    """
    Get all .laz files from lidar directory.

    Returns:
        Dict mapping site names to file paths
    """
    lidar_files = {}

    for file_path in lidar_dir.glob("*.laz"):
        # Extract site name from filename (everything before .laz)
        site_name = file_path.stem
        lidar_files[site_name] = file_path

    return lidar_files


def filter_plots_by_site(
    geojson_data: Dict[str, Any], site_name: str
) -> Dict[str, Any]:
    """
    Filter GeoJSON features to only include plots for the specified site.

    Args:
        geojson_data: Complete GeoJSON data
        site_name: Site name to filter by

    Returns:
        New GeoJSON dict with only matching plots
    """
    filtered_features = []

    for feature in geojson_data.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("site") == site_name:
            filtered_features.append(feature)

    # Create new GeoJSON with filtered features
    filtered_geojson = {
        "type": "FeatureCollection",
        "name": f"plots_{site_name}_MGA2020",
        "features": filtered_features,
    }

    # Copy CRS if it exists
    if "crs" in geojson_data:
        filtered_geojson["crs"] = geojson_data["crs"]

    return filtered_geojson


def create_pdal_pipeline(input_file: Path, output_file: Path) -> str:
    """
    Create PDAL pipeline for processing lidar data.

    Pipeline steps:
    1. Read input LAZ file
    2. Reproject to EPSG:7855 (MGA 2020 Zone 55) if needed
    3. Remove noise points (classification 7)
    4. Compute height above ground using nearest neighbour filter
    5. Write as COPC LAZ

    Args:
        input_file: Path to input LAZ file
        output_file: Path to output COPC LAZ file

    Returns:
        PDAL pipeline configuration as a JSON string
    """
    pipeline = [
        # Read input file
        {"type": "readers.las", "filename": str(input_file)},
        # Reproject to EPSG:7855 (MGA 2020 Zone 55) - auto-detect input CRS
        {
            "type": "filters.reprojection",
            "out_srs": "EPSG:7855",
        },
        #  ----- THIS MAY GET REMOVED ----
        #
        #  Check for statistical outliers. This might be better done after filtering of
        # noise that has already been identified by virtual las
        {
            "type": "filters.outlier",
            "method": "statistical",
            "mean_k": 8,
            "multiplier": 5,
            # Don't use points already classified as noise
            "where": "Classification != 18",
        },
        # # Compute height above ground using classified ground points
        # # Uses default settings
        {
            "type": "filters.hag_nn",
            "allow_extrapolation": False,
            "count": 1,
        },
        # ---- END MAY GET REMOVED ----
        #
        # Write as COPC LAZ with better compression settings
        {
            "type": "writers.copc",
            "filename": str(output_file),
            "extra_dims": "HeightAboveGround=float32",
            "forward": "header,scale,offset",
        },
    ]

    return json.dumps(pipeline)


def process_lidar_file(input_file: Path, output_file: Path) -> int:
    """
    Process a single lidar file through the PDAL pipeline.

    Args:
        input_file: Path to input LAZ file
        output_file: Path to output COPC LAZ file

    Returns:
        Number of points processed
    """
    pipeline_config = create_pdal_pipeline(input_file, output_file)

    # Create and execute pipeline
    pipeline = pdal.Pipeline(pipeline_config)
    point_count = pipeline.execute()

    return point_count


def geojson_polygon_to_wkt(coordinates: list) -> str:
    """
    Convert GeoJSON polygon coordinates to WKT format.

    Args:
        coordinates: GeoJSON polygon coordinates (array of linear rings)

    Returns:
        WKT polygon string
    """
    # GeoJSON polygon coordinates are an array of linear rings
    # Each linear ring is an array of [x, y] coordinate pairs
    # The first ring is the exterior ring, subsequent rings are holes

    rings = []
    for ring in coordinates:
        # Convert coordinate pairs to "x y" format
        coord_pairs = [f"{coord[0]} {coord[1]}" for coord in ring]
        ring_wkt = "(" + ", ".join(coord_pairs) + ")"
        rings.append(ring_wkt)

    # Format as WKT POLYGON
    if len(rings) == 1:
        # Simple polygon with no holes
        return f"POLYGON({rings[0]})"
    else:
        # Polygon with holes
        return f"POLYGON({', '.join(rings)})"


def create_plot_crop_pipeline(
    input_file: Path, output_file: Path, polygon_wkt: str
) -> str:
    """
    Create PDAL pipeline for cropping lidar data to a specific plot polygon.

    Args:
        input_file: Path to input COPC LAZ file
        output_file: Path to output cropped COPC LAZ file
        polygon_wkt: WKT polygon string for cropping

    Returns:
        PDAL pipeline configuration as a JSON string
    """
    pipeline = [
        # Read input file
        {"type": "readers.las", "filename": str(input_file)},
        # Crop to polygon
        {"type": "filters.crop", "polygon": polygon_wkt},
        # Write as COPC LAZ
        {
            "type": "writers.copc",
            "filename": str(output_file),
            "extra_dims": "HeightAboveGround=float32",
            "forward": "header,scale,offset",
        },
        # Also write to .laz version 1.2 so I can easily
        # load it into deck.gl
        {
            "type": "writers.las",
            "filename": str(output_file).replace(".copc.laz", "_1.2.laz"),
            "extra_dims": "HeightAboveGround=float32,Infrared=uint16",
            "forward": "header,scale,offset",
            "dataformat_id": 2,  # Includes RGB
            "minor_version": 2,
        },
    ]

    return json.dumps(pipeline)


def crop_plot_from_lidar(
    site_lidar_file: Path, output_file: Path, plot_geometry: Dict[str, Any]
) -> int:
    """
    Crop a single plot from the site lidar file.

    Args:
        site_lidar_file: Path to processed site COPC LAZ file
        output_file: Path to output plot COPC LAZ file
        plot_geometry: GeoJSON geometry dict for the plot

    Returns:
        Number of points in the cropped plot
    """
    # Convert GeoJSON polygon to WKT
    if plot_geometry["type"] != "Polygon":
        raise ValueError(f"Unsupported geometry type: {plot_geometry['type']}")

    polygon_wkt = geojson_polygon_to_wkt(plot_geometry["coordinates"])

    # Create and execute crop pipeline
    pipeline_config = create_plot_crop_pipeline(
        site_lidar_file, output_file, polygon_wkt
    )
    pipeline = pdal.Pipeline(pipeline_config)
    point_count = pipeline.execute()

    return point_count


@click.command()
@click.option(
    "--lidar-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory containing lidar files with naming pattern [SITE].laz",
)
@click.option(
    "--plots",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="GeoJSON file containing plot data",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Output directory (must not exist)",
)
@click.option(
    "--max-sites",
    type=int,
    help="Maximum number of sites to process (if not provided, all sites will be processed)",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing output directory and files without confirmation",
)
@click.option(
    "--clip-plots",
    is_flag=True,
    help="Create individual LAZ files for each plot by cropping the site lidar data",
)
def main(
    lidar_directory: Path,
    plots: Path,
    output_dir: Path,
    max_sites: int,
    overwrite: bool,
    clip_plots: bool,
):
    """
    Process lidar files and create site-specific directories with plots.

    For each lidar file [SITE].laz in lidar_directory:
    1. Create output_dir/[SITE] directory
    2. Reproject and process lidar file as [SITE]_MGA2020.copc.laz using PDAL
    3. Create [SITE]_plots_MGA2020.geojson with site-specific plots
    """

    # Check that output directory doesn't exist unless overwriting
    if output_dir.exists() and not overwrite:
        click.echo(f"Error: Output directory '{output_dir}' already exists.", err=True)
        click.echo("Use --overwrite to overwrite existing directory.", err=True)
        raise click.Abort()
    elif output_dir.exists() and overwrite:
        click.echo(f"Overwriting existing directory: {output_dir}")
        shutil.rmtree(output_dir)

    # Load the plots GeoJSON
    try:
        plots_data = load_geojson(plots)
    except Exception as e:
        click.echo(f"Error loading plots file: {e}", err=True)
        raise click.Abort()

    # Get all lidar files
    lidar_files = get_lidar_files(lidar_directory)

    if not lidar_files:
        click.echo(f"No .laz files found in {lidar_directory}", err=True)
        raise click.Abort()

    # Limit to max_sites if specified
    if max_sites is not None and max_sites > 0 and max_sites < len(lidar_files):
        # Take first max_sites files (could be randomized if needed)
        items = list(lidar_files.items())[:max_sites]
        lidar_files = dict(items)
        click.echo(f"Limited to first {max_sites} sites")

    click.echo(f"Found {len(lidar_files)} lidar files")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each lidar file
    total_points = 0
    processed_files = 0

    for i, (site_name, lidar_file) in enumerate(lidar_files.items(), 1):
        click.echo(f"\n[{i}/{len(lidar_files)}] Processing site: {site_name}")

        # Create site directory
        site_dir = output_dir / site_name
        site_dir.mkdir(exist_ok=True)

        # Process lidar file with PDAL and save as COPC LAZ
        new_lidar_name = f"{site_name}_MGA2020.copc.laz"
        new_lidar_path = site_dir / new_lidar_name

        try:
            click.echo(f"  Processing {lidar_file.name} -> {new_lidar_name}")
            point_count = process_lidar_file(lidar_file, new_lidar_path)
            click.echo(f"  ✓ Processed {point_count:,} points")
            total_points += point_count
            processed_files += 1
        except Exception as e:
            click.echo(f"  ✗ Error processing lidar file: {e}", err=True)
            import traceback

            click.echo(f"  Full traceback:\n{traceback.format_exc()}", err=True)
            continue

        # Filter plots for this site
        site_plots = filter_plots_by_site(plots_data, site_name)

        # Save site-specific plots GeoJSON
        plots_file = site_dir / f"{site_name}_plots_MGA2020.geojson"
        save_geojson(site_plots, plots_file)

        plot_count = len(site_plots["features"])
        click.echo(
            f"  Created {site_name}_plots_MGA2020.geojson with {plot_count} plots"
        )

        # Clip individual plots if requested
        if clip_plots:
            click.echo(f"  Clipping {plot_count} individual plots...")
            clipped_plots = 0
            total_plot_points = 0

            for plot_feature in site_plots["features"]:
                plot_properties = plot_feature.get("properties", {})
                plot_number = plot_properties.get("plot_number")
                plot_geometry = plot_feature.get("geometry")

                if not plot_number or not plot_geometry:
                    click.echo(
                        "    ✗ Skipping plot with missing number or geometry", err=True
                    )
                    continue

                # Create output filename for plot
                plot_output_file = (
                    site_dir / f"{site_name}_plot{plot_number}_MGA2020.copc.laz"
                )

                try:
                    plot_points = crop_plot_from_lidar(
                        new_lidar_path, plot_output_file, plot_geometry
                    )
                    if plot_points > 0:
                        click.echo(f"    ✓ Plot {plot_number}: {plot_points:,} points")
                        clipped_plots += 1
                        total_plot_points += plot_points
                    else:
                        click.echo(
                            f"    ⚠ Plot {plot_number}: 0 points (no data in plot area)"
                        )
                        # Remove empty file if created
                        if plot_output_file.exists():
                            plot_output_file.unlink()

                except Exception as e:
                    click.echo(f"    ✗ Plot {plot_number}: Error - {e}", err=True)
                    # Remove partial file if created
                    if plot_output_file.exists():
                        plot_output_file.unlink()

            click.echo(
                f"  ✓ Successfully clipped {clipped_plots}/{plot_count} plots ({total_plot_points:,} total points)"
            )

    click.echo(f"\n{'=' * 50}")
    click.echo("Processing complete!")
    click.echo(f"Successfully processed: {processed_files}/{len(lidar_files)} files")
    click.echo(f"Total points processed: {total_points:,}")
    click.echo(f"Created {len(lidar_files)} site directories in {output_dir}")

    if processed_files < len(lidar_files):
        failed_count = len(lidar_files) - processed_files
        click.echo(f"Failed to process: {failed_count} files", err=True)


if __name__ == "__main__":
    main()
