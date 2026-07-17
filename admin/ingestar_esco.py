"""
ESCO Skills Extractor — Full extraction from ESCO API v1.2.0
============================================================

Extrae todas las habilidades, conocimientos y competencias desde la API
europea ESCO con su jerarquia completa, descripciones, tipos de habilidad,
niveles de reutilizacion y conteo de ocupaciones relacionadas.

Output: CSV + DuckDB tables en schema tendencias_tecnologicas.
Recuperado de Repositorio Maestro V1 (v2). Sin dependencias del proyecto — funciona standalone.
"""
import requests
import json
import time
import csv
import os
import sys

API = "https://ec.europa.eu/esco/api"
VER = "v1.2.0"
LANG = "es"
PAGE_SIZE = 100  # Max allowed by ESCO API

# ============================================================================
# ESCO PILLAR HIERARCHY (from taxonomy probe)
# ============================================================================
# S = Competencias (skills/abilities)
# K = Conocimientos (knowledge) — aligned with ISCED-F fields
# T = Competencias Transversales (transversal skills)
# L = Competencias Lingüísticas (language skills) — skip for now

SKILL_PILLARS = {
    "S": {
        "uri": "http://data.europa.eu/esco/skill/335228d2-297d-4e0e-a6ee-bc6a8dc110d9",
        "name": "Competencias",
    },
    "K": {
        "uri": "http://data.europa.eu/esco/skill/c46fcb45-5c14-4ffa-abed-5a43f104bb22",
        "name": "Conocimientos",
    },
    "T": {
        "uri": "http://data.europa.eu/esco/skill/04a13491-b58c-4d33-8b59-8fad0d55fe9e",
        "name": "Competencias Transversales",
    },
}

# ISCED-F <-> SNIES Áreas de Conocimiento mapping
# K pillar sub-categories use ISCED-F codes
ISCED_TO_SNIES = {
    "00": "Transversal",
    "01": "Educación",
    "02": "Bellas Artes",
    "03": "Ciencias Sociales y Humanas",
    "04": "Economía, Administración, Contaduría y Afines",
    "05": "Matemáticas y Ciencias Naturales",
    "06": "Ingeniería, Arquitectura, Urbanismo y Afines",
    "07": "Ingeniería, Arquitectura, Urbanismo y Afines",
    "08": "Agronomía, Veterinaria y Afines",
    "09": "Ciencias de la Salud",
    "10": "Economía, Administración, Contaduría y Afines",
    "99": "Transversal",
}

# S pillar sub-categories mapping to broader sectors
S_CODE_TO_SECTOR = {
    "S1": "Transversal",  # comunicación, colaboración y creatividad
    "S2": "Transversal",  # competencias en materia de información
    "S3": "Ciencias de la Salud",  # prestar asistencia y cuidados
    "S4": "Economía, Administración, Contaduría y Afines",  # competencias de gestión
    "S5": "Ingeniería, Arquitectura, Urbanismo y Afines",  # trabajar con ordenadores
    "S6": "Transversal",  # manipular y mover
    "S7": "Ingeniería, Arquitectura, Urbanismo y Afines",  # construir
    "S8": "Ingeniería, Arquitectura, Urbanismo y Afines",  # maquinaria especializada
}

# T pillar: all are transversal
T_CODE_TO_SECTOR = {
    "T1": "Transversal",
    "T2": "Transversal",
    "T3": "Transversal",
    "T4": "Transversal",
    "T5": "Transversal",
    "T6": "Transversal",
}


