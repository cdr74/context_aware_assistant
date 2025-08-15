import os
import argparse
import time
import json
from typing import Dict, List
from chromadb import PersistentClient
from dotenv import load_dotenv
import openai

# -------------------------
# Load API keys & config
# -------------------------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

if not openai.api_key:
    raise RuntimeError("❌ OPENAI_API_KEY not found in .env file.")

# -------------------------
# Embedding helper
# -------------------------
def get_embedding(text: str, model="text-embedding-3-small", retries=3) -> List[float]:
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

# -------------------------
# Ask the LLM for a synthesized answer
# -------------------------
def get_llm_answer(query: str, documents: list) -> str:
    """
    Given a query and a list of documents, ask the LLM to synthesize an answer.
    """
    prompt = (
        "You are an assistant that answers questions based on provided code snippets and documentation.\n"
        "Use only the provided context, do not hallucinate.\n\n"
        f"Question: {query}\n\n"
        "Relevant context:\n"
    )

    for i, doc in enumerate(documents, start=1):
        prompt += f"\n--- Snippet {i} ---\n{doc}\n"

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You answer strictly based on the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        return ""

# -------------------------
# CLI arguments
# -------------------------
parser = argparse.ArgumentParser(description="Query a Chroma vector DB and get an LLM answer.")
parser.add_argument("--db", type=str, default="code_docs", help="Collection name to query (default: code_docs)")
parser.add_argument("--query", type=str, required=True, help="Search query text")
parser.add_argument("--top_k", type=int, default=3, help="Number of results to retrieve for context")
parser.add_argument("--tag", type=str, choices=["source", "test", "doc"], help="Optional filter by document type")
parser.add_argument("--language", type=str, help="Optional filter by language (python/java/markdown)")
parser.add_argument("--json", action="store_true", help="Return raw results in JSON format instead of answer")

args = parser.parse_args()

# -------------------------
# Load Chroma collection
# -------------------------
client = PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name=args.db)

# -------------------------
# Build metadata filter
# -------------------------
metadata_filter: Dict[str, str] = {}
if args.tag:
    metadata_filter["tag"] = args.tag
if args.language:
    metadata_filter["language"] = args.language

# -------------------------
# Embed query & retrieve
# -------------------------
query_embedding = get_embedding(args.query)

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=args.top_k,
    where=metadata_filter if metadata_filter else None
)

if not results["documents"] or not results["documents"][0]:
    print(f"❌ No results found for query: '{args.query}'")
    exit(0)

documents = results["documents"][0]
metadatas = results["metadatas"][0]

# -------------------------
# Output
# -------------------------
if args.json:
    output = []
    for doc, meta in zip(documents, metadatas):
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
    print(f"\n🔍 Top {args.top_k} relevant results for: '{args.query}'")
    if metadata_filter:
        print(f"(Filtered by: {metadata_filter})")

    for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
        print(f"\n#{i}: {meta['file_path']} (tag={meta['tag']}, lang={meta['language']}, chunk={meta['chunk_index']})")
        print("-" * 60)
        snippet = doc[:500].strip()
        print(snippet + ("..." if len(doc) > 500 else ""))
        print("-" * 60)

    print("\n💡 Synthesized Answer:")
    answer = get_llm_answer(args.query, documents)
    print(answer)