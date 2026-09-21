import ast
from pathlib import Path


def test_models_do_not_use_python_311_only_str_enum() -> None:
    model_path = Path("metatool/models.py")
    module = ast.parse(model_path.read_text(encoding="utf-8"))

    imported_names = {
        imported_name.name
        for statement in module.body
        if isinstance(statement, ast.ImportFrom) and statement.module == "enum"
        for imported_name in statement.names
    }

    assert "StrEnum" not in imported_names