def api_get(endpoint, params, retries=3):
    """API call with retry logic."""
    params["selectedVersion"] = VER
    params["language"] = LANG
    for attempt in range(retries):
        try:
            r = requests.get(f"{API}{endpoint}", params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP {r.status_code} for {endpoint}: {r.text[:200]}")
                time.sleep(2)
        except Exception as e:
            print(f"  Error: {e}, retrying...")
            time.sleep(3)
    return None


def get_subcategories(parent_uri):
    """Get narrower concepts (sub-categories) of a concept."""
    data = api_get("/resource/related", {
        "uri": parent_uri,
        "relation": "narrowerConcept",
        "full": "false",
        "limit": 100,
    })
    if not data:
        return []
    return data.get("_embedded", {}).get("narrowerConcept", [])


def get_leaf_skills(parent_uri, offset=0):
    """Get narrower skills (leaf-level skills) of a concept."""
    data = api_get("/resource/related", {
        "uri": parent_uri,
        "relation": "narrowerSkill",
        "full": "true",
        "limit": PAGE_SIZE,
        "offset": offset,
    })
    if not data:
        return [], 0
    total = data.get("total", 0)
    skills = data.get("_embedded", {}).get("narrowerSkill", [])
    return skills, total


def extract_skill_data(skill, pillar_code, category_code, category_name, sector):
    """Extract relevant fields from a skill JSON object."""
    uri = skill.get("uri", "")
    title = skill.get("title", "")
    
    # Get preferred label in Spanish
    pref_labels = skill.get("preferredLabel", {})
    label_es = pref_labels.get("es", title)
    
    # Description in Spanish
    desc = skill.get("description", {}).get("es", {})
    if isinstance(desc, dict):
        desc_text = desc.get("literal", "")
    elif isinstance(desc, str):
        desc_text = desc
    else:
        desc_text = ""
    
    # Skill type and reuse level from _links
    links = skill.get("_links", {})
    
    skill_type_links = links.get("hasSkillType", [])
    skill_type = ""
    if skill_type_links:
        st = skill_type_links[0] if isinstance(skill_type_links, list) else skill_type_links
        skill_type = st.get("title", st.get("uri", ""))
    
    reuse_level_links = links.get("hasReuseLevel", [])
    reuse_level = ""
    if reuse_level_links:
        rl = reuse_level_links[0] if isinstance(reuse_level_links, list) else reuse_level_links
        reuse_level = rl.get("title", rl.get("uri", ""))
    
    # Count related occupations (essential + optional)
    n_essential = len(links.get("isEssentialForOccupation", []))
    n_optional = len(links.get("isOptionalForOccupation", []))
    
    # Alternative labels in Spanish
    alt_labels = skill.get("alternativeLabel", {}).get("es", [])
    if isinstance(alt_labels, str):
        alt_labels = [alt_labels]
    alt_labels_str = "; ".join(alt_labels[:5]) if alt_labels else ""
    
    return {
        "esco_uri": uri,
        "habilidad": label_es,
        "descripcion": desc_text[:500],  # Truncate for DB
        "pilar": pillar_code,
        "categoria_esco": category_name,
        "codigo_categoria": category_code,
        "sector_snies": sector,
        "tipo_skill": skill_type,
        "nivel_reutilizacion": reuse_level,
        "n_ocupaciones_esencial": n_essential,
        "n_ocupaciones_opcional": n_optional,
        "n_ocupaciones_total": n_essential + n_optional,
        "etiquetas_alternativas": alt_labels_str,
        "fuente": "ESCO v1.2.0 (European Commission)",
    }


def extract_pillar(pillar_code, pillar_info):
    """Extract all skills from a pillar, navigating 2 levels of hierarchy."""
    print(f"\n{'='*60}")
    print(f"PILLAR {pillar_code}: {pillar_info['name']}")
    print(f"{'='*60}")
    
    all_skills = []
    
    # Get level-1 sub-categories
    subcats = get_subcategories(pillar_info["uri"])
    print(f"  Found {len(subcats)} sub-categories")
    
    for cat in subcats:
        cat_code = cat.get("code", "")
        cat_name = cat.get("title", "")
        cat_uri = cat.get("uri", "")
        
        # Determine sector mapping
        if pillar_code == "K":
            sector = ISCED_TO_SNIES.get(cat_code, "Transversal")
        elif pillar_code == "S":
            sector = S_CODE_TO_SECTOR.get(cat_code, "Transversal")
        else:
            sector = T_CODE_TO_SECTOR.get(cat_code, "Transversal")
        
        print(f"\n  [{cat_code}] {cat_name} -> Sector: {sector}")
        
        # Get level-2 sub-categories (more specific groups)
        subcats2 = get_subcategories(cat_uri)
        
        if subcats2:
            print(f"    {len(subcats2)} sub-groups")
            for subcat in subcats2:
                sub_code = subcat.get("code", cat_code)
                sub_name = subcat.get("title", "")
                sub_uri = subcat.get("uri", "")
                
                # Get leaf skills
                offset = 0
                while True:
                    skills, total = get_leaf_skills(sub_uri, offset)
                    if not skills:
                        break
                    
                    for skill in skills:
                        row = extract_skill_data(
                            skill, pillar_code, sub_code, 
                            f"{cat_name} > {sub_name}", sector
                        )
                        all_skills.append(row)
                    
                    offset += 1
                    if offset * PAGE_SIZE >= total:
                        break
                    time.sleep(0.3)  # Be respectful to the API
                
                sys.stdout.write(f"    [{sub_code}] {sub_name}: {len(skills)} skills\r\n")
                sys.stdout.flush()
        else:
            # No sub-groups, get skills directly (can happen for T pillar)
            offset = 0
            cat_skills = 0
            while True:
                skills, total = get_leaf_skills(cat_uri, offset)
                if not skills:
                    break
                
                for skill in skills:
                    row = extract_skill_data(
                        skill, pillar_code, cat_code,
                        cat_name, sector
                    )
                    all_skills.append(row)
                    cat_skills += 1
                
                offset += 1
                if offset * PAGE_SIZE >= total:
                    break
                time.sleep(0.3)
            
            print(f"    Direct skills: {cat_skills}")
    
    print(f"\n  TOTAL {pillar_code}: {len(all_skills)} skills extracted")
    return all_skills


def main():
    print("ESCO Skills Full Extraction")
    print(f"API: {API}, Version: {VER}, Language: {LANG}")
    print(f"Started at: {time.strftime('%H:%M:%S')}")
    
    all_data = []
    
    for code, info in SKILL_PILLARS.items():
        pillar_data = extract_pillar(code, info)
        all_data.extend(pillar_data)
        print(f"\nRunning total: {len(all_data)} skills")
        # Small pause between pillars
        time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE: {len(all_data)} skills total")
    print(f"Finished at: {time.strftime('%H:%M:%S')}")
    
    # Save to CSV
    csv_path = os.path.join(
        os.path.dirname(__file__),
        "Dataset", "_CATALOGO_CURADO", "CATALOGO_ESCO_SKILLS_GLOBAL.csv"
    )
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    if all_data:
        fieldnames = list(all_data[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\nCSV saved: {csv_path} ({len(all_data)} rows)")
    
    # Load into DuckDB
    try:
        import duckdb
        import pandas as pd
        
        df = pd.DataFrame(all_data)
        
        # Stats
        print(f"\nBy sector:")
        print(df["sector_snies"].value_counts().to_string())
        print(f"\nBy pillar:")
        print(df["pilar"].value_counts().to_string())
        
        # Load into app DB
        db_app = os.path.join(
            os.path.dirname(__file__),
            "Estudio_Contexto", "repositorio.duckdb"
        )
        if os.path.exists(db_app):
            print(f"\nLoading into {db_app}...")
            con = duckdb.connect(db_app)
            con.execute("CREATE SCHEMA IF NOT EXISTS esco")
            con.execute("DROP TABLE IF EXISTS esco.skills_global")
            con.execute("""
                CREATE TABLE esco.skills_global AS 
                SELECT * FROM df
            """)
            count = con.execute("SELECT COUNT(*) FROM esco.skills_global").fetchone()[0]
            print(f"  Loaded {count} rows into esco.skills_global")
            
            # Also update the old habilidades_futuro with ESCO data
            # Create a summary view by sector
            con.execute("DROP TABLE IF EXISTS tendencias_tecnologicas.habilidades_futuro_esco")
            con.execute("""
                CREATE TABLE tendencias_tecnologicas.habilidades_futuro_esco AS
                SELECT 
                    habilidad,
                    categoria_esco as categoria,
                    sector_snies as sector,
                    tipo_skill,
                    nivel_reutilizacion,
                    n_ocupaciones_esencial,
                    n_ocupaciones_opcional,
                    n_ocupaciones_total,
                    descripcion,
                    esco_uri,
                    fuente
                FROM df
                WHERE n_ocupaciones_total > 0
                ORDER BY n_ocupaciones_total DESC
            """)
            count2 = con.execute(
                "SELECT COUNT(*) FROM tendencias_tecnologicas.habilidades_futuro_esco"
            ).fetchone()[0]
            print(f"  Loaded {count2} rows into tendencias_tecnologicas.habilidades_futuro_esco")
            con.close()
        
        # Load into large DB too
        db_large = os.path.join(
            os.path.dirname(__file__),
            "Dataset", "DuckDB", "repositorio.duckdb"
        )
        if os.path.exists(db_large):
            print(f"\nLoading into {db_large}...")
            con2 = duckdb.connect(db_large)
            con2.execute("CREATE SCHEMA IF NOT EXISTS esco")
            con2.execute("DROP TABLE IF EXISTS esco.skills_global")
            con2.execute("CREATE TABLE esco.skills_global AS SELECT * FROM df")
            count3 = con2.execute("SELECT COUNT(*) FROM esco.skills_global").fetchone()[0]
            print(f"  Loaded {count3} rows")
            con2.close()
        
    except ImportError:
        print("DuckDB/pandas not available, skipping DB load")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
