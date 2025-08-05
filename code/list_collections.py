from chromadb import PersistentClient

chroma_client = PersistentClient(path="./chroma_db")

collections = chroma_client.list_collections()
if not collections:
    print("❌ No collections found in Chroma DB.")
else:
    print("📦 Collections in Chroma DB:")
    for col in collections:
        print(f"  - {col.name}")
