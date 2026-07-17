"""
Sondeo exploratorio de la taxonomia ESCO via API v1.2.0.
========================================================

Consulta la jerarquia de habilidades europea para entender su estructura
antes de ejecutar la extraccion completa con ingestar_esco.py. Responde:
- Cuantas habilidades totales tiene ESCO
- Que pilares existen (S=competencias, K=conocimientos, T=transversales)
- Como se ve una habilidad de ejemplo con todos sus metadatos
- Que campos devuelve la API para planificar el esquema de ingestion

Recuperado de UniSabana_Dev. Sin dependencias del proyecto — solo requests.
"""

import requests
import json

API = 'https://ec.europa.eu/esco/api'
VER = 'v1.2.0'

# ============================================================================
# 1. INVENTARIO TOTAL
# ============================================================================
r = requests.get(f'{API}/search', params={
    'language': 'es', 'type': 'skill', 'limit': 1,
    'full': 'false', 'selectedVersion': VER
})
data = r.json()
print(f'Total habilidades en ESCO: {data["total"]:,}')

# ============================================================================
# 2. JERARQUIA DE PILARES — Subcategorias bajo cada pillar
# ============================================================================
pilares = {
    'S': 'http://data.europa.eu/esco/skill/335228d2-297d-4e0e-a6ee-bc6a8dc110d9',
    'K': 'http://data.europa.eu/esco/skill/c46fcb45-5c14-4ffa-abed-5a43f104bb22',
    'T': 'http://data.europa.eu/esco/skill/04a13491-b58c-4d33-8b59-8fad0d55fe9e',
}

for code, uri in pilares.items():
    r2 = requests.get(f'{API}/resource/related', params={
        'uri': uri, 'relation': 'narrowerConcept',
        'language': 'es', 'full': 'false',
        'selectedVersion': VER, 'limit': 50
    })
    d2 = r2.json()
    total = d2.get('total', '?')
    print(f'\nPilar {code} ({total} subcategorias):')
    items = d2.get('_embedded', {}).get('narrowerConcept', [])
    for item in items[:20]:
        print(f'  - [{item.get("code","")}] {item.get("title","")}')

# ============================================================================
# 3. HABILIDAD DE EJEMPLO — Estructura completa de metadatos
# ============================================================================
print('\n--- Habilidad de ejemplo (full detail) ---')
r3 = requests.get(f'{API}/search', params={
    'text': 'inteligencia artificial', 'language': 'es',
    'type': 'skill', 'limit': 3, 'full': 'true',
    'selectedVersion': VER
})
d3 = r3.json()
results = d3.get('_embedded', {}).get('results', [])
for skill in results[:2]:
    print(f'\nTitle: {skill.get("title","")}')
    print(f'URI: {skill.get("uri","")}')
    print(f'SkillType: {skill.get("skillType","")}')
    print(f'ReuseLevel: {skill.get("reuseLevel","")}')
    desc = skill.get('description', {}).get('es', {})
    if isinstance(desc, dict):
        desc = desc.get('literal', '')
    print(f'Description: {str(desc)[:200]}')
    links = skill.get('_links', {})
    broader = links.get('broaderSkillGroup', links.get('broaderHierarchyConcept', []))
    print(f'Broader: {[b.get("title","") for b in broader[:3]]}')
    print(f'Keys disponibles en el objeto: {list(skill.keys())}')
    if links:
        print(f'Link keys: {list(links.keys())}')
