"""Mapeo semantico NBC-CUOC via sentence-transformers multilingue."""

import os
import pickle
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np

# Cache directory for embeddings
CACHE_DIR = Path(__file__).parent.parent / "cache_data" / "ml_embeddings"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Modelo configurable via variable de entorno EMBEDDING_MODEL
# Opciones recomendadas para español:
#   "paraphrase-multilingual-MiniLM-L12-v2"   (120 MB, ligero, default)
#   "Alibaba-NLP/gte-multilingual-base"        (620 MB, mejor precision)
#   "intfloat/multilingual-e5-large"           (1.2 GB, alternativa top)
MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

# Singleton para el modelo (evita recargar)
_model = None
_model_failed = False  # Flag para evitar reintentos infinitos
_embeddings_cache = {}


def get_model():
    """Carga el modelo de sentence-transformers (singleton). Auto-detecta GPU con fallback a CPU."""
    global _model, _model_failed
    
    if _model_failed:
        return None
        
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            
            # Auto-detectar dispositivo: GPU (CUDA/MPS) > CPU
            if torch.cuda.is_available():
                device = "cuda"
                if False: print(f"[ML] GPU detectada: {torch.cuda.get_device_name(0)}")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"
                if False: print("[ML] GPU Apple MPS detectada")
            else:
                device = "cpu"
                if False: print("[ML] Sin GPU, usando CPU")
            
            if False: print(f"[ML] Cargando modelo {MODEL_NAME} en {device}...")
            
            _model = SentenceTransformer(MODEL_NAME, device=device, trust_remote_code=True)
            
            # Verificar que el modelo funciona con una prueba simple
            _ = _model.encode(["test"], convert_to_numpy=True)
            
            if False: print(f"[ML] Modelo cargado correctamente en {device}")
            
        except Exception as e:
            error_msg = str(e)
            if False: print(f"[ML] Error cargando modelo: {error_msg}")
            
            # Fallback a CPU si GPU falla
            if device != "cpu":
                try:
                    if False: print("[ML] Fallback a CPU...")
                    _model = SentenceTransformer(MODEL_NAME, device="cpu", trust_remote_code=True)
                    _ = _model.encode(["test"], convert_to_numpy=True)
                    if False: print("[ML] Modelo cargado en CPU (fallback)")
                    return _model
                except Exception as e2:
                    if False: print(f"[ML] Fallback CPU tambien fallo: {e2}")
                    _model_failed = True
                    _model = None
            else:
                _model_failed = True
                _model = None
    
    return _model


def compute_hash(texts: List[str]) -> str:
    """Genera hash único para una lista de textos."""
    combined = "||".join(sorted(texts))
    return hashlib.md5(combined.encode()).hexdigest()[:12]


def get_or_compute_embeddings(
    texts: List[str], 
    cache_name: str,
    force_recompute: bool = False
) -> Optional[np.ndarray]:
    """Obtiene embeddings desde cache de disco o los computa con sentence-transformers."""
    global _embeddings_cache
    
    # Check in-memory cache first
    cache_key = f"{cache_name}_{compute_hash(texts)}"
    if cache_key in _embeddings_cache and not force_recompute:
        return _embeddings_cache[cache_key]
    
    # Check file cache
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    if cache_file.exists() and not force_recompute:
        try:
            with open(cache_file, "rb") as f:
                embeddings = pickle.load(f)
            _embeddings_cache[cache_key] = embeddings
            return embeddings
        except Exception as e:
            if False: print(f"[ML] Error leyendo cache: {e}")
    
    # Compute embeddings
    model = get_model()
    if model is None:
        if False: print("[ML] Modelo no disponible, no se pueden computar embeddings")
        return None
        
    if False: print(f"[ML] Computando embeddings para {len(texts)} textos...")
    try:
        embeddings = model.encode(
            texts, 
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
            normalize_embeddings=True  # Para usar dot product como similitud
        )
    except Exception as e:
        if False: print(f"[ML] Error computando embeddings: {e}")
        return None
    
    # Save to caches
    _embeddings_cache[cache_key] = embeddings
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(embeddings, f)
        if False: print(f"[ML] Embeddings guardados en cache: {cache_file.name}")
    except Exception as e:
        if False: print(f"[ML] Warning: No se pudo guardar cache: {e}")
    
    return embeddings


