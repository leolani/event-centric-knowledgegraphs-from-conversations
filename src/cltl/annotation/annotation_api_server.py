"""Local API server that lets the browser-based annotation tool (annotation_tool.html) push its
exported JSON straight into a knowledge graph, via populate_ekg.populate_ekg_from_annotations.

Run with:
    python annotation_api_server.py
and keep it running while using the "Push to Knowledge Graph" button in the annotation tool.
"""

import sys
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import populate_ekg

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GRAPH_LOG_DIR = REPO_ROOT / "data" / "graph"

app = Flask(__name__)
CORS(app)  # annotation_tool.html is opened as a local file (origin "null"), so allow any origin


@app.post("/api/populate-ekg")
def populate_ekg_endpoint():
    payload = request.get_json(force=True, silent=True) or {}
    annotations = payload.get("annotations")
    kg_address = (payload.get("kg_address") or "").strip()
    clear_all = bool(payload.get("clear_all", False))

    if not annotations:
        return jsonify(error="No annotations provided."), 400
    if not kg_address:
        return jsonify(error="No knowledge graph address provided."), 400

    try:
        summary = populate_ekg.populate_ekg_from_annotations(
            annotations, kg_address=kg_address, log_dir=GRAPH_LOG_DIR, clear_all=clear_all,
        )
    except Exception as exc:
        return jsonify(error=str(exc)), 500

    return jsonify(success=True, **summary)


@app.get("/api/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050)
