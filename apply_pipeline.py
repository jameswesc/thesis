"""
Apply Pipeline

This is a CLI tool for applying PDAL pipelines.

It takes the following arguments

    --pipeline <PATH_TO_PIPELINE_JSON> (required)

    Pipeline is a JSON file with variables marked with {{ }}
    e.g. "filename": "{{ site }}.laz" Variables are replaced
    by values in the current context.

    --global-context <PATH_TO_CONTEXT_JSON> (optional)

    A JSON representing values that will be in the context
    for every execution of a pipeline.

    --loop <PATH_TO_LOOP_JSON> (optional)

    Must be a JSON with a top level array. Each item should
    have the same keys. If provided, the pipeline will be applied
    once for each item in the loop. The context for that iteration
    will be a combination of the global context and values from
    the current loop item.

    --loop-max-iter <int> (optional)

    Maximum number of iterations to perform. Has no effect if --loop
    is not provided.

    --dry-run <boolean> (optional) default=FALSE

    When provided, the CLI will not execute each pipeline. Instead it
    will print the pipeline out after variables have been replaced.

    The below code was mostly generated with Zed Claude Sonnet 4 using
    the above info and the following prompts

    Prompt 1:

    Implement the apply_pipeline.py script. The functionality of the script
    is outlined in [@apply_pipeline.py](@file:thesis/apply_pipeline.py. An
    older version of a similar CLI is in [@apply_pipeline.py.archive]
    (@file:thesis/archive/apply_pipeline.py.archive)

    In this version I want to create a context object for each iteration
    (or single if loop isn't specified) of the pipeline. The pipeline json
    should have its variables replaced using str.format . If variables are
    missing the program should fail and the user should be warned.

    An example pipeline can be seen at [@preprocess_sites.jsonc]
    (@file:thesis/pipelines/preprocess_sites.jsonc) and an example
    global context can be seen [@context.jsonc](@file:thesis/context.jsonc)

    Use jsonc library to read the json files as I'm allowing .jsonc files

    Prompt 2:

    To fix the json with comments issue just use the jsonc in place of where
    you would use the json library.

    Prompt 3:

    Alright, I'm still having some errors with apply_pipeline. i've installed
    Jinja2. Can you update it to use that for replacing the pipeline JSONs. I've
    also updated [@preprocess_sites.jsonc](@file:thesis/pipelines/preprocess_sites.jsonc)
    to use the Jinja2 format. Still use jsonc when loading in the original json
    as i have normal comments in there

"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import click
import jsonc
import pdal
from jinja2 import (
    BaseLoader,
    Environment,
    StrictUndefined,
    TemplateError,
    UndefinedError,
)


def load_jsonc_file(file_path: Path) -> Union[Dict[str, Any], List[Any]]:
    """Load a JSON/JSONC file."""
    try:
        with open(file_path, "r") as f:
            return jsonc.load(f)
    except Exception as e:
        raise click.ClickException(f"Error loading {file_path}: {e}")


def format_pipeline_with_context(
    pipeline: List[Dict[str, Any]], context: Dict[str, Any]
) -> str:
    """
    Replace variables in pipeline using Jinja2 with the provided context.

    Args:
        pipeline: PDAL pipeline configuration
        context: Context dictionary for variable replacement

    Returns:
        Pipeline string with variables replaced

    Raises:
        ClickException: If a required variable is missing from context or template error occurs
    """
    try:
        # Convert pipeline to JSON string
        pipeline_str = jsonc.dumps(pipeline, indent=2)

        # Create Jinja2 environment with strict undefined behavior
        env = Environment(loader=BaseLoader(), undefined=StrictUndefined)
        template = env.from_string(pipeline_str)

        # Render template with context
        formatted_str = template.render(**context)

        return formatted_str

    except UndefinedError as e:
        raise click.ClickException(
            f"Missing variable in template: {e}. "
            f"Available variables: {', '.join(sorted(context.keys()))}"
        )
    except TemplateError as e:
        raise click.ClickException(f"Template error: {e}")
    except Exception as e:
        raise click.ClickException(f"Error formatting pipeline: {e}")


def execute_pipeline(
    pipeline: List[Dict[str, Any]], context: Dict[str, Any], dry_run: bool = False
) -> int:
    """
    Execute a PDAL pipeline with the given context.

    Args:
        pipeline: PDAL pipeline configuration
        context: Context for variable replacement
        dry_run: If True, print pipeline instead of executing

    Returns:
        Number of points processed (0 for dry run)
    """
    # Format pipeline with context
    pipeline_config = format_pipeline_with_context(pipeline, context)

    if dry_run:
        click.echo("Pipeline JSON:")
        click.echo(pipeline_config)
        click.echo()
        return 0

    try:
        pdal_pipeline = pdal.Pipeline(pipeline_config)
        point_count = pdal_pipeline.execute()
        return point_count
    except Exception as e:
        raise click.ClickException(f"Error executing PDAL pipeline: {e}")


@click.command()
@click.option(
    "--pipeline",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="JSON file containing PDAL pipeline configuration with variables marked with {{ }}",
)
@click.option(
    "--global-context",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="JSON file containing global context values for variable replacement",
)
@click.option(
    "--loop",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="JSON file containing array of loop items. Pipeline will be executed once per item.",
)
@click.option(
    "--loop-max-iter",
    type=int,
    help="Maximum number of loop iterations to perform",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print the processed pipeline JSON without executing it",
)
def main(
    pipeline: Path,
    global_context: Optional[Path],
    loop: Optional[Path],
    loop_max_iter: Optional[int],
    dry_run: bool,
):
    """
    Apply a PDAL pipeline with context-based variable replacement.

    The pipeline JSON file can contain variables marked with double curly braces {{ }}
    which will be replaced using Jinja2 templating. For example:

    "filename": "{{ data_dir }}/{{ site }}.laz"

    Variables are replaced from the context, which is a combination of:
    1. Global context (if --global-context is provided)
    2. Current loop item (if --loop is provided)

    If --loop is provided, the pipeline will be executed once for each item
    in the loop array. Each loop item should be a dictionary with the same keys.

    Use --dry-run to see the processed pipeline JSON without executing it.
    """

    # Load pipeline configuration
    click.echo(f"Loading pipeline from {pipeline}")
    pipeline_config = load_jsonc_file(pipeline)

    if not isinstance(pipeline_config, list):
        raise click.ClickException("Pipeline must be a JSON array")

    # Load global context
    global_ctx = {}
    if global_context:
        click.echo(f"Loading global context from {global_context}")
        global_ctx_data = load_jsonc_file(global_context)
        if not isinstance(global_ctx_data, dict):
            raise click.ClickException("Global context must be a JSON object")
        global_ctx = global_ctx_data

    # Load loop data
    loop_items = []
    if loop:
        click.echo(f"Loading loop data from {loop}")
        loop_data = load_jsonc_file(loop)
        if not isinstance(loop_data, list):
            raise click.ClickException("Loop data must be a JSON array")
        loop_items = loop_data

        # Apply max iterations limit
        if loop_max_iter is not None and loop_max_iter > 0:
            if loop_max_iter < len(loop_items):
                click.echo(
                    f"Limiting to {loop_max_iter} iterations (out of {len(loop_items)} total)"
                )
                loop_items = loop_items[:loop_max_iter]

    # If no loop provided, create a single empty loop item
    if not loop_items:
        loop_items = [{}]

    # Display execution plan
    click.echo(f"Pipeline: {pipeline.name}")
    if global_context:
        click.echo(f"Global context: {global_context.name}")
        click.echo(f"  Variables: {', '.join(sorted(global_ctx.keys()))}")
    if loop:
        click.echo(f"Loop: {loop.name}")
        click.echo(f"  Iterations: {len(loop_items)}")
        if loop_items:
            # Show variables from first loop item
            first_item_vars = (
                list(loop_items[0].keys()) if isinstance(loop_items[0], dict) else []
            )
            if first_item_vars:
                click.echo(f"  Loop variables: {', '.join(sorted(first_item_vars))}")

    if dry_run:
        click.echo("DRY RUN MODE - Pipeline will not be executed")

    click.echo()

    # Execute pipeline for each loop iteration
    click.echo(f"Starting sequential execution of {len(loop_items)} iterations...")
    start_time = time.time()
    
    total_points = 0
    successful_iterations = 0
    failed_iterations = []

    for i, loop_item in enumerate(loop_items, 1):
        click.echo(f"[{i}/{len(loop_items)}] Processing iteration {i}")

        # Validate loop item
        if not isinstance(loop_item, dict):
            click.echo(f"  ✗ Error: Loop item {i} is not a dictionary", err=True)
            failed_iterations.append(i)
            continue

        # Combine global context with current loop item
        # Loop item variables override global context variables
        current_context = {**global_ctx, **loop_item}

        if current_context:
            click.echo(
                f"  Context variables: {', '.join(sorted(current_context.keys()))}"
            )

        try:
            point_count = execute_pipeline(pipeline_config, current_context, dry_run)

            if not dry_run:
                click.echo(f"  ✓ Processed {point_count:,} points")
                total_points += point_count
            else:
                click.echo("  ✓ Pipeline formatted successfully")

            successful_iterations += 1

        except Exception as e:
            click.echo(f"  ✗ Error: {e}", err=True)
            failed_iterations.append(i)
            continue

    end_time = time.time()
    execution_time = end_time - start_time

    # Summary
    click.echo(f"\n{'=' * 60}")
    click.echo("EXECUTION SUMMARY")
    click.echo(f"{'=' * 60}")
    
    if dry_run:
        click.echo("Dry run complete!")
        click.echo(
            f"Successfully formatted: {successful_iterations}/{len(loop_items)} iterations"
        )
    else:
        click.echo("Pipeline execution complete!")
        click.echo(
            f"Successfully processed: {successful_iterations}/{len(loop_items)} iterations"
        )
        click.echo(f"Total points processed: {total_points:,}")

    click.echo(f"Execution time: {execution_time:.2f} seconds")
    
    if len(loop_items) > 1:
        avg_time_per_iteration = execution_time / len(loop_items)
        click.echo(f"Average time per iteration: {avg_time_per_iteration:.2f} seconds")

    if failed_iterations:
        click.echo(f"Failed iterations: {len(failed_iterations)}")
        for iteration in failed_iterations:
            click.echo(f"  - Iteration {iteration}")

        # Exit with error code if any iterations failed
        sys.exit(1)

    click.echo("All iterations completed successfully!")


if __name__ == "__main__":
    main()
