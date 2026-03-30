# Search Engine Project

This project provides a document search service for four file formats:

- `.txt`
- `.html`
- `.pdf`
- `.xlsx`

The server searches for a keyword inside the files stored in the `data/` directory and returns useful context:

- file name
- file type
- location of the match (`line`, `page`, or `sheet` + `row`)
- text snippet around the match

Advanced search is also supported:

- boolean operators `and` / `or` and `et` / `ou`
- parentheses to group conditions
- regular expressions from the web UI or with the `re:` prefix

The project includes two ways to use the service:

- a socket server with a command-line client
- a small Flask web interface

## Project Structure

```text
search_engine_project/
├── data/
├── src/
│   ├── client.py
│   ├── server.py
│   ├── templates/
│   │   └── index.html
│   └── web_server.py
├── requirements.txt
└── README.md
```

## Dependencies

Install the required packages with:

```bash
pip install -r requirements.txt
```

The main dependencies are:

- `flask` for the web interface
- `beautifulsoup4` for HTML parsing
- `pypdf` for PDF parsing
- `pandas` and `openpyxl` for Excel parsing

## How To Use The Socket Version

Start the search server:

```bash
python3 src/server.py
```

In another terminal, start the client:

```bash
python3 src/client.py
```

Then enter a keyword. Type `q` to quit.

Examples:

```text
adam and optimization
bonjour or adam
re:Bonj.*test
```

## How To Use The Web Version

Start the web server:

```bash
python3 src/web_server.py
```

Open the following address in your browser:

```text
http://127.0.0.1:8000
```

Enter a keyword, choose the file types to search, optionally enable regex mode, and read the results in the table.

## Notes

- The application reads files from the relative `data/` directory.
- Invalid placeholder files are handled safely when possible.
- Search is case-insensitive to keep the interface simple.

## Tests

Run the automated tests with:

```bash
pytest -q
```
