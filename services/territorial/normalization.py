"""
Módulo de normalización territorial con matching robusto.
Maneja variaciones de nombres de departamentos/municipios usando:
1. Normalización básica (tildes, mayúsculas, espacios)
2. Diccionario de alias conocidos
3. ML fuzzy matching como fallback
4. Código DANE como llave maestra
"""
import unicodedata
import re
from functools import lru_cache
from typing import Optional, Dict, Tuple
import duckdb

# ============================================================================
# NORMALIZACIÓN BÁSICA
# ============================================================================

def normalize_text(text: str) -> str:
    """
    Normaliza texto: quita tildes, minúsculas, espacios extra.
    
    >>> normalize_text("NARIÑO")
    'narino'
    >>> normalize_text("Bogotá D.C.")
    'bogota d.c.'
    >>> normalize_text("NORTE  DE   SANTANDER")
    'norte de santander'
    """
    if not text:
        return ""
    # Quitar tildes
    text = unicodedata.normalize('NFD', str(text))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Minúsculas y espacios
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def normalize_depto(depto: str) -> str:
    """
    Normaliza nombre de departamento a forma canónica.
    Maneja variaciones conocidas como D.C., d. c., etc.
    """
    text = normalize_text(depto)
    # Normalizar variantes de D.C.
    text = re.sub(r'd\.?\s*c\.?', 'd.c.', text)
    # Quitar "departamento de" si existe
    text = re.sub(r'^departamento\s+de\s+', '', text)
    return text


# ============================================================================
# DICCIONARIO DE ALIAS CONOCIDOS
# ============================================================================

# Mapeo de alias a nombre canónico
DEPTO_ALIASES: Dict[str, str] = {
    # Bogotá variantes
    'bogota': 'bogota d.c.',
    'bogota d.c': 'bogota d.c.',
    'bogota dc': 'bogota d.c.',
    'santafe de bogota': 'bogota d.c.',
    'distrito capital': 'bogota d.c.',
    
    # Norte de Santander
    'n. de santander': 'norte de santander',
    'nte de santander': 'norte de santander',
    'nte. de santander': 'norte de santander',
    
    # San Andrés variantes
    'san andres': 'san andres y providencia',
    'san andres y providencia': 'san andres y providencia',
    'archipielago de san andres': 'san andres y providencia',
    
    # Valle
    'valle': 'valle del cauca',
    
    # Ciudades que aparecen como departamento (errores en datos)
    'armenia': 'quindio',  # Armenia es capital de Quindío
    'monteria': 'cordoba',  # Montería es capital de Córdoba
    'medellin': 'antioquia',
    'cali': 'valle del cauca',
    'barranquilla': 'atlantico',
    'cartagena': 'bolivar',
    'bucaramanga': 'santander',
    'cucuta': 'norte de santander',
    'pereira': 'risaralda',
    'manizales': 'caldas',
    'ibague': 'tolima',
    'villavicencio': 'meta',
    'pasto': 'narino',
    'neiva': 'huila',
    'santa marta': 'magdalena',
    'popayan': 'cauca',
    'sincelejo': 'sucre',
    'valledupar': 'cesar',
    'tunja': 'boyaca',
    'florencia': 'caqueta',
    'quibdo': 'choco',
    'mocoa': 'putumayo',
    'riohacha': 'la guajira',
    'yopal': 'casanare',
    'arauca': 'arauca',  # Igual nombre
    'leticia': 'amazonas',
    'inirida': 'guainia',
    'san jose del guaviare': 'guaviare',
    'mitu': 'vaupes',
    'puerto carreno': 'vichada',
}


def resolve_depto_alias(depto: str) -> str:
    """
    Resuelve alias de departamento a nombre canónico.
    
    >>> resolve_depto_alias("BOGOTÁ")
    'bogota d.c.'
    >>> resolve_depto_alias("Armenia")
    'quindio'
    """
    normalized = normalize_depto(depto)
    return DEPTO_ALIASES.get(normalized, normalized)


# ============================================================================
# MAPEO CÓDIGO DANE <-> NOMBRE
# ============================================================================