def semantic_search(
    query: str,
    corpus_texts: List[str],
    corpus_ids: Optional[List[str]] = None,
    top_k: int = 10,
    threshold: float = 0.3,
    cache_name: str = "corpus"
) -> List[Dict]:
    """Busqueda semantica: top-K textos del corpus mas similares al query."""
    if not corpus_texts:
        return []
    
    # Get corpus embeddings (cached)
    corpus_embeddings = get_or_compute_embeddings(corpus_texts, cache_name)
    if corpus_embeddings is None:
        return []
    
    # Compute query embedding (not cached - queries change)
    model = get_model()
    if model is None:
        return []
    
    try:
        query_embedding = model.encode(
            [query], 
            convert_to_numpy=True,
            normalize_embeddings=True
        )[0]
    except Exception as e:
        if False: print(f"[ML] Error codificando query: {e}")
        return []
    
    # Compute similarities (dot product since normalized)
    similarities = np.dot(corpus_embeddings, query_embedding)
    
    # Get top-k indices above threshold
    top_indices = np.argsort(similarities)[::-1][:top_k * 2]  # Get more, then filter
    
    results = []
    for idx in top_indices:
        score = float(similarities[idx])
        if score >= threshold:
            result = {
                "text": corpus_texts[idx],
                "score": score,
                "id": corpus_ids[idx] if corpus_ids else str(idx)
            }
            results.append(result)
            if len(results) >= top_k:
                break
    
    return results


def match_nbc_to_ocupaciones(
    nbc_nombre: str,
    ocupaciones_df: pd.DataFrame,
    top_k: int = 15,
    threshold: float = 0.25,
    query_override: str = None
) -> pd.DataFrame:
    """
    Encuentra ocupaciones CUOC más relevantes para un NBC usando ML.
    
    Args:
        nbc_nombre: Nombre del Núcleo Básico del Conocimiento
        ocupaciones_df: DataFrame con columnas [codigo_cuoc, nombre_ocupacion, ...]
        top_k: Número de ocupaciones a retornar
        threshold: Similitud mínima (0-1)
        query_override: Query de busqueda personalizado (si None, se genera automaticamente)
        
    Returns:
        DataFrame con las ocupaciones más relevantes y score de similitud
    """
    if ocupaciones_df.empty:
        return pd.DataFrame()
    
    # Preparar textos del corpus
    # Usar nombre_ocupacion, y si existe descripción, concatenar
    if "descripcion" in ocupaciones_df.columns:
        corpus_texts = (
            ocupaciones_df["nombre_ocupacion"].fillna("") + " - " + 
            ocupaciones_df["descripcion"].fillna("")
        ).tolist()
    else:
        corpus_texts = ocupaciones_df["nombre_ocupacion"].fillna("").tolist()
    
    # IDs (códigos CUOC)
    if "codigo_cuoc" in ocupaciones_df.columns:
        corpus_ids = ocupaciones_df["codigo_cuoc"].astype(str).tolist()
    elif "cuoc_codigo" in ocupaciones_df.columns:
        corpus_ids = ocupaciones_df["cuoc_codigo"].astype(str).tolist()
    else:
        corpus_ids = [str(i) for i in range(len(corpus_texts))]
    
    # Enriquecer query con contexto
    if query_override:
        query = query_override
    else:
        query = f"Profesional en {nbc_nombre}. Egresado de programa de {nbc_nombre}."
    
    # Búsqueda semántica
    results = semantic_search(
        query=query,
        corpus_texts=corpus_texts,
        corpus_ids=corpus_ids,
        top_k=top_k,
        threshold=threshold,
        cache_name="ocupaciones_cuoc"
    )
    
    if not results:
        return pd.DataFrame()
    
    # Construir DataFrame de resultados
    result_codes = [r["id"] for r in results]
    result_scores = {r["id"]: r["score"] for r in results}
    
    # Filtrar DataFrame original
    code_col = "codigo_cuoc" if "codigo_cuoc" in ocupaciones_df.columns else "cuoc_codigo"
    matched_df = ocupaciones_df[
        ocupaciones_df[code_col].astype(str).isin(result_codes)
    ].copy()
    
    # Agregar score de similitud
    matched_df["similitud_ml"] = matched_df[code_col].astype(str).map(result_scores)
    matched_df = matched_df.sort_values("similitud_ml", ascending=False)
    
    return matched_df


