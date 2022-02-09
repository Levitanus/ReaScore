from rea_score import inspector as it
import reapy as rpr
from pathlib import Path


def test_project_inspector() -> None:
    pi = it.ProjectInspector()
    pr_path = Path(rpr.Project().path).resolve()
    my_path = Path().resolve()
    assert pr_path == my_path
    pi.export_dir = Path('score')
    pi_path = pi.export_dir_absolute
    assert pi_path == my_path.joinpath('score')
