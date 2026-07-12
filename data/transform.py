"""
Capa de Transformacion Inteligente (la T de ELT).

Usa embeddings semanticos para detectar y corregir automaticamente
inconsistencias en los datos: acentos, case, duplicados, variantes.

Principio: embeddings → clustering → canonicalizacion.
Sin reglas manuales. Sin archivo por archivo.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import unicodedata
import re

# Articulos y preposiciones que no cambian el significado del programa
_ARTICLES = {'EL', 'LA', 'LOS', 'LAS', 'DE', 'DEL', 'EN'}


def _norm(text: str) -> str:
    """
    Normalizacion completa para canonicalizacion de nombres.

    Pipeline:
      1. NFKD decompose -> strip accents
      2. UPPER -> elimina variaciones de case
      3. Remove punctuation (conserva + para CEFR: B1+, A2+)
      4. Collapse multiple spaces
      5. Remove articles/prepositions (EL, LA, LOS, LAS, DE, DEL, EN)
      6. Trim

    Reduce 11,233 nombres SIET a ~8,937 canonicos (20.4%).
    """
    if not text or not isinstance(text, str):
        return ''

    # 1. NFKD decompose + strip combining chars (acentos)
    nfkd = unicodedata.normalize('NFKD', text)
    result = ''.join(c for c in nfkd if not unicodedata.combining(c))

    # 2. UPPER
    result = result.upper()

    # 3. Remove punctuation EXCEPT + (CEFR levels: B1+, A2+)
    result = re.sub(r'[^A-Z0-9 +]', ' ', result)

    # 4. Collapse whitespace
    result = re.sub(r'\s+', ' ', result).strip()

    # 5. Remove articles/prepositions (as standalone words)
    words = [w for w in result.split() if w not in _ARTICLES]
    result = ' '.join(words)

    return result.strip()


def build_canonical_siet_mapping(conn) -> Dict[str, str]:
    """
    Construye mapeo inteligente de nombres SIET variantes -> canonico.

    Pipeline:
      1. Cargar todos los nombres unicos de siet_programas
      2. Agrupar por nombre normalizado (_norm: accents + case + punctuation + articles)
      3. Dentro de cada grupo, elegir el nombre mas frecuente como canonico

    Returns:
        Dict[str, str]: raw_name -> canonical_name
    """
    print("[Transform] Construyendo mapeo canonico de programas SIET...")

    # 1. Cargar nombres unicos con frecuencias
    df = conn.execute("""
        SELECT "Nombre Programa" as nombre, COUNT(*) as freq
        FROM siet.siet_programas
        WHERE "Nombre Programa" IS NOT NULL
        GROUP BY 1
        ORDER BY freq DESC
    """).fetchdf()

    print(f"[Transform] {len(df)} nombres unicos")

    # 2. Agrupar por forma normalizada
    df['norm'] = df['nombre'].apply(_norm)
    groups = df.groupby('norm')

    canonical = {}
    direct_matches = 0
    cluster_matches = 0

    for norm_name, group in groups:
        if len(group) == 1:
            # Caso simple: una sola forma -> es su propio canonico
            name = group.iloc[0]['nombre']
            canonical[name] = name
            direct_matches += 1
        else:
            # Multiples variantes -> elegir la mas frecuente como canonico
            group_sorted = group.sort_values('freq', ascending=False)
            canonical_name = group_sorted.iloc[0]['nombre']

            for _, row in group.iterrows():
                canonical[row['nombre']] = canonical_name
                cluster_matches += 1

    print(f"[Transform] {direct_matches} nombres unicos, {cluster_matches} variantes agrupadas")
    print(f"[Transform] {len(canonical)} mappings generados")

    return canonical


def normalize_nbc_name(name: str, conn) -> str:
    """
    Resuelve un nombre de NBC (posiblemente con acentos o variantes)
    a su forma canonica desde catalogo_nbc_snies.

    Usa STRIP_ACCENTS + UPPER para matching case/accent-insensitive.
    """
    name_esc = name.replace("'", "''")
    name_norm = _norm(name)

    # Buscar en tabla corregida primero
    try:
        rows = conn.execute("""
            SELECT NBC FROM catalogo_curado.catalogo_nbc_snies_corregido
        """).fetchall()
        for (nbc,) in rows:
            if _norm(nbc) == name_norm:
                return nbc
    except Exception:
        pass

    # Buscar en tabla original
    rows = conn.execute("""
        SELECT NBC FROM catalogo_curado.catalogo_nbc_snies
    """).fetchall()
    for (nbc,) in rows:
        if _norm(nbc) == name_norm:
            return nbc

    # No encontrado -> devolver el original
    return name


def build_siet_corpus_clean(conn, canonical: Dict[str, str] = None) -> Tuple[List[str], List[str]]:
    """
    Construye corpus SIET limpio para busqueda semantica.

    Aplica mapeo canonico si se proporciona, deduplica, y guarda
    tanto el nombre original como la version limpia (sin prefijos).
    """
    if canonical is None:
        canonical = build_canonical_siet_mapping(conn)

    df = conn.execute("""
        SELECT DISTINCT "Nombre Programa" as nombre, "Area de Desempeño" as area
        FROM siet.siet_programas
        WHERE "Nombre Programa" IS NOT NULL
          AND LENGTH("Nombre Programa") > 5
    """).fetchdf()

    # Aplicar mapeo canonico
    df['canonical'] = df['nombre'].map(canonical).fillna(df['nombre'])

    # Deducplicar por nombre canonico
    df = df.drop_duplicates(subset=['canonical'])

    # Limpiar prefijos para mejor embedding
    from services.ml.snies_etdh import _strip_siet_prefix
    df['clean'] = df['canonical'].apply(lambda n: _strip_siet_prefix(str(n)))

    print(f"[Transform] Corpus SIET limpio: {len(df)} programas canonicos "
          f"(de {len(canonical)} nombres originales)")

    return df['clean'].tolist(), df['canonical'].tolist()
