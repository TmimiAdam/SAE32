"""Socket search server for TXT, HTML, PDF and XLSX documents."""

import contextlib
import glob
import io
import os
import re
import socket
import threading
import zipfile


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 52300
BUFFER_SIZE = 4096
SOCKET_BACKLOG = 5
ENDING_MESSAGE = "q"

DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "..", "data")
TEXT_ENCODING = "utf-8"
TEXT_ERRORS = "ignore"
PDF_SIGNATURE = b"%PDF"
PDF_SIGNATURE_SIZE = 5
SNIPPET_CONTEXT = 40
MAX_SNIPPET_LENGTH = 200

SUPPORTED_TYPES = ("txt", "html", "pdf", "xlsx")
FILE_PATTERNS = {
    "txt": "*.txt",
    "html": "*.html",
    "pdf": "*.pdf",
    "xlsx": "*.xlsx",
}

BOOLEAN_OPERATOR_ALIASES = {
    "and": "AND",
    "et": "AND",
    "or": "OR",
    "ou": "OR",
}
BOOLEAN_OPERATOR_PRECEDENCE = {
    "AND": 2,
    "OR": 1,
}
REGEX_PREFIXES = ("re:", "regex:")


def is_regex_search(query, use_regex=False):
    """Return True when the query should be evaluated as a regex."""
    if use_regex:
        return True

    lowered_query = query.lower()
    return any(lowered_query.startswith(prefix) for prefix in REGEX_PREFIXES)


def extract_regex_pattern(query):
    """Return the regex pattern without the optional prefix."""
    lowered_query = query.lower()
    for prefix in REGEX_PREFIXES:
        if lowered_query.startswith(prefix):
            return query[len(prefix):].strip()
    return query


def tokenize_boolean_query(query):
    """Split a boolean query into terms, operators and parentheses."""
    raw_tokens = re.split(r"(\(|\)|\b(?:and|or|et|ou)\b)", query, flags=re.IGNORECASE)
    tokens = []

    for raw_token in raw_tokens:
        stripped_token = raw_token.strip()
        if not stripped_token:
            continue

        lowered_token = stripped_token.lower()
        if stripped_token in {"(", ")"}:
            tokens.append({"type": "PAREN", "value": stripped_token})
        elif lowered_token in BOOLEAN_OPERATOR_ALIASES:
            tokens.append(
                {
                    "type": "OPERATOR",
                    "value": BOOLEAN_OPERATOR_ALIASES[lowered_token],
                }
            )
        else:
            tokens.append({"type": "TERM", "value": stripped_token})

    return tokens


def infix_tokens_to_postfix(tokens):
    """Convert infix boolean tokens to postfix notation."""
    output = []
    operators = []

    for token in tokens:
        if token["type"] == "TERM":
            output.append(token)
            continue

        if token["type"] == "OPERATOR":
            while operators:
                top_token = operators[-1]
                if top_token["type"] != "OPERATOR":
                    break
                if BOOLEAN_OPERATOR_PRECEDENCE[top_token["value"]] < BOOLEAN_OPERATOR_PRECEDENCE[token["value"]]:
                    break
                output.append(operators.pop())
            operators.append(token)
            continue

        if token["value"] == "(":
            operators.append(token)
            continue

        while operators and operators[-1]["value"] != "(":
            output.append(operators.pop())

        if not operators:
            raise ValueError("Parentheses are not balanced in the query.")

        operators.pop()

    while operators:
        token = operators.pop()
        if token["value"] == "(":
            raise ValueError("Parentheses are not balanced in the query.")
        output.append(token)

    return output


def validate_postfix_tokens(postfix_tokens):
    """Validate that the postfix expression is executable."""
    stack_size = 0

    for token in postfix_tokens:
        if token["type"] == "TERM":
            stack_size += 1
            continue

        if stack_size < 2:
            raise ValueError("The boolean query is invalid.")
        stack_size -= 1

    if stack_size != 1:
        raise ValueError("The boolean query is invalid.")


def parse_search_query(query, use_regex=False):
    """Build a normalized search specification from the user query."""
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("The query cannot be empty.")

    if is_regex_search(cleaned_query, use_regex=use_regex):
        pattern = extract_regex_pattern(cleaned_query)
        if not pattern:
            raise ValueError("The regex pattern cannot be empty.")

        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error as error:
            raise ValueError(f"Invalid regex: {error}") from error

        return {
            "mode": "regex",
            "query": cleaned_query,
            "pattern": compiled_pattern,
            "terms": [],
        }

    tokens = tokenize_boolean_query(cleaned_query)
    has_boolean_syntax = any(token["type"] != "TERM" for token in tokens)

    if not has_boolean_syntax:
        return {
            "mode": "term",
            "query": cleaned_query,
            "pattern": None,
            "terms": [cleaned_query],
            "postfix": [{"type": "TERM", "value": cleaned_query}],
        }

    postfix_tokens = infix_tokens_to_postfix(tokens)
    if not postfix_tokens:
        raise ValueError("The query is invalid.")

    validate_postfix_tokens(postfix_tokens)

    terms = [token["value"] for token in postfix_tokens if token["type"] == "TERM"]
    return {
        "mode": "boolean",
        "query": cleaned_query,
        "pattern": None,
        "terms": terms,
        "postfix": postfix_tokens,
    }


