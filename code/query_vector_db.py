import os
import argparse
import time
from chromadb import PersistentClient
from dotenv import load_dotenv
import openai
from typing import Dict

# ---- Load OpenAI config ----
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env file.")


# ---- Embedding function with retries ----
def get_embedding(text: str, model="text-embedding-3-small", retries=3):
    if not text.strip():
        raise ValueError("Empty or whitespace-only query cannot be embedded.")
    for attempt in range(retries):
        try:
            response = openai.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"⚠️ Embedding failed ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


# ---- CLI args ----
parser = argparse.ArgumentParser(description="Query a Chroma vector DB collection.")
parser.add_argument("--db", type=str, default="code_docs", help="Collection name to query (default: code_docs)")
parser.add_argument("--query", type=str, required=True, help="Search query text")
parser.add_argument("--top_k", type=int, default=3, help="Number of results to return (default: 3)")
parser.add_argument("--tag", type=str, choices=["source", "test", "doc"], help="Optional filter by document type")
parser.add_argument("--language", type=str, help="Optional filter by language (python/java/markdown)")
parser.add_argument("--json", action="store_true", help="Return results in JSON format")

args = parser.parse_args()

# ---- Load Chroma collection ----
client = PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name=args.db)

# ---- Build metadata filter ----
metadata_filter: Dict[str, str] = {}
if args.tag:
    metadata_filter["tag"] = args.tag
if args.language:
    metadata_filter["language"] = args.language

# ---- Embed query ----
query_embedding = get_embedding(args.query)

# ---- Perform query ----
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=args.top_k,
    where=metadata_filter if metadata_filter else None
)

# ---- Handle no results ----
if not results["documents"] or not results["documents"][0]:
    print(f"❌ No results found for query: '{args.query}'")
    exit(0)

# ---- Output ----
if args.json:
    import json
    output = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        output.append({
            "file_path": meta.get("file_path"),
            "file_name": meta.get("file_name"),
            "tag": meta.get("tag"),
            "language": meta.get("language"),
            "chunk_index": meta.get("chunk_index"),
            "snippet": doc.strip()
        })
    print(json.dumps(output, indent=2))
else:
    print(f"\n🔍 Top {args.top_k} results for query: '{args.query}'")
    if metadata_filter:
        print(f"(Filtered by: {metadata_filter})")
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), start=1):
        print(f"\n#{i}: {meta['file_path']} (tag={meta['tag']}, lang={meta['language']}, chunk={meta['chunk_index']})")
        print("-" * 60)
        snippet = doc[:500].strip()
        print(snippet + ("..." if len(doc) > 500 else ""))
        print("-" * 60)
