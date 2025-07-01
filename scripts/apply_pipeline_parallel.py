"""
Apply Pipeline (Parallel Version)

This is a CLI tool for applying PDAL pipelines with parallel execution support.

This parallel version is based on the original apply_pipeline.py but adds support
for parallel execution of pipeline iterations using ProcessPoolExecutor.

It takes the following arguments:

    --pipeline <PATH_TO_PIPELINE_JSON> (required)

    Pipeline is a JSON file with variables marked with {{ }}
    e.g. "filename": "{{ site }}.laz" Variables are replaced
    by values in the current context using Jinja2 templating.

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

    --max-workers <int> (optional)

    Maximum number of parallel workers to use. Defaults to number of CPU cores.

    --dry-run <boolean> (optional) default=FALSE

    When provided, the CLI will not execute each pipeline. Instead it
    will print the pipeline out after variables have been replaced.

"""

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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


@dataclass
class ExecutionResult:
    """Result of a single pipeline execution."""

    iteration: int
    success: bool
    point_count: int
    error_message: Optional[str] = None
    context_vars: Optional[List[str]] = None


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
        raise Exception(
            f"Missing variable in template: {e}. "
            f"Available variables: {', '.join(sorted(context.keys()))}"
        )
    except TemplateError as e:
        raise Exception(f"Template error: {e}")
    except Exception as e:
        raise Exception(f"Error formatting pipeline: {e}")


def execute_pipeline_internal(
    pipeline: List[Dict[str, Any]], context: Dict[str, Any], dry_run: bool = False
) -> int:
    """
    Execute a PDAL pipeline with the given context.

    Args:
        pipeline: PDAL pipeline configuration
        context: Context for variable replacement
        dry_run: If True, return 0 instead of executing

    Returns:
        Number of points processed (0 for dry run)
    """
    # Format pipeline with context
    pipeline_config = format_pipeline_with_context(pipeline, context)

    if dry_run:
        return 0

    try:
        pdal_pipeline = pdal.Pipeline(pipeline_config)
        point_count = pdal_pipeline.execute()
        return point_count
    except Exception as e:
        raise Exception(f"Error executing PDAL pipeline: {e}")