def contains_keyword(text, keyword):
    """Return True when the keyword is present in the text."""
    return keyword.lower() in text.lower()


def find_match_bounds(text, search_spec):
    """Return the bounds of the first relevant match inside the text."""
    if search_spec["mode"] == "regex":
        match = search_spec["pattern"].search(text)
        if match is None:
            return None
        return match.span()

    best_match = None
    lowered_text = text.lower()

    for term in search_spec["terms"]:
        match_index = lowered_text.find(term.lower())
        if match_index < 0:
            continue

        match_bounds = (match_index, match_index + len(term))
        if best_match is None or match_bounds[0] < best_match[0]:
            best_match = match_bounds

    return best_match


def build_snippet(text, search_spec):
    """Return a compact text snippet centered around the first match."""
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return ""

    match_bounds = find_match_bounds(normalized_text, search_spec)
    if match_bounds is None:
        return normalized_text[:MAX_SNIPPET_LENGTH]

    start_index = max(0, match_bounds[0] - SNIPPET_CONTEXT)
    end_index = start_index + MAX_SNIPPET_LENGTH
    return normalized_text[start_index:end_index]


def text_matches(text, search_spec):
    """Return True when the text matches the normalized search specification."""
    if search_spec["mode"] == "regex":
        return bool(search_spec["pattern"].search(text))

    if search_spec["mode"] == "term":
        return contains_keyword(text, search_spec["terms"][0])

    stack = []
    for token in search_spec["postfix"]:
        if token["type"] == "TERM":
            stack.append(contains_keyword(text, token["value"]))
            continue

        if len(stack) < 2:
            raise ValueError("The boolean query is invalid.")

        right_operand = stack.pop()
        left_operand = stack.pop()

        if token["value"] == "AND":
            stack.append(left_operand and right_operand)
        else:
            stack.append(left_operand or right_operand)

    if len(stack) != 1:
        raise ValueError("The boolean query is invalid.")

    return stack[0]


def build_hit(filepath, file_type, location, snippet):
    """Create a normalized search result entry."""
    return {
        "file": os.path.basename(filepath),
        "path": os.path.relpath(filepath, start=os.path.dirname(__file__)),
        "type": file_type,
        "location": location,
        "snippet": snippet,
    }


def search_plain_text_lines(filepath, search_spec, file_type):
    """Search a line-based text file and return matching hits."""
    hits = []

    try:
        with open(filepath, "r", encoding=TEXT_ENCODING, errors=TEXT_ERRORS) as file_handle:
            for line_number, line in enumerate(file_handle, start=1):
                if text_matches(line, search_spec):
                    hits.append(
                        build_hit(
                            filepath,
                            file_type,
                            f"line:{line_number}",
                            build_snippet(line, search_spec),
                        )
                    )
    except OSError as error:
        print(f"[Error] Could not read {file_type.upper()} file {filepath}: {error}")

    return hits


def search_txt_file(filepath, search_spec):
    """Search a TXT file and return matching hits."""
    return search_plain_text_lines(filepath, search_spec, "txt")


def search_html_file(filepath, search_spec):
    """Search visible text extracted from an HTML file."""
    hits = []

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print(f"[Warning] BeautifulSoup is not installed; skipping HTML file {filepath}")
        return hits

    try:
        with open(filepath, "r", encoding=TEXT_ENCODING, errors=TEXT_ERRORS) as file_handle:
            soup = BeautifulSoup(file_handle, "html.parser")

        for line_number, line in enumerate(soup.get_text().splitlines(), start=1):
            cleaned_line = line.strip()
            if cleaned_line and text_matches(cleaned_line, search_spec):
                hits.append(
                    build_hit(
                        filepath,
                        "html",
                        f"line:{line_number}",
                        build_snippet(cleaned_line, search_spec),
                    )
                )
    except OSError as error:
        print(f"[Error] Could not read HTML file {filepath}: {error}")

    return hits


