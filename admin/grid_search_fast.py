"""
Grid search optimizado para MiniLM — pre-computa corpus UNA vez,
luego prueba 100+ configuraciones en segundos contra cache.

Optimizaciones probadas:
- Threshold: 0.15 a 0.85 (step 0.05)
- L2 normalization: on/off
- Query: NBC solo / Skills CUOC / Ambos combinados
- Stage1 window: 100, 200, 500, 1000
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time, numpy as np
from config.database import get_conn
from data.transform import normalize_nbc_name, _norm, build_canonical_siet_mapping, build_siet_corpus_clean
from services.ml.snies_etdh import (_get_nbc_skills_profile, _build_skills_query,
                                     _strip_siet_prefix, precompute_siet_corpus,
                                     _resolve_structural_chain)

os.environ['EMBEDDING_MODEL'] = 'paraphrase-multilingual-MiniLM-L12-v2'
import services.ml.matching as ml_matching; ml_matching.MODEL_NAME = os.environ['EMBEDDING_MODEL']
import services.ml.snies_etdh as etdh

# Cargar corpus UNA SOLA VEZ
conn = get_conn()

# Obtener todos los NBCs del catalogo
nbcs_raw = conn.execute("SELECT DISTINCT NBC FROM catalogo_curado.catalogo_nbc_snies WHERE NBC IS NOT NULL ORDER BY NBC").fetchall()
NBCS = [normalize_nbc_name(r[0], conn) for r in nbcs_raw]
NBCS = list(dict.fromkeys(NBCS))  # 56 NBCs unicos

print(f"Grid Search MiniLM — {len(NBCS)} NBCs\n")

# Pre-computar corpus SIET (cached in disk)
t0 = time.time()
etdh._siet_corpus_cache = None; etdh._siet_canonical_map = None
ml_matching._embeddings_cache = {}
corpus = precompute_siet_corpus(conn)
clean_texts, canonical_names, corpus_ids, corpus_embs = corpus
print(f"Corpus: {len(clean_texts)} textos, {corpus_embs.shape} dims, {time.time()-t0:.1f}s\n")

# L2 normalize corpus
corpus_embs_norm = corpus_embs / (np.linalg.norm(corpus_embs, axis=1, keepdims=True) + 1e-8)

# Pre-computar queries para TODOS los NBCs (con y sin enrichment)
from services.ml.matching import get_model
model = get_model()

queries_bare = []      # Solo nombre NBC
queries_skills = []    # Skills CUOC
queries_mixed = []     # Ambos

print("Computando queries...")
for nbc in NBCS:
    queries_bare.append(nbc)
    
    skills = _get_nbc_skills_profile(nbc, conn)
    q_skills = _build_skills_query(nbc, skills)
    queries_skills.append(q_skills)
    
    # Mixed: NBC + top 10 skills (para no sobrecargar)
    con = skills.get('top_conocimientos_text', [])[:10]
    q_mixed = nbc + ". " + ". ".join(con) if con else nbc
    queries_mixed.append(q_mixed)

# Embed todos los queries
print("Embedding queries...")
tq = time.time()
emb_bare = model.encode(queries_bare, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
emb_skills = model.encode(queries_skills, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
emb_mixed = model.encode(queries_mixed, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
print(f"Queries embedded in {time.time()-tq:.1f}s\n")

# Pre-computar areas SIET esperadas para cada NBC (para validacion rapida)
expected_areas = []
for nbc in NBCS:
    chain = _resolve_structural_chain(nbc, conn)
    areas = set(_norm(a) for a in chain.get('areas_desempeno_siet', []))
    expected_areas.append(areas)

# Funcion de evaluacion rapida (sin consultas DB, solo dot products)
def evaluate_fast(query_embs, norm_embs, threshold, top_k):
    """Evalua todos los NBCs contra corpus cacheado. Retorna precision."""
    ok = 0
    for i, (q_emb, expected) in enumerate(zip(query_embs, expected_areas)):
        # Dot product (corpus ya esta L2-normalizado)
        scores = np.dot(q_emb, norm_embs.T)
        top_indices = np.argsort(scores)[-top_k:][::-1]
        top_scores = scores[top_indices]
        
        # Aplicar threshold
        valid = top_scores >= threshold
        if not valid.any():
            valid[:5] = True  # Al menos top-5
        
        # Verificar area del top match
        top_idx = top_indices[0]
        top_name = canonical_names[top_idx]
        
        # Buscar area en DB solo para el top match (cachear)
        area = _get_area_for_name(top_name)
        if area and expected:
            if _norm(area) in expected:
                ok += 1
    
    return 100 * ok / len(query_embs)


# Cache de areas para no consultar DB por cada config
_AREA_CACHE = {}

def _get_area_for_name(name):
    if name in _AREA_CACHE:
        return _AREA_CACHE[name]
    try:
        r = conn.execute(
            'SELECT DISTINCT "Area de Desempeño" FROM siet.siet_programas WHERE "Nombre Programa" = ?', [name]
        ).fetchone()
        area = r[0] if r else None
    except:
        area = None
    _AREA_CACHE[name] = area
    return area


# Pre-cachear areas para todos los nombres canonicos
print(f"Caching areas para {len(canonical_names)} nombres...")
for name in canonical_names:
    _get_area_for_name(name)
print("Done.\n")

# GRID SEARCH
THRESHOLDS = [round(0.15 + i*0.02, 2) for i in range(36)]  # 0.15 a 0.85
STAGE1_K = [100, 200, 500, 1000]
QUERY_TYPES = [
    ("Bare", emb_bare),
    ("Skills", emb_skills),
    ("Mixed", emb_mixed),
]

results = []
total_configs = len(THRESHOLDS) * len(STAGE1_K) * len(QUERY_TYPES)
print(f"GRID SEARCH: {total_configs} configuraciones\n")
t_start = time.time()

for qt_name, qt_embs in QUERY_TYPES:
    for k in STAGE1_K:
        # Pre-computar top-k indices para todos los NBCs (costoso pero se hace una vez por k)
        all_top_indices = []
        all_top_scores = []
        for q_emb in qt_embs:
            scores = np.dot(q_emb, corpus_embs_norm.T)
            top_idx = np.argsort(scores)[-k:][::-1]
            top_sc = scores[top_idx]
            all_top_indices.append(top_idx)
            all_top_scores.append(top_sc)
        
        for th in THRESHOLDS:
            ok = 0
            for i, expected in enumerate(expected_areas):
                top_idx = all_top_indices[i]
                top_sc = all_top_scores[i]
                
                valid_mask = top_sc >= th
                if not valid_mask.any():
                    valid_mask[:5] = True
                
                best_idx = top_idx[np.argmax(top_sc)]
                best_name = canonical_names[best_idx]
                area = _AREA_CACHE.get(best_name)
                if area and expected and _norm(area) in expected:
                    ok += 1
            
            prec = 100 * ok / len(NBCS)
            results.append({
                'query': qt_name, 'k': k, 'th': th,
                'prec': round(prec, 1), 'ok': ok
            })

# Ordenar por precision
results.sort(key=lambda r: r['prec'], reverse=True)

print(f"{'='*60}")
print(f"TOP 15 CONFIGURACIONES ({len(results)} probadas en {time.time()-t_start:.1f}s)")
print(f"{'Rank':4s} {'Query':8s} {'K':5s} {'Th':6s} {'Prec':8s} {'OK':5s}")
print(f"{'-'*45}")
for i, r in enumerate(results[:15]):
    print(f"{i+1:3d}.  {r['query']:8s} {r['k']:4d}  {r['th']:.2f}   {r['prec']:5.1f}%  {r['ok']}/{len(NBCS)}")

# Enrichment on vs off
for qt in ['Bare', 'Skills', 'Mixed']:
    subset = [r for r in results if r['query'] == qt]
    best = max(subset, key=lambda r: r['prec'])
    avg = np.mean([r['prec'] for r in subset])
    print(f"\n{qt}: best={best['prec']:.1f}% (th={best['th']:.2f} k={best['k']}) avg={avg:.1f}%")

conn.close()
