"""Ingest a project's docs/FAQ into Supabase as embedded chunks.

Folder layout expected:

    ingest/data/<project_key>/project.json     <- project metadata (name, description, keywords, persona)
    ingest/data/<project_key>/*.md|*.txt|*.pdf  <- knowledge files (docs + FAQ)

Usage:
    python -m ingest.ingest_docs --project billing-portal
    python -m ingest.ingest_docs --all
    python -m ingest.ingest_docs --all --replace      # wipe a project's old chunks first

Run from the repository root with your .env populated.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from core import db
from core.embeddings import embed_texts

DATA_DIR = Path(__file__).parent / "data"
CHUNK_CHARS = 1100
CHUNK_OVERLAP = 150


def chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        # try to break on a paragraph/sentence boundary
        if end < len(text):
            for sep in ("\n\n", "\n", ". "):
                cut = text.rfind(sep, start + CHUNK_CHARS // 2, end)
                if cut != -1:
                    end = cut + len(sep)
                    break
        chunks.append(text[start:end].strip())
        start = max(end - CHUNK_OVERLAP, end) if end <= start else end - CHUNK_OVERLAP
        if start < 0:
            start = end
    return [c for c in chunks if c]


def read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            print(f"  ! skipping {path.name} (install pypdf to ingest PDFs)")
            return ""
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def ingest_project(project_key: str, replace: bool) -> None:
    folder = DATA_DIR / project_key
    if not folder.is_dir():
        print(f"! no folder for project '{project_key}' at {folder}")
        return

    meta_path = folder / "project.json"
    if not meta_path.exists():
        print(f"! missing project.json in {folder}")
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    project = db.upsert_project(
        key=project_key,
        name=meta["name"],
        description=meta["description"],
        keywords=meta.get("keywords", []),
        persona=meta.get("persona", ""),
    )
    print(f"\n== {meta['name']} ({project_key}) ==")

    if replace:
        db.delete_project_documents(project["id"])
        print("  cleared previous chunks")

    files = [
        p
        for p in sorted(folder.iterdir())
        if p.suffix.lower() in (".md", ".txt", ".pdf") and p.name != "project.json"
    ]
    if not files:
        print("  (no .md/.txt/.pdf knowledge files found)")
        return

    all_chunks: list[str] = []
    meta_per_chunk: list[dict] = []
    for f in files:
        text = read_file(f)
        for idx, ch in enumerate(chunk_text(text)):
            all_chunks.append(ch)
            meta_per_chunk.append({"source": f.name, "title": f.stem, "chunk_index": idx})
        print(f"  + {f.name}: {len([m for m in meta_per_chunk if m['source'] == f.name])} chunks")

    if not all_chunks:
        return

    print(f"  embedding {len(all_chunks)} chunks ...")
    vectors = embed_texts(all_chunks)

    rows = [
        {
            "project_id": project["id"],
            "source": m["source"],
            "title": m["title"],
            "content": ch,
            "chunk_index": m["chunk_index"],
            "embedding": vec,
        }
        for ch, vec, m in zip(all_chunks, vectors, meta_per_chunk)
    ]
    # insert in batches to stay under payload limits
    for i in range(0, len(rows), 100):
        db.insert_document_chunks(rows[i : i + 100])
    print(f"  stored {len(rows)} chunks ✓")


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest project docs/FAQ into Supabase.")
    ap.add_argument("--project", help="project_key folder under ingest/data/")
    ap.add_argument("--all", action="store_true", help="ingest every project folder")
    ap.add_argument("--replace", action="store_true", help="delete existing chunks first")
    args = ap.parse_args()

    if args.all:
        keys = [p.name for p in DATA_DIR.iterdir() if p.is_dir()] if DATA_DIR.is_dir() else []
        if not keys:
            print(f"No project folders found in {DATA_DIR}")
            return
        for k in keys:
            ingest_project(k, args.replace)
    elif args.project:
        ingest_project(args.project, args.replace)
    else:
        ap.error("pass --project <key> or --all")


if __name__ == "__main__":
    main()
