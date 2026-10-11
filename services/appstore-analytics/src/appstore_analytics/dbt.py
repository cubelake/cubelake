import json
from pathlib import Path

from dbt.cli.main import dbtRunner
from loguru import logger


def run_dbt(project_dir: Path, select: str, dbt_vars: dict[str, str] | None = None) -> None:
    common = ["--project-dir", str(project_dir), "--profiles-dir", str(project_dir)]
    runner = dbtRunner()
    args = ["run", "--select", select, *common]
    if dbt_vars:
        args += ["--vars", json.dumps(dbt_vars)]
    logger.info("dbt {}", " ".join(args))
    _invoke(runner, args)


def _invoke(runner: dbtRunner, args: list[str]) -> None:
    result = runner.invoke(args)
    if not result.success:
        raise RuntimeError(f"dbt {args[0]} failed: {result.exception or 'see log above'}")
