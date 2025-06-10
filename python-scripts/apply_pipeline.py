"""
CLI script for applying PDAL pipelines to site directories.

This script:
1. Loops through site directories
2. Loads a PDAL pipeline from JSON file
3. Replaces placeholders with actual values
4. Executes the pipeline for each site (and plot if required)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import jsonc
import pdal  # pyright: ignore[reportMissingImports]
from shapely.geometry import shape


def load_pipeline_json(pipeline_file: Path) -> List[Dict[str, Any]]:
    """Load PDAL pipeline from JSON file."""
    with open(pipeline_file, "r") as f:
        return jsonc.load(f)


def load_plots_geojson(plots_file: Path) -> Dict[str, Any]:
    """Load plots GeoJSON file."""
    with open(plots_file, "r") as f:
        return jsonc.load(f)


def get_site_directories(sites_dir: Path) -> List[str]:
    """
    Get all site directories from the sites directory.

    Returns:
        List of site directory names
    """
    site_dirs = []

    for item in sites_dir.iterdir():
        if item.is_dir():
            site_dirs.append(item.name)

    return sorted(site_dirs)


def requires_plot_processing(pipeline: List[Dict[str, Any]]) -> bool:
    """
    Check if pipeline requires plot-level processing by looking for PLOT_NUMBER or PLOT_WKT placeholders.

    Args:
        pipeline: PDAL pipeline configuration

    Returns:
        True if plot-level processing is required
    """
    pipeline_str = jsonc.dumps(pipeline)
    return "<PLOT_NUMBER>" in pipeline_str or "<PLOT_WKT>" in pipeline_str


def replace_site_placeholders(
    pipeline: List[Dict[str, Any]], base_dir: str, site_name: str
) -> List[Dict[str, Any]]:
    """
    Replace <BASE_DIR> and <SITE> placeholders in pipeline with actual paths.

    Args:
        pipeline: PDAL pipeline configuration
        base_dir: Base directory path (e.g., "../sites-v2")
        site_name: Site name (e.g., "AGG_O_01")

    Returns:
        Modified pipeline with placeholders replaced
    """
    # Convert to JSON string, replace placeholders, then parse back
    pipeline_str = jsonc.dumps(pipeline)
    pipeline_str = pipeline_str.replace("<BASE_DIR>", base_dir)
    pipeline_str = pipeline_str.replace("<SITE>", site_name)
    return jsonc.loads(pipeline_str)


def replace_plot_placeholders(
    pipeline: List[Dict[str, Any]], plot_number: int, plot_wkt: str
) -> List[Dict[str, Any]]:
    """
    Replace <PLOT_NUMBER> and <PLOT_WKT> placeholders in pipeline.

    Args:
        pipeline: PDAL pipeline configuration
        plot_number: Plot number
        plot_wkt: Plot geometry as WKT string

    Returns:
        Modified pipeline with plot placeholders replaced
    """
    pipeline_str = jsonc.dumps(pipeline)
    pipeline_str = pipeline_str.replace("<PLOT_NUMBER>", str(plot_number))
    pipeline_str = pipeline_str.replace("<PLOT_WKT>", plot_wkt)
    return jsonc.loads(pipeline_str)


def geometry_to_wkt(geometry: Dict[str, Any]) -> str:
    """
    Convert GeoJSON geometry to WKT string.

    Args:
        geometry: GeoJSON geometry dictionary

    Returns:
        WKT string representation
    """
    geom = shape(geometry)
    return geom.wkt


def execute_pipeline_for_plot(
    pipeline: List[Dict[str, Any]],
    site_name: str,
    plot_number: int,
    plot_wkt: str,
    dry_run: bool = False,
) -> int:
    """
    Execute PDAL pipeline for a specific plot.

    Args:
        pipeline: PDAL pipeline configuration (already has site placeholders replaced)
        site_name: Name of the site
        plot_number: Plot number
        plot_wkt: Plot geometry as WKT string
        dry_run: If True, print pipeline without executing

    Returns:
        Number of points processed (0 for dry run)
    """
    modified_pipeline = replace_plot_placeholders(pipeline, plot_number, plot_wkt)

    # Convert back to JSON string for PDAL
    pipeline_config = jsonc.dumps(modified_pipeline, indent=2)

    if dry_run:
        click.echo(f"    Pipeline JSON for {site_name} plot {plot_number}:")
        click.echo(pipeline_config)
        return 0

    # Create and execute pipeline
    pdal_pipeline = pdal.Pipeline(pipeline_config)
    point_count = pdal_pipeline.execute()

    return point_count


def execute_pipeline_for_site(
    pipeline: List[Dict[str, Any]],
    site_name: str,
    base_dir: Path,
    plot_path_template: str,
    dry_run: bool = False,
) -> int:
    """
    Execute PDAL pipeline for a specific site.

    Args:
        pipeline: PDAL pipeline configuration
        site_name: Name of the site
        base_dir: Base directory containing site directories
        plot_path_template: Template path for plot GeoJSON files
        dry_run: If True, print pipeline without executing

    Returns:
        Number of points processed (0 for dry run)
    """
    base_dir_str = str(base_dir)
    site_pipeline = replace_site_placeholders(pipeline, base_dir_str, site_name)

    # Check if plot-level processing is required
    if requires_plot_processing(site_pipeline):
        # Replace placeholders in plot path template
        plot_path_str = plot_path_template.replace("<BASE_DIR>", base_dir_str)
        plot_path_str = plot_path_str.replace("<SITE>", site_name)
        plot_path = Path(plot_path_str)

        if not plot_path.exists():
            raise FileNotFoundError(f"Plot file not found: {plot_path}")

        # Load plots GeoJSON
        plots_data = load_plots_geojson(plot_path)

        if "features" not in plots_data:
            raise ValueError(f"Invalid GeoJSON: no features found in {plot_path}")

        # Process each plot
        total_points = 0
        processed_plots = 0

        for feature in plots_data["features"]:
            if (
                "properties" not in feature
                or "plot_number" not in feature["properties"]
            ):
                click.echo("    Warning: Skipping feature without plot_number property")
                continue

            plot_number = feature["properties"]["plot_number"]
            plot_wkt = geometry_to_wkt(feature["geometry"])

            click.echo(f"    Processing plot {plot_number}")

            try:
                point_count = execute_pipeline_for_plot(
                    site_pipeline, site_name, plot_number, plot_wkt, dry_run
                )
                if not dry_run:
                    click.echo(f"      ✓ Processed {point_count:,} points")
                    total_points += point_count
                processed_plots += 1
            except Exception as e:
                click.echo(
                    f"      ✗ Error processing plot {plot_number}: {e}", err=True
                )
                continue

        click.echo(
            f"    Processed {processed_plots}/{len(plots_data['features'])} plots"
        )
        return total_points
    else:
        # Site-level processing only
        # Convert back to JSON string for PDAL
        pipeline_config = jsonc.dumps(site_pipeline, indent=2)

        if dry_run:
            click.echo(f"  Pipeline JSON for {site_name}:")
            click.echo(pipeline_config)
            return 0

        # Create and execute pipeline
        pdal_pipeline = pdal.Pipeline(pipeline_config)
        point_count = pdal_pipeline.execute()

        return point_count


@click.command()
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Base directory containing site subdirectories",
)
@click.option(
    "--pipeline",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="JSON file containing PDAL pipeline configuration",
)
@click.option(
    "--plot-path",
    type=str,
    default="<BASE_DIR>/<SITE>/<SITE>_plots_MGA2020.geojson",
    help="Template path for plot GeoJSON files (supports <BASE_DIR> and <SITE> placeholders)",
)
@click.option(
    "--max-sites",
    type=int,
    help="Maximum number of sites to process (if not provided, all sites will be processed)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print the processed pipeline JSON without executing it",
)
def main(
    base_dir: Path,
    pipeline: Path,
    plot_path: str,
    max_sites: Optional[int],
    dry_run: bool,
):
    """
    Apply a PDAL pipeline to all sites in a directory.

    The pipeline JSON file can use placeholders which will be replaced during processing:
    - <BASE_DIR>: Base directory path
    - <SITE>: Site name
    - <PLOT_NUMBER>: Plot number (triggers plot-level processing)
    - <PLOT_WKT>: Plot geometry as WKT (triggers plot-level processing)

    Example: If pipeline contains "filename": "<BASE_DIR>/<SITE>/<SITE>_MGA2020.copc.laz"
    and base_dir is "../sites" and site is "AGG_O_01", it becomes
    "filename": "../sites/AGG_O_01/AGG_O_01_MGA2020.copc.laz"

    If <PLOT_NUMBER> or <PLOT_WKT> placeholders are found, the pipeline will be executed
    for each plot in the site's GeoJSON file.

    Use --dry-run to see the processed pipeline JSON without executing it.
    """

    # Load pipeline configuration
    try:
        pipeline_config = load_pipeline_json(pipeline)
        click.echo(f"Loaded pipeline from {pipeline}")
    except Exception as e:
        click.echo(f"Error loading pipeline file: {e}", err=True)
        raise click.Abort()

    # Check if plot-level processing is required
    plot_processing = requires_plot_processing(pipeline_config)
    if plot_processing:
        click.echo(
            "Plot-level processing detected (found <PLOT_NUMBER> or <PLOT_WKT> placeholders)"
        )
        click.echo(f"Plot path template: {plot_path}")

    # Get all site directories
    site_dirs = get_site_directories(base_dir)

    if not site_dirs:
        click.echo(f"No site directories found in {base_dir}", err=True)
        raise click.Abort()

    # Limit to max_sites if specified
    if max_sites is not None and max_sites > 0 and max_sites < len(site_dirs):
        site_dirs = site_dirs[:max_sites]
        click.echo(f"Limited to first {max_sites} sites")

    click.echo(f"Found {len(site_dirs)} site directories")
    click.echo(f"Pipeline: {pipeline.name}")

    if dry_run:
        click.echo("DRY RUN MODE - Pipeline will not be executed")

    # Process each site
    total_points = 0
    processed_sites = 0
    failed_sites = []

    for i, site_name in enumerate(site_dirs, 1):
        click.echo(f"\n[{i}/{len(site_dirs)}] Processing site: {site_name}")

        try:
            point_count = execute_pipeline_for_site(
                pipeline_config, site_name, base_dir, plot_path, dry_run
            )
            if not dry_run:
                if plot_processing:
                    click.echo(f"  ✓ Site total: {point_count:,} points")
                else:
                    click.echo(f"  ✓ Processed {point_count:,} points")
                total_points += point_count
            processed_sites += 1
        except Exception as e:
            click.echo(f"  ✗ Error processing site: {e}", err=True)
            import traceback

            click.echo(f"  Full traceback:\n{traceback.format_exc()}", err=True)
            failed_sites.append(site_name)
            continue

    # Summary
    click.echo(f"\n{'=' * 50}")
    if dry_run:
        click.echo("Dry run complete!")
        if plot_processing:
            click.echo(
                f"Pipeline JSON shown for plots in: {processed_sites}/{len(site_dirs)} sites"
            )
        else:
            click.echo(
                f"Pipeline JSON shown for: {processed_sites}/{len(site_dirs)} sites"
            )
    else:
        click.echo("Pipeline execution complete!")
        click.echo(f"Successfully processed: {processed_sites}/{len(site_dirs)} sites")
        click.echo(f"Total points processed: {total_points:,}")

    if failed_sites:
        click.echo(f"Failed sites: {len(failed_sites)}")
        for site in failed_sites:
            click.echo(f"  - {site}")


if __name__ == "__main__":
    main()