# Código DANE a nombre canónico (de DIVIPOLA)
DANE_TO_DEPTO: Dict[int, str] = {
    5: 'antioquia',
    8: 'atlantico',
    11: 'bogota d.c.',
    13: 'bolivar',
    15: 'boyaca',
    17: 'caldas',
    18: 'caqueta',
    19: 'cauca',
    20: 'cesar',
    23: 'cordoba',
    25: 'cundinamarca',
    27: 'choco',
    41: 'huila',
    44: 'la guajira',
    47: 'magdalena',
    50: 'meta',
    52: 'narino',
    54: 'norte de santander',
    63: 'quindio',
    66: 'risaralda',
    68: 'santander',
    70: 'sucre',
    73: 'tolima',
    76: 'valle del cauca',
    81: 'arauca',
    85: 'casanare',
    86: 'putumayo',
    88: 'san andres y providencia',
    91: 'amazonas',
    94: 'guainia',
    95: 'guaviare',
    97: 'vaupes',
    99: 'vichada',
}

# Nombre canónico a código DANE (inverso)
DEPTO_TO_DANE: Dict[str, int] = {v: k for k, v in DANE_TO_DEPTO.items()}


def get_codigo_dane(depto: str) -> Optional[int]:
    """
    Obtiene código DANE de un departamento.
    Maneja alias y variaciones de nombres.
    
    >>> get_codigo_dane("NARIÑO")
    52
    >>> get_codigo_dane("Bogotá D.C.")
    11
    >>> get_codigo_dane("Armenia")  # Ciudad -> Departamento
    63
    """
    canonical = resolve_depto_alias(depto)
    return DEPTO_TO_DANE.get(canonical)


def get_depto_from_dane(codigo: int) -> Optional[str]:
    """
    Obtiene nombre de departamento desde código DANE.
    
    >>> get_depto_from_dane(52)
    'narino'
    >>> get_depto_from_dane(11)
    'bogota d.c.'
    """
    return DANE_TO_DEPTO.get(codigo)


# ============================================================================
# ML FUZZY MATCHING (FALLBACK)
# ============================================================================

_embedding_model = None

