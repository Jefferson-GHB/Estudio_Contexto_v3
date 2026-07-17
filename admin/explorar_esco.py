"""Probe ESCO API hierarchy."""
import requests
import json

API = 'https://ec.europa.eu/esco/api'
VER = 'v1.2.0'

# How many total skills?
r = requests.get(f'{API}/search', params={
    'language': 'es', 'type': 'skill', 'limit': 1,
    'full': 'false', 'selectedVersion': VER
})
data = r.json()
print(f'Total skills in ESCO: {data["total"]}')

# Check broader categories under each pillar
pillars = {
    'S': 'http://data.europa.eu/esco/skill/335228d2-297d-4e0e-a6ee-bc6a8dc110d9',
    'K': 'http://data.europa.eu/esco/skill/c46fcb45-5c14-4ffa-abed-5a43f104bb22',
    'T': 'http://data.europa.eu/esco/skill/04a13491-b58c-4d33-8b59-8fad0d55fe9e',
}

for code, uri in pillars.items():
    r2 = requests.get(f'{API}/resource/related', params={
        'uri': uri, 'relation': 'narrowerConcept',
        'language': 'es', 'full': 'false',
        'selectedVersion': VER, 'limit': 50
    })
    d2 = r2.json()
    total = d2.get('total', '?')
    print(f'\nPillar {code} ({total} sub-categories):')
    items = d2.get('_embedded', {}).get('narrowerConcept', [])
    for item in items[:20]:
        print(f'  - [{item.get("code","")}] {item.get("title","")}')

# Get one sample skill with full detail
print('\n--- Sample full skill ---')
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
    print(f'Keys: {list(skill.keys())}')
    if links:
        print(f'Link keys: {list(links.keys())}')