def match_nbc_to_vacantes(
    nbc_nombre: str,
    vacantes_df: pd.DataFrame,
    top_k: int = 20,
    threshold: float = 0.20,
    query_override: str = None
) -> pd.DataFrame:
    """
    Encuentra vacantes laborales más relevantes para un NBC usando ML.
    
    Args:
        nbc_nombre: Nombre del Núcleo Básico del Conocimiento
        vacantes_df: DataFrame con datos de vacantes (debe tener nombre_ocupacion)
        top_k: Número de grupos de ocupación únicos a considerar
        threshold: Similitud mínima
        query_override: Query de busqueda personalizado
        
    Returns:
        DataFrame con vacantes filtradas por ocupaciones relevantes
    """
    if vacantes_df.empty:
        return pd.DataFrame()
    
    # Obtener ocupaciones únicas
    ocupaciones_unicas = vacantes_df.drop_duplicates(
        subset=["nombre_ocupacion"]
    )[["codigo_cuoc", "nombre_ocupacion"]].copy()
    
    # Match semántico
    matched = match_nbc_to_ocupaciones(
        nbc_nombre=nbc_nombre,
        ocupaciones_df=ocupaciones_unicas,
        top_k=top_k,
        threshold=threshold,
        query_override=query_override
    )
    
    if matched.empty:
        return pd.DataFrame()
    
    # Filtrar vacantes por ocupaciones matched
    codigos_matched = matched["codigo_cuoc"].astype(str).tolist()
    result_df = vacantes_df[
        vacantes_df["codigo_cuoc"].astype(str).isin(codigos_matched)
    ].copy()
    
    # Agregar score de similitud
    score_map = matched.set_index(
        matched["codigo_cuoc"].astype(str)
    )["similitud_ml"].to_dict()
    result_df["similitud_ml"] = result_df["codigo_cuoc"].astype(str).map(score_map)
    
    return result_df


