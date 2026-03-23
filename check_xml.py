import requests
from lxml import etree

url = 'https://logiciel-immo-clean.vercel.app/api/export/socialimmo/OI123'
r = requests.get(url, timeout=30)
root = etree.fromstring(r.content)
all_annonces = root.findall('.//annonce')
print(f'TOTAL: {len(all_annonces)} annonces\n')

codes = set()
libelles = set()
ptypes = set()
for a in all_annonces:
    codes.add(a.findtext('.//code_type', '?'))
    libelles.add(a.findtext('.//libelle_type', '?'))
    ptypes.add(a.findtext('.//prestation/type', '?'))

print(f'code_type uniques: {sorted(codes)}')
print(f'libelle_type uniques: {sorted(libelles)}')
print(f'prestation/type uniques: {sorted(ptypes)}')
