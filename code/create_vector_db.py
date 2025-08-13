import os
import argparse
import hashlib
import time
import openai
from dotenv import load_dotenv
import chromadb
from chromadb import PersistentClient
from typing import List, Dict

# ---- Load OpenAI config ----
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env file.")

# ---- Setup Chroma client ----
chroma_client = PersistentClient(path="./chroma_db")


# ---- Embedding function with retries ----
def get_embedding(text: str, model="text-embedding-3-small", retries=3):
    if not text.strip():
        raise ValueError("Empty or whitespace-only text cannot be embedded.")

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


# ---- File collection ----
def collect_files(directory: str, extensions: tuple) -> List[str]:
    file_paths = []
    for root, _, files in os.walk(directory):
        for name in files:
            if name.endswith(extensions):
                file_paths.append(os.path.join(root, name))
    return file_paths


# ---- Chunking helper ----
def chunk_text(text: str, chunk_size: int = 200, overlap: int = 50) -> List[str]:
    """
    Splits text into chunks of roughly `chunk_size` lines with `overlap` lines overlap.
    """
    lines = text.splitlines()
    chunks = []
    start = 0
    while start < len(lines):
        end = start + chunk_size
        chunk = "\n".join(lines[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ---- Language detection based on extension ----
def detect_language(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return "python"
    elif ext == ".java":
        return "java"
    elif ext == ".md":
        return "markdown"
    else:
        return "unknown"


# ---- Process and store file chunks ----
def process_and_store(collection, file_paths: List[str], tag: str):
    existing_ids = set(collection.get()["ids"])

    for path in file_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if not content.strip():
                print(f"⚠️ Skipping empty file: {path}")
                continue

            chunks = chunk_text(content, chunk_size=200, overlap=50)
            language = detect_language(path)

            for idx, chunk in enumerate(chunks):
                doc_id = f"{tag}:{path}:{idx}"
                if doc_id in existing_ids:
                    collection.delete(ids=[doc_id])
                    print(f"🔁 Replacing existing chunk: {path} [chunk {idx}]")

                embedding = get_embedding(chunk)

                collection.add(
                    documents=[chunk],
                    embeddings=[embedding],
                    ids=[doc_id],
                    metadatas=[{
                        "file_path": path,
                        "file_name": os.path.basename(path),
                        "tag": tag,
                        "language": language,
                        "chunk_index": idx
                    }]
                )
            print(f"✅ Added {path} as {tag} ({len(chunks)} chunks)")
        except Exception as e:
            print(f"❌ Failed to process {path}: {e}")


# ---- Main entry point ----
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create/update Chroma vector DB from source/test/doc directories.")
    parser.add_argument("--src", type=str, help="Directory with source code files (.py/.java)")
    parser.add_argument("--test", type=str, help="Directory with test code files (.py/.java)")
    parser.add_argument("--doc", type=str, help="Directory with markdown docs (.md)")
    parser.add_argument("--db", type=str, default="code_docs", help="Name of the Chroma collection (default: code_docs)")

    args = parser.parse_args()

    if not any([args.src, args.test, args.doc]):
        parser.error("At least one of --src, --test, or --doc must be provided.")

    collection = chroma_client.get_or_create_collection(name=args.db)

    if args.src:
        src_files = collect_files(args.src, (".py", ".java"))
        process_and_store(collection, src_files, "source")

    if args.test:
        test_files = collect_files(args.test, (".py", ".java"))
        process_and_store(collection, test_files, "test")

    if args.doc:
        doc_files = collect_files(args.doc, (".md",))
        process_and_store(collection, doc_files, "doc")

    print("\n✅ Done. Chroma DB persisted to ./chroma_db")
