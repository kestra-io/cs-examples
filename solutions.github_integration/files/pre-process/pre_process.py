"""Utility for validating CSV inputs prior to Kestra processing."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Sequence

import click
import pandas as pd


logging.basicConfig(
	level=logging.INFO,
	format="%(levelname)s: %(message)s",
	stream=sys.stdout,
)


def pre_process(input_file: Path, column_names: Sequence[str]) -> None:
	"""Load a CSV file, print quick stats, and ensure required columns exist."""

	logging.info(f"Reading CSV from {input_file}")
	dataframe = pd.read_csv(input_file)

	logging.info(f"CSV details - rows: {len(dataframe)}, columns: {len(dataframe.columns)}")
	logging.info(f"Available columns: {', '.join(dataframe.columns)}")

	missing_columns = [col for col in column_names if col not in dataframe.columns]
	if missing_columns:
		logging.error(f"Missing required columns: {', '.join(missing_columns)}")
		raise ValueError(f"CSV validation failed; missing columns: {', '.join(missing_columns)}")

	logging.info(f"Column validation successful for: {', '.join(column_names)}")


@click.command()
@click.option(
	"--input-file",
	"input_file",
	type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
	required=True,
	help="Path to the CSV file to validate.",
)
@click.option(
	"--column-names",
	"column_names",
	type=str,
	required=True,
	help="Comma-separated list of column names that must exist in the CSV.",
)
def main(input_file: Path, column_names: str) -> None:
	"""CLI entry point for the pre-process validation script."""

	requested_columns = [col.strip() for col in column_names.split(",") if col.strip()]
	if not requested_columns:
		raise click.BadParameter(
			"At least one column name must be provided.",
			param_hint="--column-names",
		)

	try:
		pre_process(input_file=input_file, column_names=requested_columns)
	except ValueError as exc:
		raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
	main()
	