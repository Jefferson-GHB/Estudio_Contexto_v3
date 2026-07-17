"""
ESCO Skills Extractor v2 — Full extraction via /search endpoint.
================================================================

Version mejorada del extractor ESCO. Usa el endpoint /search?type=skill
con full=true para obtener las 13,939 habilidades paginando de a 100.
Extrae la jerarquia desde broaderHierarchyConcept links en lugar de
recorrer el arbol de pilares manualmente como hace la v1.

Output: CSV + DuckDB tables en schema tendencias_tecnologicas.
Recuperado de UniSabana_Dev (v2). Sin dependencias del proyecto.
"""
import requests
import json
import time
import csv
import os
import sys
import pandas as pd

API = "https://ec.europa.eu/esco/api"
VER = "v1.2.0"
LANG = "es"
PAGE_SIZE = 100  # Max per page

# ISCED-F broad field -> SNIES Área de Conocimiento
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

# S pillar sub-category -> SNIES sector
S_TO_SNIES = {
    "S1": "Transversal",
    "S2": "Transversal",
    "S3": "Ciencias de la Salud",
    "S4": "Economía, Administración, Contaduría y Afines",
    "S5": "Ingeniería, Arquitectura, Urbanismo y Afines",
    "S6": "Transversal",
    "S7": "Ingeniería, Arquitectura, Urbanismo y Afines",
    "S8": "Ingeniería, Arquitectura, Urbanismo y Afines",
}

# Cache for concept code lookups
_concept_cache = {}


