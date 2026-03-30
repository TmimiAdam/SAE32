# Grille de notation - mapping des réalisations au projet

Cette grille reprend les critères fournis et indique où chaque point est couvert dans le projet, ainsi que les fichiers/commandes pour tester.

| Réalisation | Points | Couverture dans le projet | Fichier(s) / Test |
|---|---:|---|---|
| Interaction Client(s) - Serveur | 2 | IHM web (Flask) + client socket existant | `src/web_server.py`, `src/templates/index.html`, `src/client.py` |
| Gestion simultanée de plusieurs clients | 1 | Socket server multi-threaded | `src/server.py` => `start_server()` uses threads; test by connecting multiple clients |
| Choix des catégories de documents | 1 | UI filters & API support `types` param | `src/templates/index.html`, `src/web_server.py` |
| Gestion fichier txt/HTML | 2 | Implemented structured search with snippets and line numbers | `src/server.py` (search_in_txt_structured/search_in_html_structured) |
| Gestion fichier xlsx | 2 | Excel sheets parsed and sheet name returned | `src/server.py` (search_in_excel_structured) |
| Gestion fichier pdf | 2 | PDF pages searched and snippets returned | `src/server.py` (search_in_pdf_structured) |
| Recherche avancée et/ou | 1 | Requêtes booléennes `and/or` et `et/ou` avec parenthèses | `src/server.py` (`parse_search_query`, `text_matches`) |
| Recherche avancée regex | 1 | Mode regex via case à cocher web ou préfixe `re:` | `src/server.py`, `src/web_server.py`, `src/templates/index.html` |
| Informations additionnelles à la recherche | 2 | page, line, row, sheet are returned in results | `src/server.py` (location, sheet fields) |
| Qualité du code | 4 | Docstrings, fonctions modulaires, chemins relatifs, tests `pytest` | `src/*.py`, `tests/test_search.py` |
| Fichiers README et requirements | 2 | README updated; `requirements.txt` maintained | `README.md`, `requirements.txt` |

Total: 20

Pour exécuter les tests :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Pour lancer l'interface web :

```bash
python3 src/web_server.py
# ouvrir http://127.0.0.1:8000
```

