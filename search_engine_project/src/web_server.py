#!/usr/bin/env python3
"""Web application exposing the document search service."""

import os
import sys
from flask import Flask, request, jsonify, render_template

WEB_HOST = "127.0.0.1"
WEB_PORT = 8000
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import server as search_server

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)


@app.route('/')
def index():
    """Render the main search page."""
    return render_template("index.html")


@app.route('/api/search')
def api_search():
    """Return structured search results as JSON."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"query": q, "count": 0, "results": []})

    types_param = request.args.get("types", "")
    types = [t for t in types_param.split(',') if t] if types_param else None
    use_regex = request.args.get("regex", "").lower() in {"1", "true", "yes", "on"}

    try:
        results = search_server.perform_structured_search(q, types=types, use_regex=use_regex)
    except ValueError as error:
        return jsonify({"query": q, "count": 0, "results": [], "error": str(error)}), 400
    except Exception as error:
        return jsonify({"query": q, "count": 0, "results": [], "error": str(error)}), 500

    return jsonify({"query": q, "count": len(results), "results": results})


if __name__ == "__main__":
    print(f"Starting web server on http://{WEB_HOST}:{WEB_PORT}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=True)
