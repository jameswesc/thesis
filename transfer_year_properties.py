#!/usr/bin/env python3
"""
Script to transfer year and year_known properties from sites.geo.json to plots.geo.json
with special handling for AGG sites and agg_retained property.
"""

import json
import sys
from pathlib import Path


def load_geojson(filepath):
    """Load a GeoJSON file and return its contents."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_geojson(data, filepath):
    """Save data to a GeoJSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def update_agg_retained(plots_data):
    """
    Update agg_retained property in plots data:
    - For site_type == AGG: true if currently true, false otherwise
    - For site_type != AGG: null
    """
    for feature in plots_data["features"]:
        props = feature["properties"]
        site_type = props.get("site_type")

        if site_type == "AGG":
            # Keep true if already true, otherwise false
            current_value = props.get("agg_retained")
            if current_value is True:
                props["agg_retained"] = True
            else:
                props["agg_retained"] = False
        else:
            # Set to null for non-AGG sites
            props["agg_retained"] = None

    return plots_data


def create_site_lookup(sites_data):
    """Create a lookup dictionary for sites by their site name."""
    lookup = {}
    for feature in sites_data["features"]:
        site_name = feature["properties"].get("site")
        if site_name:
            lookup[site_name] = feature["properties"]
    return lookup


def transfer_year_properties(plots_data, sites_data):
    """
    Transfer year and year_known properties from sites to plots.
    Special handling for AGG sites with agg_retained=true.
    """
    # Create lookup for sites
    site_lookup = create_site_lookup(sites_data)

    # Process each plot
    for feature in plots_data["features"]:
        props = feature["properties"]
        site_name = props.get("site")

        # Find matching site
        if site_name and site_name in site_lookup:
            site_props = site_lookup[site_name]

            # Check if this is an AGG site with agg_retained=true
            if props.get("site_type") == "AGG" and props.get("agg_retained") is True:
                # Special case: set year to 1900 and year_known to false
                props["year"] = 1900
                props["year_known"] = False
            else:
                # Transfer as-is from sites data
                if "year" in site_props:
                    props["year"] = site_props["year"]
                if "year_known" in site_props:
                    props["year_known"] = site_props["year_known"]
        else:
            print(f"Warning: No matching site found for plot with site '{site_name}'")

    return plots_data


def main():
    """Main function to coordinate the data transfer."""
    # Define file paths
    base_dir = Path(__file__).parent
    plots_file = base_dir / "data" / "plots" / "plots.geo.json"
    sites_file = base_dir / "data" / "sites" / "sites.geo.json"

    # Check if files exist
    if not plots_file.exists():
        print(f"Error: {plots_file} not found")
        sys.exit(1)
    if not sites_file.exists():
        print(f"Error: {sites_file} not found")
        sys.exit(1)

    print(f"Loading plots from: {plots_file}")
    print(f"Loading sites from: {sites_file}")

    # Load data
    plots_data = load_geojson(plots_file)
    sites_data = load_geojson(sites_file)

    print(f"Loaded {len(plots_data['features'])} plots")
    print(f"Loaded {len(sites_data['features'])} sites")

    # Step 1: Update agg_retained property
    print("\nUpdating agg_retained property...")
    plots_data = update_agg_retained(plots_data)

    # Step 2: Transfer year properties
    print("Transferring year and year_known properties...")
    plots_data = transfer_year_properties(plots_data, sites_data)

    # Save updated plots data
    print(f"\nSaving updated plots to: {plots_file}")
    save_geojson(plots_data, plots_file)

    print("Done! Successfully updated plots.geo.json")

    # Print summary statistics
    agg_retained_count = sum(
        1 for f in plots_data["features"] if f["properties"].get("agg_retained") is True
    )
    year_count = sum(1 for f in plots_data["features"] if "year" in f["properties"])

    print("\nSummary:")
    print(f"- Plots with agg_retained=true: {agg_retained_count}")
    print(f"- Plots with year property: {year_count}")


if __name__ == "__main__":
    main()