def api_get(endpoint, params, retries=3):
    params["selectedVersion"] = VER
    params["language"] = LANG
    for attempt in range(retries):
        try:
            r = requests.get(f"{API}{endpoint}", params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  HTTP {r.status_code}: {r.text[:200]}")
                time.sleep(2)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(3)
    return None


def get_concept_code(uri):
    """Get the code for a concept URI (cached)."""
    if uri in _concept_cache:
        return _concept_cache[uri]
    
    data = api_get("/resource/concept", {"uri": uri})
    if data:
        code = data.get("code", "")
        title = data.get("title", "")
        _concept_cache[uri] = (code, title)
        return (code, title)
    return ("", "")


def determine_sector(skill_data):
    """Determine SNIES sector from the skill's hierarchy links."""
    links = skill_data.get("_links", {})
    
    # Try broaderHierarchyConcept first (most reliable for hierarchy)
    broader = links.get("broaderHierarchyConcept", [])
    if not broader:
        broader = links.get("broaderSkillGroup", [])
    
    # Look at the broader concepts to find the pillar/category code
    for b in broader:
        title = b.get("title", "")
        code = b.get("code", "")
        
        # K pillar: ISCED codes (2-3 digits)
        if code and len(code) >= 2 and code[:2].isdigit():
            broad_field = code[:2]
            sector = ISCED_TO_SNIES.get(broad_field, "")
            if sector:
                return sector, code, title
        
        # S pillar: S codes
        if code and code.startswith("S"):
            base = code[:2]  # S1, S2, etc.
            sector = S_TO_SNIES.get(base, "Transversal")
            return sector, code, title
        
        # T pillar
        if code and code.startswith("T"):
            return "Transversal", code, title
        
        # L pillar (languages)
        if code and code.startswith("L"):
            return "Transversal", code, title
    
    return "Transversal", "", ""


def extract_skills_via_search():
    """Extract ALL skills using the /search endpoint with pagination."""
    all_skills = []
    offset = 0
    total = None
    
    print("Extracting all ESCO skills via /search endpoint...")
    print(f"API: {API}, Version: {VER}, Language: {LANG}")
    start_time = time.time()
    
    while True:
        data = api_get("/search", {
            "type": "skill",
            "limit": PAGE_SIZE,
            "offset": offset,
            "full": "true",
        })
        
        if not data:
            print(f"  Failed at offset {offset}, retrying in 10s...")
            time.sleep(10)
            data = api_get("/search", {
                "type": "skill",
                "limit": PAGE_SIZE,
                "offset": offset,
                "full": "true",
            })
            if not data:
                print(f"  FATAL: Could not fetch page at offset {offset}")
                break
        
        if total is None:
            total = data.get("total", 0)
            print(f"  Total skills to extract: {total}")
        
        results = data.get("_embedded", {}).get("results", [])
        if not results:
            print(f"  No more results at offset {offset}")
            break
        
        for skill in results:
            uri = skill.get("uri", "")
            title = skill.get("title", "")
            
            # Preferred label in Spanish
            pref = skill.get("preferredLabel", {})
            label_es = pref.get("es", title)
            
            # Description in Spanish
            desc = skill.get("description", {}).get("es", {})
            if isinstance(desc, dict):
                desc_text = desc.get("literal", "")
            elif isinstance(desc, str):
                desc_text = desc
            else:
                desc_text = ""
            
            # Skill type
            links = skill.get("_links", {})
            skill_type_links = links.get("hasSkillType", [])
            skill_type = ""
            if skill_type_links:
                st = skill_type_links[0] if isinstance(skill_type_links, list) else skill_type_links
                skill_type = st.get("title", "")
            
            # Reuse level
            reuse_links = links.get("hasReuseLevel", [])
            reuse_level = ""
            if reuse_links:
                rl = reuse_links[0] if isinstance(reuse_links, list) else reuse_links
                reuse_level = rl.get("title", "")
            
            # Occupation counts
            n_essential = len(links.get("isEssentialForOccupation", []))
            n_optional = len(links.get("isOptionalForOccupation", []))
            
            # Determine sector from hierarchy
            sector, cat_code, cat_name = determine_sector(skill)
            
            # Determine pillar
            pilar = ""
            if cat_code:
                if cat_code[0] == "S":
                    pilar = "S"
                elif cat_code[0] == "T":
                    pilar = "T"
                elif cat_code[0] == "L":
                    pilar = "L"
                elif cat_code[0].isdigit():
                    pilar = "K"
            
            # Alternative labels
            alt_labels = skill.get("alternativeLabel", {}).get("es", [])
            if isinstance(alt_labels, str):
                alt_labels = [alt_labels]
            alt_str = "; ".join(alt_labels[:5]) if alt_labels else ""
            
            all_skills.append({
                "esco_uri": uri,
                "habilidad": label_es,
                "descripcion": desc_text[:500],
                "pilar": pilar,
                "codigo_categoria": cat_code,
                "categoria_esco": cat_name,
                "sector_snies": sector,
                "tipo_skill": skill_type,
                "nivel_reutilizacion": reuse_level,
                "n_ocupaciones_esencial": n_essential,
                "n_ocupaciones_opcional": n_optional,
                "n_ocupaciones_total": n_essential + n_optional,
                "etiquetas_alternativas": alt_str,
                "fuente": "ESCO v1.2.0 (European Commission)",
            })
        
        extracted = len(all_skills)
        elapsed = time.time() - start_time
        rate = extracted / elapsed if elapsed > 0 else 0
        eta = (total - extracted) / rate if rate > 0 else 0
        
        print(f"  Page {offset}: {extracted}/{total} skills ({extracted*100//total}%) "
              f"| {rate:.0f} skills/s | ETA: {eta/60:.1f}min")
        
        offset += 1
        
        if offset * PAGE_SIZE >= total:
            break
        
        # Be respectful — small delay between pages
        time.sleep(0.5)
    
    elapsed = time.time() - start_time
    print(f"\nExtraction complete: {len(all_skills)} skills in {elapsed/60:.1f} minutes")
    return all_skills


def main():
    print(f"Started at: {time.strftime('%H:%M:%S')}")
    
    all_data = extract_skills_via_search()
    
    if not all_data:
        print("ERROR: No data extracted!")
        return
    
    # Save CSV
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "Dataset", "_CATALOGO_CURADO", "CATALOGO_ESCO_SKILLS_GLOBAL.csv"
    )
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    fieldnames = list(all_data[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    print(f"\nCSV saved: {csv_path} ({len(all_data)} rows)")
    
    # Stats
    df = pd.DataFrame(all_data)
    print(f"\nBy sector_snies:")
    print(df["sector_snies"].value_counts().to_string())
    print(f"\nBy pilar:")
    print(df["pilar"].value_counts().to_string())
    print(f"\nBy tipo_skill:")
    print(df["tipo_skill"].value_counts().to_string())
    print(f"\nSkills with >0 occupations: {(df['n_ocupaciones_total'] > 0).sum()}")
    print(f"Mean occupations per skill: {df['n_ocupaciones_total'].mean():.1f}")
    
    # Load into DuckDB
    import duckdb
    
    base = os.path.dirname(os.path.abspath(__file__))
    
    # App DB
    db_app = os.path.join(base, "Estudio_Contexto", "repositorio.duckdb")
    if os.path.exists(db_app):
        print(f"\nLoading into {db_app}...")
        con = duckdb.connect(db_app)
        con.execute("CREATE SCHEMA IF NOT EXISTS esco")
        con.execute("DROP TABLE IF EXISTS esco.skills_global")
        con.execute("CREATE TABLE esco.skills_global AS SELECT * FROM df")
        cnt = con.execute("SELECT COUNT(*) FROM esco.skills_global").fetchone()[0]
        print(f"  esco.skills_global: {cnt} rows")
        
        # Summary table for the chart (skills with occupations, top by sector)  
        con.execute("DROP TABLE IF EXISTS esco.skills_por_sector")
        con.execute("""
            CREATE TABLE esco.skills_por_sector AS
            SELECT 
                habilidad,
                categoria_esco as categoria,
                sector_snies as sector,
                pilar,
                tipo_skill,
                nivel_reutilizacion,
                n_ocupaciones_esencial,
                n_ocupaciones_opcional,
                n_ocupaciones_total,
                descripcion,
                esco_uri,
                fuente,
                -- Rank within sector by occupation relevance
                ROW_NUMBER() OVER (
                    PARTITION BY sector_snies 
                    ORDER BY n_ocupaciones_total DESC
                ) as rank_en_sector
            FROM df
            WHERE n_ocupaciones_total > 0
            ORDER BY sector_snies, n_ocupaciones_total DESC
        """)
        cnt2 = con.execute("SELECT COUNT(*) FROM esco.skills_por_sector").fetchone()[0]
        print(f"  esco.skills_por_sector: {cnt2} rows (with occupations)")
        
        # Stats per sector
        stats = con.execute("""
            SELECT sector, COUNT(*) as total, 
                   AVG(n_ocupaciones_total) as avg_ocup
            FROM esco.skills_por_sector
            GROUP BY sector ORDER BY total DESC
        """).fetchdf()
        print(f"\n  Skills per sector (with occupations):")
        for _, row in stats.iterrows():
            print(f"    {row['sector']}: {int(row['total'])} skills, avg {row['avg_ocup']:.1f} occupations")
        
        con.close()
    
    # Large DB
    db_large = os.path.join(base, "Dataset", "DuckDB", "repositorio.duckdb")
    if os.path.exists(db_large):
        print(f"\nLoading into large DB...")
        con2 = duckdb.connect(db_large)
        con2.execute("CREATE SCHEMA IF NOT EXISTS esco")
        con2.execute("DROP TABLE IF EXISTS esco.skills_global")
        con2.execute("CREATE TABLE esco.skills_global AS SELECT * FROM df")
        cnt3 = con2.execute("SELECT COUNT(*) FROM esco.skills_global").fetchone()[0]
        print(f"  {cnt3} rows loaded")
        con2.close()
    
    print(f"\nFinished at: {time.strftime('%H:%M:%S')}")
    print("Done!")


if __name__ == "__main__":
    main()