def match_nbc_to_competencias(
    nbc_nombre: str,
    competencias_df: pd.DataFrame,
    tipo: str = "conocimientos",  # o "destrezas"
    top_k: int = 15,
    threshold: float = 0.25
) -> pd.DataFrame:
    """
    Encuentra conocimientos o destrezas CUOC relevantes para un NBC.
    
    ESTRATEGIA MEJORADA:
    1. Buscar ocupaciones por similitud semántica con el NBC usando nombre_ocupacion
    2. Obtener las competencias de esas ocupaciones
    
    Args:
        nbc_nombre: Nombre del NBC
        competencias_df: DataFrame con competencias (conocimientos o destrezas)
        tipo: "conocimientos" o "destrezas"
        top_k: Número máximo de resultados
        threshold: Similitud mínima
        
    Returns:
        DataFrame con competencias relevantes
    """
    if competencias_df.empty:
        return pd.DataFrame()
    
    # ESTRATEGIA: Buscar por nombre_ocupacion (no por el texto de la competencia)
    if "nombre_ocupacion" in competencias_df.columns:
        # Obtener ocupaciones únicas
        ocupaciones_unicas = competencias_df[["nombre_ocupacion"]].drop_duplicates()
        ocupaciones_unicas = ocupaciones_unicas[ocupaciones_unicas["nombre_ocupacion"].notna()]
        
        if not ocupaciones_unicas.empty:
            corpus_texts = ocupaciones_unicas["nombre_ocupacion"].tolist()
            corpus_ids = [str(i) for i in range(len(corpus_texts))]
            
            # Query enriquecido para ocupaciones
            query = f"Profesional en {nbc_nombre}. Egresado de programa de {nbc_nombre}. Trabajador de {nbc_nombre}."
            
            results = semantic_search(
                query=query,
                corpus_texts=corpus_texts,
                corpus_ids=corpus_ids,
                top_k=top_k,
                threshold=threshold,
                cache_name=f"ocupaciones_{tipo}"
            )
            
            if results:
                # Obtener nombres de ocupaciones matched
                matched_ocupaciones = [corpus_texts[int(r["id"])] for r in results]
                
                # Filtrar competencias de esas ocupaciones
                result_df = competencias_df[
                    competencias_df["nombre_ocupacion"].isin(matched_ocupaciones)
                ].copy()
                
                # Agregar score de similitud
                score_map = {corpus_texts[int(r["id"])]: r["score"] for r in results}
                result_df["similitud_ml"] = result_df["nombre_ocupacion"].map(score_map)
                
                return result_df
    
    # FALLBACK: Si no hay nombre_ocupacion, buscar por texto de competencia (menos preciso)
    if tipo == "conocimientos":
        text_col = "conocimiento" if "conocimiento" in competencias_df.columns else "descripcion"
    else:
        text_col = "destreza" if "destreza" in competencias_df.columns else "descripcion"
    
    if text_col not in competencias_df.columns:
        text_cols = [c for c in competencias_df.columns if "desc" in c.lower() or "nombre" in c.lower()]
        if text_cols:
            text_col = text_cols[0]
        else:
            return pd.DataFrame()
    
    corpus_texts = competencias_df[text_col].fillna("").tolist()
    corpus_ids = [str(i) for i in range(len(corpus_texts))]
    
    query = f"Competencias y habilidades de {nbc_nombre}. Conocimientos de {nbc_nombre}."
    
    results = semantic_search(
        query=query,
        corpus_texts=corpus_texts,
        corpus_ids=corpus_ids,
        top_k=top_k,
        threshold=threshold,
        cache_name=f"competencias_{tipo}"
    )
    
    if not results:
        return pd.DataFrame()
    
    # Filtrar y agregar scores
    indices = [int(r["id"]) for r in results]
    scores = {int(r["id"]): r["score"] for r in results}
    
    result_df = competencias_df.iloc[indices].copy()
    result_df["similitud_ml"] = result_df.index.map(lambda x: scores.get(x, 0))
    result_df = result_df.sort_values("similitud_ml", ascending=False)
    
    return result_df


# Función de prueba
def test_matching():
    """Prueba rápida del módulo."""
    import duckdb
    
    db_path = Path(__file__).parent.parent.parent / "data" / "repositorio.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    
    # Cargar ocupaciones de vacantes
    vacantes = conn.execute("""
        SELECT DISTINCT codigo_cuoc, ocupacion as nombre_ocupacion 
        FROM tendencias_laborales.vacantes_ape_clean
        WHERE ocupacion IS NOT NULL
        LIMIT 500
    """).df()
    
    # Probar con "Música"
    print("\n" + "="*60)
    print("TEST: Matching semántico para NBC 'Música'")
    print("="*60)
    
    results = match_nbc_to_ocupaciones("Música", vacantes, top_k=10)
    
    if not results.empty:
        print("\nOcupaciones encontradas:")
        for _, row in results.iterrows():
            print(f"  [{row['similitud_ml']:.2f}] {row['nombre_ocupacion']}")
    else:
        print("No se encontraron ocupaciones relevantes")
    
    # Probar con "Ingeniería de sistemas"
    print("\n" + "="*60)
    print("TEST: Matching semántico para NBC 'Ingeniería de sistemas'")
    print("="*60)
    
    results = match_nbc_to_ocupaciones("Ingeniería de sistemas", vacantes, top_k=10)
    
    if not results.empty:
        print("\nOcupaciones encontradas:")
        for _, row in results.iterrows():
            print(f"  [{row['similitud_ml']:.2f}] {row['nombre_ocupacion']}")
    
    conn.close()


if __name__ == "__main__":
    test_matching()
