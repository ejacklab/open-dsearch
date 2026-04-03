#!/usr/bin/env python3
"""
Push search results to ZVec vector collection for semantic search.
Supports concurrent access via file locking (fcntl.flock).

Usage:
    python push_zvec.py add --title "Title" --url "url" --snippet "text" --topic "topic"
    python push_zvec.py add --batch < results.jsonl
    python push_zvec.py query "semantic search query" --top 5
    python push_zvec.py stats
    python push_zvec.py clear --topic "topic"

Requires: zvec (pip install zvec)
"""

import argparse
import fcntl
import json
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

import zvec

DEFAULT_COLLECTION_DIR = Path.home() / ".open-dsearch" / "zvec_data"

# Module-level cache — ZVec locks files, can't reopen within same process
_COLLECTION_CACHE: dict = {}

# Embedding dimension — set on first embed (BM25 = 4D)
_EMBEDDING_DIM: Optional[int] = None


def _lock_path(collection_path: Path) -> Path:
    """Path to the exclusive write-lock file."""
    return collection_path / ".push.lock"


@contextmanager
def _write_lock(collection_path: Path):
    """Acquire exclusive blocking lock on the collection before any write."""
    collection_path.mkdir(parents=True, exist_ok=True)
    lock_file = _lock_path(collection_path)
    lock_fd = open(lock_file, "w")
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)  # blocking exclusive
        yield
    finally:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()


def _bm25_embed(text: str) -> List[float]:
    """BM25 pseudo-embedding via ZVec (always 4D, float32 for ZVec FP32 schema)."""
    import numpy as np

    try:
        emb = zvec.BM25EmbeddingFunction(text)
        if hasattr(emb, "astype"):
            emb = emb.astype(np.float32)
        if hasattr(emb, "tolist"):
            return emb.tolist()
        if isinstance(emb, list):
            return [float(x) for x in emb]
        return [float(x) for x in emb]
    except Exception:
        pass

    # Fallback: deterministic hash (4D)
    import hashlib

    vec = [0.0] * 4
    for i, word in enumerate(text.lower().split()[:4]):
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        vec[i] = (h % 1000) / 1000.0
    mag = sum(v * v for v in vec) ** 0.5 or 1
    return [float(v / mag) for v in vec]


def _get_embedding(text: str) -> List[float]:
    """Get embedding. Always returns 4D (BM25)."""
    global _EMBEDDING_DIM

    emb = _bm25_embed(text)
    _EMBEDDING_DIM = len(emb)
    return emb


def _make_doc_id(url: str) -> str:
    """MD5 hash of URL → 16-char hex doc_id. Safe for ZVec (max 50 chars, no special chars)."""
    import hashlib

    return hashlib.md5(url.encode()).hexdigest()[:16]


def _get_collection(path: Path):
    """Open or create ZVec collection. ZVec locks files — must use cache.

    Logic:
    1. Check cache (prevents double-open within same process)
    2. Try zvec.open() for existing collection
    3. If open fails, remove stale state and create_and_open fresh
    """
    path_str = str(path)
    if path_str in _COLLECTION_CACHE:
        return _COLLECTION_CACHE[path_str]

    # Try to open existing collection first
    try:
        col = zvec.open(path_str)
        _COLLECTION_CACHE[path_str] = col
        return col
    except Exception:
        pass

    # No valid collection — remove whatever is there and create fresh.
    # create_and_open requires the directory to not exist.
    if path.exists():
        shutil.rmtree(path_str)

    dim = _EMBEDDING_DIM or 4
    schema = zvec.CollectionSchema(
        name="research",
        vectors=zvec.VectorSchema("embedding", zvec.DataType.VECTOR_FP32, dim),
        fields=[
            zvec.FieldSchema("title", zvec.DataType.STRING),
            zvec.FieldSchema("url", zvec.DataType.STRING),
            zvec.FieldSchema("snippet", zvec.DataType.STRING),
            zvec.FieldSchema("topic", zvec.DataType.STRING),
            zvec.FieldSchema("source", zvec.DataType.STRING),
        ],
    )
    col = zvec.create_and_open(path_str, schema)
    _COLLECTION_CACHE[path_str] = col
    return col


# ── Public API ───────────────────────────────────────────────────────────────


def push_result(
    title: str,
    url: str,
    snippet: str,
    topic: str,
    source: str = "unknown",
    collection_path: Optional[Path] = None,
) -> bool:
    """Push a single result to the collection. Returns True on success."""
    path = collection_path or DEFAULT_COLLECTION_DIR
    try:
        with _write_lock(path):
            col = _get_collection(path)
            embedding = _get_embedding(f"{title}. {snippet}")
            doc = zvec.Doc(
                id=_make_doc_id(url),
                vectors={"embedding": embedding},
                fields={
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "topic": topic,
                    "source": source,
                },
            )
            col.insert(doc)
            col.flush()
        return True
    except Exception as e:
        import sys as _sys

        print(f"[push_zvec] push_result failed: {e}", file=_sys.stderr)
        return False


