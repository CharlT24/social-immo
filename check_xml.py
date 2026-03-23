import requests
from lxml import etree

url = 'https://logiciel-immo-clean.vercel.app/api/export/socialimmo/OI123'
r = requests.get(url, timeout=30)
root = etree.fromstring(r.content)
for a in root.findall('.//annonce')[:15]:
    ref = a.findtext('.//reference', '?')
    code = a.findtext('.//code_type', '?')
    libelle = a.findtext('.//libelle_type', '?')
    ptype = a.findtext('.//prestation/type', '?')
    titre = (a.findtext('.//titre', '?'))[:60]
    print(f'{ref} | code_type={code} | libelle={libelle} | ptype={ptype} | {titre}')