def execute_single_iteration(
    args: Tuple[int, List[Dict[str, Any]], Dict[str, Any], bool],
) -> ExecutionResult:
    """
    Execute a single pipeline iteration. This function needs to be at module level
    for multiprocessing to work properly.

    Args:
        args: Tuple containing (iteration_number, pipeline_config, context, dry_run)

    Returns:
        ExecutionResult with success/failure information
    """
    iteration, pipeline_config, context, dry_run = args

    try:
        point_count = execute_pipeline_internal(pipeline_config, context, dry_run)
        return ExecutionResult(
            iteration=iteration,
            success=True,
            point_count=point_count,
            context_vars=list(context.keys()) if context else [],
        )
    except Exception as e:
        return ExecutionResult(
            iteration=iteration,
            success=False,
            point_count=0,
            error_message=str(e),
            context_vars=list(context.keys()) if context else [],
        )


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
    "--max-workers",
    type=int,
    default=None,
    help="Maximum number of parallel workers (default: number of CPU cores)",
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
    max_workers: Optional[int],
    dry_run: bool,
):
    """
    Apply a PDAL pipeline with context-based variable replacement (parallel version).

    The pipeline JSON file can contain variables marked with double curly braces {{ }}
    which will be replaced using Jinja2 templating. For example:

    "filename": "{{ data_dir }}/{{ site }}.laz"

    Variables are replaced from the context, which is a combination of:
    1. Global context (if --global-context is provided)
    2. Current loop item (if --loop is provided)

    If --loop is provided, the pipeline will be executed once for each item
    in the loop array. Each loop item should be a dictionary with the same keys.

    Use --dry-run to see the processed pipeline JSON without executing it.

    This parallel version executes multiple pipeline iterations concurrently
    using ProcessPoolExecutor for improved performance.
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

    # Display parallel execution info
    actual_max_workers = max_workers or os.cpu_count()
    if max_workers:
        click.echo(f"Max workers: {max_workers}")
    else:
        click.echo(f"Max workers: auto ({actual_max_workers} CPU cores)")

    if dry_run:
        click.echo("DRY RUN MODE - Pipeline will not be executed")

    click.echo()

    # Prepare arguments for parallel execution
    execution_args = []
    skipped_iterations = []

    for i, loop_item in enumerate(loop_items, 1):
        # Validate loop item
        if not isinstance(loop_item, dict):
            click.echo(
                f"Skipping iteration {i}: Loop item is not a dictionary", err=True
            )
            skipped_iterations.append(i)
            continue

        # Combine global context with current loop item
        # Loop item variables override global context variables
        current_context = {**global_ctx, **loop_item}
        execution_args.append((i, pipeline_config, current_context, dry_run))

    if not execution_args:
        click.echo("No valid iterations to execute!")
        sys.exit(1)

    # Execute in parallel
    click.echo(f"Starting parallel execution of {len(execution_args)} iterations...")
    start_time = time.time()

    results = []
    completed_count = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_iteration = {
            executor.submit(execute_single_iteration, args): args[0]
            for args in execution_args
        }

        # Collect results as they complete
        for future in as_completed(future_to_iteration):
            iteration = future_to_iteration[future]
            completed_count += 1

            try:
                result = future.result()
                results.append(result)

                # Progress reporting
                progress = f"[{completed_count}/{len(execution_args)}]"
                if result.success:
                    if dry_run:
                        click.echo(
                            f"{progress} Iteration {result.iteration}: ✓ Pipeline formatted successfully"
                        )
                    else:
                        click.echo(
                            f"{progress} Iteration {result.iteration}: ✓ Processed {result.point_count:,} points"
                        )
                else:
                    click.echo(
                        f"{progress} Iteration {result.iteration}: ✗ {result.error_message}",
                        err=True,
                    )

            except Exception as e:
                click.echo(
                    f"[{completed_count}/{len(execution_args)}] Iteration {iteration}: ✗ Unexpected error: {e}",
                    err=True,
                )
                results.append(
                    ExecutionResult(
                        iteration=iteration,
                        success=False,
                        point_count=0,
                        error_message=f"Unexpected error: {e}",
                    )
                )

    end_time = time.time()
    execution_time = end_time - start_time

    # Sort results by iteration number for consistent reporting
    results.sort(key=lambda x: x.iteration)

    # Generate summary
    successful_results = [r for r in results if r.success]
    failed_results = [r for r in results if not r.success]
    total_points = sum(r.point_count for r in successful_results)

    click.echo(f"\n{'=' * 60}")
    click.echo("EXECUTION SUMMARY")
    click.echo(f"{'=' * 60}")

    if dry_run:
        click.echo("Dry run complete!")
        click.echo(
            f"Successfully formatted: {len(successful_results)}/{len(results)} iterations"
        )
    else:
        click.echo("Pipeline execution complete!")
        click.echo(
            f"Successfully processed: {len(successful_results)}/{len(results)} iterations"
        )
        click.echo(f"Total points processed: {total_points:,}")

    click.echo(f"Execution time: {execution_time:.2f} seconds")

    if len(results) > 1:
        click.echo(
            f"Parallel efficiency: {len(results)} iterations completed in {execution_time:.2f}s"
        )
        if not dry_run:
            # Only show throughput for actual executions
            points_per_second = (
                total_points / execution_time if execution_time > 0 else 0
            )
            click.echo(f"Processing throughput: {points_per_second:,.0f} points/second")

    if skipped_iterations:
        click.echo(f"Skipped iterations (invalid): {len(skipped_iterations)}")
        for iteration in skipped_iterations:
            click.echo(f"  - Iteration {iteration}")

    if failed_results:
        click.echo(f"Failed iterations: {len(failed_results)}")
        for result in failed_results:
            click.echo(f"  - Iteration {result.iteration}: {result.error_message}")

        # Exit with error code if any iterations failed
        sys.exit(1)

    click.echo("All iterations completed successfully!")


if __name__ == "__main__":
    main()
