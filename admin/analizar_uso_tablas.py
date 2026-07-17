"""Analyze which tables are actually used in the app."""
import re
import os

# Files to scan
files_to_scan = [
    r'D:\UniSabana_Dev\Estudio_Contexto\data\queries.py',
    r'D:\UniSabana_Dev\Estudio_Contexto\app_streamlit.py',
    r'D:\UniSabana_Dev\Estudio_Contexto\ml_matching.py',
    r'D:\UniSabana_Dev\Estudio_Contexto\ml_matching_snies_etdh.py',
    r'D:\UniSabana_Dev\Estudio_Contexto\fuentes_datos.py',
]

used_tables = set()

# Pattern to find schema.table references
pattern = re.compile(r'(FROM|JOIN|INTO)\s+([a-z_]+)\.([a-z_0-9]+)', re.IGNORECASE)

for filepath in files_to_scan:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = pattern.findall(content)
            for match in matches:
                keyword, schema, table = match
                used_tables.add(f"{schema.lower()}.{table.lower()}")

# Also check for string interpolations like f"{schema}.{table}"
string_pattern = re.compile(r'["\']([a-z_]+)\.([a-z_0-9]+)["\']', re.IGNORECASE)
for filepath in files_to_scan:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = string_pattern.findall(content)
            for schema, table in matches:
                if schema.lower() not in ['main', 'temp', 'information_schema']:
                    used_tables.add(f"{schema.lower()}.{table.lower()}")

print(f"Total unique tables referenced in code: {len(used_tables)}")
print("\nUsed schemas:")
schemas = set(t.split('.')[0] for t in used_tables)
for schema in sorted(schemas):
    tables_in_schema = [t for t in used_tables if t.startswith(schema + '.')]
    print(f"  {schema}: {len(tables_in_schema)} tables")

print("\nAll referenced tables:")
for table in sorted(used_tables):
    print(f"  {table}")