def search_pdf_file(filepath, search_spec):
    """Search a PDF file and return matching hits."""
    hits = []

    try:
        with open(filepath, "rb") as file_handle:
            header = file_handle.read(PDF_SIGNATURE_SIZE)
    except OSError as error:
        print(f"[Error] Could not open PDF file {filepath}: {error}")
        return hits

    if not header.startswith(PDF_SIGNATURE):
        return search_plain_text_lines(filepath, search_spec, "pdf")

    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"[Warning] pypdf is not installed; skipping PDF file {filepath}")
        return hits

    try:
        with contextlib.redirect_stderr(io.StringIO()):
            reader = PdfReader(filepath, strict=False)
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if text_matches(page_text, search_spec):
                hits.append(
                    build_hit(
                        filepath,
                        "pdf",
                        f"page:{page_number}",
                        build_snippet(page_text, search_spec),
                    )
                )
    except Exception:
        return search_plain_text_lines(filepath, search_spec, "pdf")

    return hits


def search_xlsx_file(filepath, search_spec):
    """Search an XLSX file and return matching hits."""
    hits = []

    if not zipfile.is_zipfile(filepath):
        return search_plain_text_lines(filepath, search_spec, "xlsx")

    try:
        import pandas as pd
    except ImportError:
        print(f"[Warning] pandas or openpyxl is not installed; skipping XLSX file {filepath}")
        return hits

    try:
        workbook = pd.ExcelFile(filepath)
        for sheet_name in workbook.sheet_names:
            dataframe = workbook.parse(sheet_name=sheet_name, dtype=str)
            for row_index, row in dataframe.fillna("").iterrows():
                row_text = " | ".join(row.astype(str).tolist())
                if text_matches(row_text, search_spec):
                    hits.append(
                        build_hit(
                            filepath,
                            "xlsx",
                            f"sheet:{sheet_name} row:{row_index + 2}",
                            build_snippet(row_text, search_spec),
                        )
                    )
    except Exception as error:
        print(f"[Error] Could not read XLSX file {filepath}: {error}")

    return hits


SEARCH_HANDLERS = {
    "txt": search_txt_file,
    "html": search_html_file,
    "pdf": search_pdf_file,
    "xlsx": search_xlsx_file,
}


def get_files_for_type(file_type):
    """Return all files matching the requested supported type."""
    pattern = FILE_PATTERNS[file_type]
    return glob.glob(os.path.join(DATA_DIRECTORY, pattern))


def perform_structured_search(keyword, types=None, use_regex=False):
    """Return structured search results for the selected file types."""
    cleaned_keyword = keyword.strip()
    if not cleaned_keyword:
        return []

    search_spec = parse_search_query(cleaned_keyword, use_regex=use_regex)
    requested_types = types or list(SUPPORTED_TYPES)
    results = []

    for file_type in requested_types:
        if file_type not in SEARCH_HANDLERS:
            continue
        for filepath in get_files_for_type(file_type):
            results.extend(SEARCH_HANDLERS[file_type](filepath, search_spec))

    return results


def format_results_for_client(keyword, results):
    """Format structured results for the socket client."""
    if not results:
        return f"\n--- Search Results for '{keyword}' ---\nNo matches found in any file."

    lines = [f"\n--- Search Results for '{keyword}' ---"]
    for hit in results:
        lines.append(
            f"{hit['file']} [{hit['type']}] {hit['location']}: {hit['snippet']}"
        )
    return "\n".join(lines)


def perform_global_search(keyword):
    """Return a plain-text representation of all search results."""
    results = perform_structured_search(keyword)
    return format_results_for_client(keyword, results)


def handle_client(connection, address):
    """Serve one connected socket client."""
    with connection:
        print(f"[Server] Connected by {address}")
        welcome_message = "Welcome! Enter a keyword to search (or 'q' to quit)."
        connection.sendall(welcome_message.encode(TEXT_ENCODING))

        while True:
            try:
                data = connection.recv(BUFFER_SIZE)
                if not data:
                    break

                client_message = data.decode(TEXT_ENCODING).strip()
                if client_message.lower() == ENDING_MESSAGE:
                    print(f"[Server] Client {address} disconnected.")
                    break

                print(f"[Server] Searching for: {client_message}")
                search_result = perform_global_search(client_message)
                final_response = search_result + "\n[Server] Next keyword: "
                connection.sendall(final_response.encode(TEXT_ENCODING))
            except ConnectionResetError:
                print(f"[Server] Connection lost with {address}.")
                break


def start_server():
    """Start the socket server and accept incoming client connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        try:
            server_socket.bind((SERVER_HOST, SERVER_PORT))
            server_socket.listen(SOCKET_BACKLOG)
            print(f"[Server] Server running on {SERVER_HOST}:{SERVER_PORT}")
            print(f"[Server] Reading files from: {DATA_DIRECTORY}")

            while True:
                print("[Server] Waiting for client...")
                connection, address = server_socket.accept()
                worker = threading.Thread(
                    target=handle_client,
                    args=(connection, address),
                    daemon=True,
                )
                worker.start()
        except OSError as error:
            print(f"[Error] Server socket error: {error}")


if __name__ == "__main__":
    start_server()
