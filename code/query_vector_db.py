import os
import argparse
from chromadb import PersistentClient
from dotenv import load_dotenv
import openai

# --- Load .env credentials ---
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env file.")

# --- Embedding function ---
def get_embedding(text: str, model="text-embedding-3-small"):
    response = openai.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

# --- CLI args ---
parser = argparse.ArgumentParser(description="Query a Chroma vector DB collection.")
parser.add_argument("--db", type=str, default="code_docs", help="Collection name to query (default: code_docs)")
parser.add_argument("--query", type=str, required=True, help="Search query text")
parser.add_argument("--top_k", type=int, default=3, help="Number of results to return (default: 3)")
parser.add_argument("--tag", type=str, choices=["source", "test", "doc"], help="Optional filter by document type")

args = parser.parse_args()

# --- Load Chroma collection ---
client = PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name=args.db)

# --- Optional metadata filter ---
metadata_filter = {}
if args.tag:
    metadata_filter["tag"] = args.tag

# --- Embed the query ---
query_embedding = get_embedding(args.query)

# --- Perform query ---
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=args.top_k,
    where=metadata_filter
)

# --- Display results ---
matches = zip(results["documents"][0], results["metadatas"][0])

print(f"\n🔍 Top {args.top_k} results for query: '{args.query}'")
if args.tag:
    print(f"(Filtered by tag: {args.tag})")

for i, (doc, meta) in enumerate(matches, start=1):
    print(f"\n#{i}: {meta['file_path']} ({meta['tag']})")
    print("-" * 60)
    snippet = doc[:500].strip()
    print(snippet + ("..." if len(doc) > 500 else ""))
    print("-" * 60)