def push_batch(
    results: List[dict],
    topic: str,
    collection_path: Optional[Path] = None,
) -> int:
    """Push multiple results. Returns count of successfully indexed docs."""
    if not results:
        return 0

    path = collection_path or DEFAULT_COLLECTION_DIR
    try:
        with _write_lock(path):
            col = _get_collection(path)
            docs = []
            for r in results:
                embedding = _get_embedding(f"{r['title']}. {r.get('snippet', '')}")
                docs.append(
                    zvec.Doc(
                        id=_make_doc_id(r["url"]),
                        vectors={"embedding": embedding},
                        fields={
                            "title": r["title"],
                            "url": r["url"],
                            "snippet": r.get("snippet", ""),
                            "topic": topic,
                            "source": r.get("source", "unknown"),
                        },
                    )
                )
            if docs:
                col.insert(docs)
                col.flush()
            return len(docs)
    except Exception as e:
        import sys as _sys

        print(f"[push_zvec] push_batch failed: {e}", file=_sys.stderr)
        return 0


def query_collection(
    query_text: str,
    top_k: int = 5,
    topic: Optional[str] = None,
    collection_path: Optional[Path] = None,
) -> List[dict]:
    """Semantic search over accumulated results."""
    col = _get_collection(collection_path or DEFAULT_COLLECTION_DIR)
    query_emb = _get_embedding(query_text)
    vector_query = zvec.VectorQuery("embedding", vector=query_emb)
    output_fields = ["title", "url", "snippet", "topic", "source"]
    if topic:
        results = col.query(
            vectors=vector_query,
            topk=top_k,
            filter=f"topic = '{topic}'",
            output_fields=output_fields,
        )
    else:
        results = col.query(
            vectors=vector_query, topk=top_k, output_fields=output_fields
        )
    return [{k: r.fields.get(k, "") for k in output_fields} for r in results]


def get_stats(collection_path: Optional[Path] = None) -> dict:
    try:
        col = _get_collection(collection_path or DEFAULT_COLLECTION_DIR)
        s = col.stats
        return {"doc_count": s.doc_count}
    except Exception:
        return {}


def clear_topic(topic: str, collection_path: Optional[Path] = None):
    path = collection_path or DEFAULT_COLLECTION_DIR
    try:
        with _write_lock(path):
            col = _get_collection(path)
            col.delete_by_filter(f"topic = '{topic}'")
            col.flush()
        print(f"Cleared topic: {topic}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="ZVec vector store for open-dsearch research results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python push_zvec.py add --title "Rust async" --url "https://..." \\
      --snippet "Guide" --topic "rust-research"
  cat results.jsonl | python push_zvec.py add --batch --topic "my-topic"
  python push_zvec.py query "async patterns" --top 5
  python push_zvec.py clear --topic "old-topic"
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("--title")
    add.add_argument("--url")
    add.add_argument("--snippet", default="")
    add.add_argument("--topic", "-t", default="default")
    add.add_argument("--source", "-s", default="cli")
    add.add_argument("--batch", action="store_true")
    add.add_argument("--collection", "-c")

    query = sub.add_parser("query")
    query.add_argument("query", nargs="?")
    query.add_argument("--top", "-n", type=int, default=5)
    query.add_argument("--topic", "-t")
    query.add_argument("--list", action="store_true")
    query.add_argument("--collection", "-c")

    stats = sub.add_parser("stats")
    stats.add_argument("--collection", "-c")

    clear = sub.add_parser("clear")
    clear.add_argument("--topic", "-t", required=True)
    clear.add_argument("--collection", "-c")

    args = parser.parse_args()
    collection_path = Path(args.collection) if args.collection else None

    if args.command == "add":
        if args.batch:
            results = [json.loads(l) for l in sys.stdin if l.strip()]
            count = push_batch(results, args.topic, collection_path)
            print(f"Indexed {count} results")
        else:
            if not args.title or not args.url:
                print("--title and --url required", file=sys.stderr)
                sys.exit(1)
            ok = push_result(
                args.title, args.url, args.snippet, args.topic,
                args.source, collection_path
            )
            if ok:
                print(f"Indexed: {args.title[:50]}")
            else:
                sys.exit(1)

    elif args.command == "query":
        if args.list:
            print(get_stats(collection_path))
            return
        if not args.query:
            print("--query required", file=sys.stderr)
            sys.exit(1)
        results = query_collection(
            args.query, top_k=args.top, topic=args.topic,
            collection_path=collection_path
        )
        if not results:
            print("No results found.")
            return
        print(f"\nTop {len(results)} for: {args.query!r}\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] {r['title']}\n    {r['url']}\n    {r['snippet'][:100]}\n")

    elif args.command == "stats":
        print(get_stats(collection_path))

    elif args.command == "clear":
        clear_topic(args.topic, collection_path)


if __name__ == "__main__":
    main()