def get_embedding_model():
    """Carga modelo de embeddings (lazy loading)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    return _embedding_model


def ml_match_depto(depto: str, candidates: list, threshold: float = 0.85) -> Optional[str]:
    """
    Usa ML para encontrar el mejor match de departamento.
    Solo se usa como fallback cuando normalización + alias fallan.
    
    Args:
        depto: Nombre de departamento a buscar
        candidates: Lista de nombres canónicos
        threshold: Umbral mínimo de similitud (default 0.85)
    
    Returns:
        Mejor match si supera threshold, None si no
    """
    try:
        model = get_embedding_model()
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Embeddings
        query_emb = model.encode([depto])
        cand_embs = model.encode(candidates)
        
        # Similitud
        sims = cosine_similarity(query_emb, cand_embs)[0]
        best_idx = sims.argmax()
        best_sim = sims[best_idx]
        
        if best_sim >= threshold:
            return candidates[best_idx]
        return None
    except Exception:
        return None


def robust_depto_match(depto: str, use_ml: bool = True) -> Tuple[Optional[str], Optional[int]]:
    """
    Match robusto de departamento con fallback ML.
    
    Returns:
        Tuple[nombre_canonico, codigo_dane] o (None, None) si no match
    """
    # 1. Intentar normalización + alias
    canonical = resolve_depto_alias(depto)
    code = DEPTO_TO_DANE.get(canonical)
    
    if code is not None:
        return canonical, code
    
    # 2. Fallback ML si está habilitado
    if use_ml:
        candidates = list(DEPTO_TO_DANE.keys())
        ml_match = ml_match_depto(normalize_text(depto), candidates)
        if ml_match:
            return ml_match, DEPTO_TO_DANE.get(ml_match)
    
    return None, None


# ============================================================================
# MAPEO DE REGIONES COLOMBIANAS
# ============================================================================

DEPTO_TO_REGION: Dict[str, str] = {
    # Región Caribe
    'atlantico': 'Caribe',
    'bolivar': 'Caribe',
    'cesar': 'Caribe',
    'cordoba': 'Caribe',
    'la guajira': 'Caribe',
    'magdalena': 'Caribe',
    'sucre': 'Caribe',
    'san andres y providencia': 'Caribe',
    
    # Región Andina
    'antioquia': 'Andina',
    'boyaca': 'Andina',
    'caldas': 'Andina',
    'cundinamarca': 'Andina',
    'huila': 'Andina',
    'norte de santander': 'Andina',
    'quindio': 'Andina',
    'risaralda': 'Andina',
    'santander': 'Andina',
    'tolima': 'Andina',
    'bogota d.c.': 'Andina',
    
    # Región Pacífica
    'cauca': 'Pacífica',
    'choco': 'Pacífica',
    'narino': 'Pacífica',
    'valle del cauca': 'Pacífica',
    
    # Región Orinoquía
    'arauca': 'Orinoquía',
    'casanare': 'Orinoquía',
    'meta': 'Orinoquía',
    'vichada': 'Orinoquía',
    
    # Región Amazonía
    'amazonas': 'Amazonía',
    'caqueta': 'Amazonía',
    'guainia': 'Amazonía',
    'guaviare': 'Amazonía',
    'putumayo': 'Amazonía',
    'vaupes': 'Amazonía',
}


def get_region(depto: str) -> Optional[str]:
    """
    Obtiene la región geográfica de un departamento.
    
    >>> get_region("NARIÑO")
    'Pacífica'
    >>> get_region("Bogotá D.C.")
    'Andina'
    """
    canonical, _ = robust_depto_match(depto, use_ml=False)
    if canonical:
        return DEPTO_TO_REGION.get(canonical)
    return None


# ============================================================================
# UTILIDADES PARA QUERIES
# ============================================================================

@lru_cache(maxsize=128)
def build_depto_name_variations(depto: str) -> tuple:
    """
    Construye lista de variaciones de nombre para usar en queries SQL.
    Retorna tuple para que sea hashable (cacheable).
    
    >>> build_depto_name_variations("NARIÑO")
    ('NARIÑO', 'Nariño', 'narino', 'NARINO', ...)
    """
    canonical, _ = robust_depto_match(depto, use_ml=False)
    if not canonical:
        canonical = normalize_depto(depto)
    
    variations = set()
    
    # Original y normalizado
    variations.add(depto)
    variations.add(depto.upper())
    variations.add(depto.lower())
    variations.add(depto.title())
    
    # Canónico y sus variantes
    variations.add(canonical)
    variations.add(canonical.upper())
    variations.add(canonical.title())
    
    # Con y sin tildes
    with_accent = canonical
    for old, new in [('a', 'á'), ('e', 'é'), ('i', 'í'), ('o', 'ó'), ('u', 'ú'), ('n', 'ñ')]:
        if old in canonical:
            # Generar versiones con tildes comunes
            variations.add(canonical.replace('narino', 'nariño'))
            variations.add(canonical.replace('cordoba', 'córdoba'))
            variations.add(canonical.replace('bolivar', 'bolívar'))
            variations.add(canonical.replace('boyaca', 'boyacá'))
            variations.add(canonical.replace('caqueta', 'caquetá'))
            variations.add(canonical.replace('choco', 'chocó'))
            variations.add(canonical.replace('quindio', 'quindío'))
            variations.add(canonical.replace('atlantico', 'atlántico'))
            variations.add(canonical.replace('bogota', 'bogotá'))
    
    # Mayúsculas con tildes
    variations.update(v.upper() for v in list(variations))
    
    return tuple(variations)


# ============================================================================
# TEST
# ============================================================================

if __name__ == '__main__':
    print("=== TEST DE NORMALIZACIÓN TERRITORIAL ===\n")
    
    test_cases = [
        "NARIÑO",
        "Narino", 
        "nariño",
        "Bogotá D.C.",
        "BOGOTA",
        "bogota dc",
        "Armenia",  # Ciudad -> Quindío
        "MONTERIA", # Ciudad -> Córdoba
        "N. de Santander",
        "Valle",
        "San Andrés",
        "DESCONOCIDO",
    ]
    
    for test in test_cases:
        canonical, code = robust_depto_match(test, use_ml=False)
        region = get_region(test) if canonical else None
        print(f"'{test}' -> canonical='{canonical}', DANE={code}, región='{region}'")
    
    print("\n=== TEST DE VARIACIONES ===")
    for depto in ["NARIÑO", "Bogotá D.C."]:
        vars = build_depto_name_variations(depto)
        print(f"\n'{depto}' tiene {len(vars)} variaciones:")
        print(f"  {list(vars)[:10]}...")
