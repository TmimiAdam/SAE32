# Explication Du Code

Ce document explique simplement comment fonctionne le projet, sans jargon inutile.

## 1. But Du Projet

Le projet est un moteur de recherche de documents.

Il permet de chercher du texte dans plusieurs types de fichiers :

- `txt`
- `html`
- `pdf`
- `xlsx`

Le projet a deux interfaces :

- une version **socket** avec un client et un serveur Python
- une version **web** avec Flask

Le coeur du projet est dans `src/server.py`.

## 2. Vue D'Ensemble

L'idee generale est la suivante :

1. l'utilisateur saisit une requete
2. le programme analyse cette requete
3. il parcourt les fichiers du dossier `data/`
4. il applique une methode differente selon le type de fichier
5. il retourne les resultats trouves avec du contexte

Un resultat contient :

- le nom du fichier
- le type du fichier
- l'emplacement du resultat
- un extrait de texte autour du mot trouve

## 3. Structure Du Projet

### `src/server.py`

C'est le fichier principal.

Il contient :

- l'analyse de la requete
- la logique de recherche
- la gestion des fichiers `txt`, `html`, `pdf`, `xlsx`
- le serveur socket

### `src/client.py`

C'est le client en ligne de commande.

Il se connecte au serveur socket, envoie une requete, puis affiche la reponse.

### `src/web_server.py`

C'est le serveur web Flask.

Il sert la page HTML et propose une route API `/api/search` qui appelle le moteur de recherche de `server.py`.

### `src/templates/index.html`

C'est l'interface web.

Elle contient :

- le champ de recherche
- les cases a cocher pour filtrer les types de fichiers
- le bouton de recherche
- le tableau des resultats
- le JavaScript qui appelle l'API Flask

### `data/`

Ce dossier contient les documents sur lesquels la recherche est faite.

### `tests/test_search.py`

Ce fichier contient les tests automatiques.

Il verifie :

- les recherches simples
- les recherches avec `and` / `or`
- les regex
- les erreurs de requetes invalides
- l'API web

## 4. Fonctionnement Global

Le vrai point d'entree de la recherche est la fonction :

`perform_structured_search(keyword, types=None, use_regex=False)`

Cette fonction fait presque tout le travail.

### Son role

Elle :

1. nettoie la requete
2. appelle `parse_search_query()` pour comprendre le type de recherche
3. choisit quels types de fichiers parcourir
4. appelle la fonction adaptee a chaque type de fichier
5. rassemble tous les resultats dans une seule liste

## 5. Comment La Requete Est Analysee

La fonction importante est :

`parse_search_query(query, use_regex=False)`

Elle detecte trois cas.

### Cas 1 : recherche simple

Exemple :

```text
bonjour
```

Dans ce cas, le programme cherche simplement si le mot apparait dans le texte.

### Cas 2 : recherche booleenne

Exemples :

```text
adam and optimization
bonjour ou adam
(adam and optimization) or test
```

Dans ce cas :

- `and` et `et` veulent dire la meme chose
- `or` et `ou` veulent dire la meme chose
- les parentheses sont prises en compte

Le code fait plusieurs etapes.

#### a. `tokenize_boolean_query(query)`

Cette fonction decoupe la requete en morceaux :

- termes
- operateurs
- parentheses

Exemple :

```text
adam and optimization
```

devient en idee :

- `adam`
- `AND`
- `optimization`

#### b. `infix_tokens_to_postfix(tokens)`

Cette fonction transforme l'expression en notation postfixee.

Pourquoi ?

Parce que c'est plus simple a evaluer avec une pile.

Exemple :

```text
adam and optimization
```

devient :

```text
adam optimization AND
```

#### c. `validate_postfix_tokens(postfix_tokens)`

Cette fonction verifie que la requete est correcte.

Elle empeche des requetes invalides comme :

```text
adam and or optimization
```

ou des parentheses mal fermees.

## 6. Comment Le Texte Est Teste

La fonction centrale est :

`text_matches(text, search_spec)`

Son role est de dire : "est-ce que ce morceau de texte correspond a la requete ?"

### Si la recherche est simple

Le code appelle :

`contains_keyword(text, keyword)`

Cette fonction fait juste une recherche insensible a la casse.

Donc :

- `Adam`
- `adam`
- `ADAM`

sont consideres comme identiques.

### Si la recherche est une regex

Le programme compile la regex avec `re.compile(..., re.IGNORECASE)` puis applique le motif sur le texte.

### Si la recherche est booleenne

