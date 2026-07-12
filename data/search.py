"""Busqueda semantica de programas con sentence-transformers.
Cache en disco: primera carga ~30s, posteriores <1s desde .npy."""
import streamlit as st
import numpy as np
import json
from pathlib import Path
from typing import List, Tuple, Optional

MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
CACHE_DIR = Path(__file__).parent.parent / "services" / "cache_data" / "ml_embeddings"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_FILE = CACHE_DIR / "programas_embeddings.npy"
NAMES_FILE = CACHE_DIR / "programas_nombres.json"


@st.cache_resource(show_spinner=False, ttl=3600)
def _cargar_modelo():
    """Carga el modelo una sola vez por sesion (TTL 1h)."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(MODEL_NAME, device="cpu", trust_remote_code=True)
    except Exception:
        return None


def _contar_registros():
    """Cuenta registros en DuckDB para detectar cambios en la BD."""
    import duckdb
    from config.database import DUCKDB_PATH
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    snies = conn.execute("SELECT COUNT(DISTINCT \"NOMBRE_DEL_PROGRAMA\") FROM snies.snies_programas WHERE LENGTH(\"NOMBRE_DEL_PROGRAMA\") > 5").fetchone()[0]
    siet = conn.execute("SELECT COUNT(DISTINCT \"Nombre Programa\") FROM siet.siet_programas WHERE LENGTH(\"Nombre Programa\") > 5").fetchone()[0]
    saber = conn.execute("SELECT COUNT(DISTINCT estu_prgm_academico) FROM icfes_saber.icfes_saber_pro_resultados WHERE LENGTH(estu_prgm_academico) > 5").fetchone()[0]
    conn.close()
    return snies + siet + saber


def _cache_es_fresco():
    """True si el cache en disco existe y tiene <24h de antiguedad y mismo conteo de registros."""
    if not EMBEDDINGS_FILE.exists() or not NAMES_FILE.exists():
        return False
    try:
        import time
        mtime = EMBEDDINGS_FILE.stat().st_mtime
        edad_horas = (time.time() - mtime) / 3600
        if edad_horas > 24:
            return False
        with open(NAMES_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("total_registros", 0) == _contar_registros()
    except Exception:
        return False


def _cache_valido():
    """Verifica si el cache en disco sigue vigente (solo conteo, sin timestamp)."""
    if not EMBEDDINGS_FILE.exists() or not NAMES_FILE.exists():
        return False
    try:
        with open(NAMES_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("total_registros", 0) == _contar_registros()
    except Exception:
        return False


def _cargar_nombres_desde_db():
    """Carga nombres de programa desde DuckDB."""
    import duckdb
    import pandas as pd
    from config.database import DUCKDB_PATH
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    df_snies = conn.execute("""
        SELECT DISTINCT "NOMBRE_DEL_PROGRAMA" as nombre, 'SNIES' as fuente
        FROM snies.snies_programas WHERE "NOMBRE_DEL_PROGRAMA" IS NOT NULL AND LENGTH("NOMBRE_DEL_PROGRAMA") > 5
    """).fetchdf()
    df_siet = conn.execute("""
        SELECT DISTINCT "Nombre Programa" as nombre, 'SIET' as fuente
        FROM siet.siet_programas WHERE "Nombre Programa" IS NOT NULL AND LENGTH("Nombre Programa") > 5
    """).fetchdf()
    df_saber = conn.execute("""
        SELECT DISTINCT estu_prgm_academico as nombre, 'SABER' as fuente
        FROM icfes_saber.icfes_saber_pro_resultados
        WHERE estu_prgm_academico IS NOT NULL AND LENGTH(estu_prgm_academico) > 5
    """).fetchdf()
    conn.close()
    df = pd.concat([df_snies, df_siet, df_saber], ignore_index=True)
    return df['nombre'].tolist(), df['fuente'].tolist()


@st.cache_resource(show_spinner=False, ttl=3600)
def _obtener_embeddings_raw():
    """Computa o carga embeddings desde disco. Sin UI — pura logica.
    Cacheado con st.cache_resource: se ejecuta una sola vez por sesion (TTL 1h)."""
    if _cache_valido():
        embeddings = np.load(EMBEDDINGS_FILE)
        with open(NAMES_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta["nombres"], meta["fuentes"], embeddings

    nombres, fuentes = _cargar_nombres_desde_db()
    model = _cargar_modelo()
    if model is None:
        return [], [], None

    try:
        embeddings = model.encode(nombres, convert_to_numpy=True, show_progress_bar=False)
    except Exception:
        embeddings = model.encode(nombres, convert_to_numpy=True, show_progress_bar=False)

    np.save(EMBEDDINGS_FILE, embeddings)
    with open(NAMES_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "nombres": nombres,
            "fuentes": fuentes,
            "total_registros": len(nombres)
        }, f, ensure_ascii=False)

    return nombres, fuentes, embeddings


def _obtener_embeddings():
    """Wrapper con UI animada solo en cold start.
    Si el cache en disco esta fresco, carga sin mostrar spinner.
    Si necesita computar, muestra st.status animado."""
    if _cache_es_fresco():
        return _obtener_embeddings_raw()

    # Cold start: mostrar UI animada (fuera del cache_resource para que no se congele)
    n_snies, n_siet, n_saber = _contar_fuentes()
    try:
        with st.status("Preparando busqueda inteligente...", expanded=True) as status:
            st.write(f"Base de datos: {n_snies:,} programas SNIES + {n_siet:,} programas SIET + {n_saber:,} Saber PRO")
            st.write("Cargando modelo de inteligencia artificial...")
            st.write("Indexando nombres de programa — esto solo pasa la primera vez...")
            result = _obtener_embeddings_raw()
            if status is not None:
                status.update(label="Busqueda inteligente lista", state="complete", expanded=False)
            return result
    except Exception:
        return _obtener_embeddings_raw()


def _contar_fuentes():
    """Cuenta programas por fuente desde DuckDB (para mostrar en UI)."""
    import duckdb
    from config.database import DUCKDB_PATH
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    n_snies = conn.execute("SELECT COUNT(DISTINCT \"NOMBRE_DEL_PROGRAMA\") FROM snies.snies_programas WHERE LENGTH(\"NOMBRE_DEL_PROGRAMA\") > 5").fetchone()[0]
    n_siet = conn.execute("SELECT COUNT(DISTINCT \"Nombre Programa\") FROM siet.siet_programas WHERE LENGTH(\"Nombre Programa\") > 5").fetchone()[0]
    n_saber = conn.execute("SELECT COUNT(DISTINCT estu_prgm_academico) FROM icfes_saber.icfes_saber_pro_resultados WHERE LENGTH(estu_prgm_academico) > 5").fetchone()[0]
    conn.close()
    return n_snies, n_siet, n_saber


def buscar_programas(query: str, top_k: int = 10) -> List[Tuple[str, str, float]]:
    """Busca programas por similitud semantica.
    Retorna lista de (nombre, fuente, score)."""
    if not query or len(query.strip()) < 2:
        return []

    nombres, fuentes, embeddings = _obtener_embeddings()
    if embeddings is None or len(nombres) == 0:
        return []

    model = _cargar_modelo()
    if model is None:
        return []

    query_emb = model.encode([query.strip()], convert_to_numpy=True)

    from sklearn.metrics.pairwise import cosine_similarity
    sims = cosine_similarity(query_emb, embeddings)[0]

    top_idx = np.argsort(sims)[::-1][:top_k]

    resultados = []
    for idx in top_idx:
        if sims[idx] > 0.3:
            resultados.append((nombres[idx], fuentes[idx], float(sims[idx])))

    return resultados
