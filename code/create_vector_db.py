import os
import argparse
import openai
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from chromadb import PersistentClient


# ---- Load OpenAI config from .env ----
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")


if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env file.")


# ---- Setup Chroma client for local persistent storage ----
chroma_client = PersistentClient(path="./chroma_db")


# ---- Embedding function using OpenAI; using large cost more but has higehr accuracy ----
def get_embedding(text: str, model="text-embedding-3-small"):
    if not text.strip():
        raise ValueError("Empty or whitespace-only text cannot be embedded.")
    response = openai.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding


# ---- Helper: Collect valid files ----
def collect_files(directory, extensions):
    file_paths = []
    for root, _, files in os.walk(directory):
        for name in files:
            if name.endswith(extensions):
                file_paths.append(os.path.join(root, name))
    return file_paths


# ---- Process and embed each file ----
def process_and_store(collection, file_paths, tag):
    existing_ids = set(collection.get()["ids"])

    for path in file_paths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if not content.strip():
                print(f"⚠️ Skipping empty file: {path}")
                continue

            doc_id = f"{tag}:{path}"

            # Refresh if it already exists
            if doc_id in existing_ids:
                collection.delete(ids=[doc_id])
                print(f"🔁 Replacing existing document: {path}")

            embedding = get_embedding(content)

            collection.add(
                documents=[content],
                embeddings=[embedding],
                ids=[doc_id],
                metadatas=[{
                    "file_path": path,
                    "tag": tag
                }]
            )
            print(f"✅ Added {path} as {tag}")
        except Exception as e:
            print(f"❌ Failed to process {path}: {e}")


# ---- Main entry point ----
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a Chroma vector DB from source/test/doc directories.")
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