Le programme lit la forme postfixee et utilise une pile :

- chaque terme donne `True` ou `False`
- `AND` combine deux resultats
- `OR` combine deux resultats

Au final, on obtient un seul booleen.

## 7. Comment L'Extrait Est Construit

Quand un resultat est trouve, le programme ne renvoie pas tout le document.

Il construit un petit extrait avec :

`build_snippet(text, search_spec)`

Cette fonction :

1. normalise les espaces
2. cherche la position du premier match avec `find_match_bounds()`
3. extrait un morceau de texte autour du match

Le but est d'aider l'utilisateur a comprendre pourquoi le resultat est apparu.

## 8. Recherche Par Type De Fichier

Chaque type de document a sa propre fonction.

## 8.1 TXT

Fonction :

`search_txt_file(filepath, search_spec)`

En pratique, elle appelle :

`search_plain_text_lines(filepath, search_spec, "txt")`

Le fichier est lu ligne par ligne.

Pour chaque ligne :

- on teste si elle correspond a la requete
- si oui, on ajoute un resultat avec `line:numero`

## 8.2 HTML

Fonction :

`search_html_file(filepath, search_spec)`

Le code utilise `BeautifulSoup` pour extraire le texte visible de la page HTML.

Ensuite :

- il decoupe ce texte en lignes
- il cherche les correspondances
- il renvoie `line:numero`

Donc on ne cherche pas dans les balises HTML brutes, mais dans le texte utile.

## 8.3 PDF

Fonction :

`search_pdf_file(filepath, search_spec)`

Le code verifie d'abord si le fichier ressemble bien a un vrai PDF avec la signature `%PDF`.

Ensuite il utilise `pypdf` pour :

- ouvrir le PDF
- lire les pages
- extraire le texte de chaque page

Si une page correspond, le resultat contient :

- le nom du fichier
- le type `pdf`
- `page:numero`
- un extrait

Si la lecture PDF echoue, le code essaie un fallback plus simple en lecture texte.

## 8.4 XLSX

Fonction :

`search_xlsx_file(filepath, search_spec)`

Le code verifie d'abord si le fichier est bien une archive ZIP valide, car un `.xlsx` est en realite un format base sur ZIP.

Ensuite il utilise `pandas` pour :

- ouvrir le classeur Excel
- lire chaque feuille
- parcourir chaque ligne

Chaque ligne est convertie en texte avec :

```text
colonne1 | colonne2 | colonne3
```

Puis le moteur teste si cette ligne correspond a la requete.

Le resultat indique :

```text
sheet:NomDeFeuille row:numero
```

Le `+ 2` dans le code vient du fait que :

- l'index Python commence a `0`
- dans un tableau Excel, la premiere ligne utile de donnees est souvent apres la ligne d'entete

## 9. Construction D'Un Resultat

La fonction :

`build_hit(filepath, file_type, location, snippet)`

cree un dictionnaire standard.

Exemple :

```python
{
    "file": "adam.html",
    "path": "../data/adam.html",
    "type": "html",
    "location": "line:10",
    "snippet": "Adam is a popular optimization algorithm ..."
}
```

L'avantage est que toutes les interfaces recoivent le meme format de donnees.

## 10. Partie Socket

Le projet contient aussi une version client/serveur classique.

### Serveur socket

Dans `server.py`, les fonctions importantes sont :

- `start_server()`
- `handle_client(connection, address)`

### `start_server()`

Cette fonction :

1. cree une socket TCP
2. fait un `bind` sur `127.0.0.1:52300`
3. ecoute les connexions entrantes
4. accepte les clients
5. cree un thread pour chaque client

L'interet du thread est de gerer plusieurs clients en meme temps.

### `handle_client(connection, address)`

Cette fonction dialogue avec un client :

1. elle envoie un message d'accueil
2. elle attend une requete
3. elle lance la recherche
4. elle renvoie le resultat texte
5. elle recommence jusqu'a `q`

## 11. Partie Client Socket

Dans `src/client.py`, le point d'entree est :

`start_client()`

Cette fonction :

1. cree une socket cliente
2. se connecte au serveur
3. affiche le message d'accueil
4. lit ce que l'utilisateur tape
5. envoie la requete au serveur
6. affiche la reponse

Donc :

- `server.py` attend et traite
- `client.py` envoie et affiche

## 12. Partie Web

Dans `src/web_server.py`, Flask sert de passerelle entre la page web et le moteur de recherche.

### Route `/`

La fonction `index()` affiche la page HTML `index.html`.

