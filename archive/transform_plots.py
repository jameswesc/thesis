"""
Transform all_plots_MGA2020.geo.json to plots.json with filtered sites and WKT format.

Created by Zed Claude Sonnet 4 to do some basic data manipulaiton.
Prompt used:
Write a quick python script to transform [@all_plots_MGA2020.geo.json](@file:thesis/data/all_plots_MGA2020.geo.json) . The resulting fils should be a json file plots.json. Each item in that file should correspond to a plot feature. It should only contain plots where the site property is included in [@sites.json](@file:thesis/sites.json) .

Each item in the plots.json file should have the following fields:

- fid (as is)
- site (as is)
- plot_number (as is)
- site_type (as is)
- srs: "EPSG:7855"
- srs_file_suffix: "MGA2020"
- polygon_wkt: the polygon of the plot in well known text (WKT) format
- site_plot_id: `${site}_P`${plot_number}`
"""

import json
from typing import List


def coordinates_to_wkt(coordinates: List[List[List[float]]]) -> str:
    """Convert GeoJSON polygon coordinates to WKT format."""
    # GeoJSON polygon has one outer ring and potentially inner rings
    # For simplicity, we'll handle the outer ring (first element)
    outer_ring = coordinates[0]

    # Format coordinates as "x y" pairs
    coord_pairs = [f"{coord[0]} {coord[1]}" for coord in outer_ring]

    # WKT polygon format
    wkt = f"POLYGON(({', '.join(coord_pairs)}))"
    return wkt


def load_sites(sites_file: str) -> set:
    """Load the list of sites to include."""
    with open(sites_file, "r") as f:
        sites_data = json.load(f)

    return {site["site"] for site in sites_data}


def transform_geojson_to_plots(geojson_file: str, sites_file: str, output_file: str):
    """Transform GeoJSON to filtered plots JSON format."""

    # Load sites to include
    valid_sites = load_sites(sites_file)

    # Load GeoJSON data
    with open(geojson_file, "r") as f:
        geojson_data = json.load(f)

    plots = []

    # Process each feature
    for feature in geojson_data["features"]:
        properties = feature["properties"]
        site = properties["site"]

        # Only include plots from valid sites
        if site in valid_sites:
            # Extract geometry and convert to WKT
            geometry = feature["geometry"]
            polygon_wkt = coordinates_to_wkt(geometry["coordinates"])

            # Create plot record
            plot = {
                "fid": properties["fid"],
                "site": properties["site"],
                "plot_number": properties["plot_number"],
                "site_type": properties["site_type"],
                "polygon_wkt": polygon_wkt,
                "site_plot_id": f"{properties['site']}_P{properties['plot_number']}",
            }

            plots.append(plot)

    # Write output file
    with open(output_file, "w") as f:
        json.dump(plots, f, indent=2)

    print(
        f"Transformed {len(plots)} plots from {len(geojson_data['features'])} total features"
    )
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    transform_geojson_to_plots(
        "data/all_plots_MGA2020.geo.json", "sites.json", "plots.json"
    )
