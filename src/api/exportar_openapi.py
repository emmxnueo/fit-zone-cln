"""Genera docs/api/openapi.json a partir de la API.

Uso:  python -m src.api.exportar_openapi
"""
import json
from pathlib import Path

from .main import app


def main() -> Path:
    destino = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


if __name__ == "__main__":
    print(f"OpenAPI escrito en {main()}")