### Route `/api/search`

La fonction `api_search()` :

1. recupere la requete `q`
2. recupere les types selectionnes
3. recupere l'option regex
4. appelle `perform_structured_search()`
5. renvoie les resultats en JSON

Si la requete est invalide, Flask renvoie une erreur `400`.

Si un autre probleme arrive, Flask renvoie une erreur `500`.

## 13. Interface Web HTML + JavaScript

Dans `src/templates/index.html`, il y a deux parties :

- le HTML visible
- le JavaScript pour faire la recherche

### Partie HTML

Elle affiche :

- une barre de recherche
- des cases a cocher `TXT`, `HTML`, `PDF`, `XLSX`
- une case pour activer la regex
- un tableau de resultats

### Partie JavaScript

La fonction importante est :

`doSearch()`

Elle :

1. lit le texte saisi
2. lit les filtres cochés
3. construit l'URL `/api/search?...`
4. fait un `fetch()`
5. recupere le JSON
6. remplit le tableau HTML

### Surlignage

La fonction `highlight(text, q, useRegex)` met en evidence les mots trouves avec la balise HTML `<mark>`.

Le surlignage n'est fait que pour les recherches non regex.

### Securite minimale

La fonction `escapeHtml()` sert a eviter qu'un texte affiche dans la page soit interprete comme du vrai HTML.

C'est une protection basique contre l'injection HTML.

## 14. Ce Que Le Projet Fait Bien

Voici les points solides du code.

- la logique de recherche est separee des interfaces
- les formats de fichiers sont geres dans des fonctions distinctes
- la recherche avancee est reelle : booleen + regex
- les resultats sont uniformes quel que soit le type de document
- l'interface web est simple a utiliser
- le serveur socket gere plusieurs clients avec des threads
- il y a des tests automatiques

## 15. Limites Du Projet

Voici les limites que tu peux reconnaitre a l'oral si on te questionne.

- la recherche est basee sur un parcours complet des fichiers, donc ce n'est pas optimise pour de tres gros volumes
- le `AND` et le `OR` s'appliquent a une unite de lecture locale :
  - une ligne pour `txt` et `html`
  - une page pour `pdf`
  - une ligne Excel pour `xlsx`
- il n'y a pas d'indexation avancee
- le classement des resultats est simple, il n'y a pas de score de pertinence
- l'import des tests depend du lancement correct de Python depuis le dossier du projet

## 16. Exemple Concret De Parcours

Prenons la requete :

```text
adam and optimization
```

Le programme fait ceci :

1. `perform_structured_search()` recoit la requete
2. `parse_search_query()` detecte une requete booleenne
3. `tokenize_boolean_query()` decoupe en `adam`, `AND`, `optimization`
4. `infix_tokens_to_postfix()` transforme en postfixe
5. le programme parcourt les fichiers du type choisi
6. pour chaque ligne ou page ou ligne Excel, `text_matches()` verifie la condition
7. si la condition est vraie, `build_snippet()` construit un extrait
8. `build_hit()` cree le resultat
9. la liste de resultats est renvoyee au client socket ou a l'interface web

## 17. Phrase Simple Pour La Soutenance

Si tu dois expliquer rapidement ton code, tu peux dire :

> J'ai construit un moteur de recherche de documents en Python. Le coeur du projet est un module qui analyse une requete, parcourt plusieurs types de fichiers et renvoie des resultats uniformes avec un contexte. Ensuite, j'ai connecte ce moteur a deux interfaces : une interface socket et une interface web Flask.

Tu peux aussi dire :

> J'ai separe la logique metier de l'interface. Comme ca, le meme moteur de recherche peut etre reutilise dans plusieurs modes d'utilisation.

## 18. Ce Qu'Il Faut Absolument Retenir

Si tu ne dois retenir que quelques idees :

1. `server.py` contient le vrai moteur
2. `web_server.py` sert juste d'interface HTTP vers ce moteur
3. `client.py` est le client socket
4. `index.html` affiche les resultats dans le navigateur
5. `perform_structured_search()` est la fonction la plus importante
6. `parse_search_query()` gere simple, booleen et regex
7. chaque type de fichier a sa propre fonction de lecture

## 19. Comment Reviser Rapidement

Ordre conseille pour relire ton projet :

1. `src/server.py`
2. `src/web_server.py`
3. `src/templates/index.html`
4. `src/client.py`
5. `tests/test_search.py`

Si tu comprends ces 5 fichiers, tu comprends l'essentiel du projet.
