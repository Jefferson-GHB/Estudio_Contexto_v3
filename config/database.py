"""Conexion a base de datos DuckDB con deteccion automatica de ruta."""

import os
from pathlib import Path
import duckdb
import streamlit as st


def _get_duckdb_path():
    """Detecta la ruta correcta de la BD segun el entorno."""
    if os.environ.get('DUCKDB_PATH'):
        return os.environ.get('DUCKDB_PATH')
    hf_path = Path(__file__).parent.parent / "data" / "repositorio.duckdb"
    if hf_path.exists():
        return str(hf_path)
    alt_path = Path(__file__).parent.parent / "repositorio.duckdb"
    if alt_path.exists():
        return str(alt_path)
    return str(Path(__file__).parent.parent / "data" / "repositorio.duckdb")


DUCKDB_PATH = _get_duckdb_path()


def get_conn():
    """Obtiene conexion read-only a DuckDB."""
    return duckdb.connect(DUCKDB_PATH, read_only=True)
