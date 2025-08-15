#!/usr/bin/env python3
from chromadb import PersistentClient
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        description="Drop one or more Chroma DB collections."
    )
    parser.add_argument(
        "--path",
        default="./chroma_db",
        help="Path to the Chroma DB directory (default: ./chroma_db)"
    )
    parser.add_argument(
        "--drop",
        help="Name of the collection to drop. Use 'ALL' to drop all collections."
    )
    args = parser.parse_args()

    chroma_client = PersistentClient(path=args.path)

    collections = chroma_client.list_collections()
    if not collections:
        print("❌ No collections found in Chroma DB.")
        sys.exit(0)

    print("📦 Collections in Chroma DB:")
    for col in collections:
        print(f"  - {col.name}")

    if not args.drop:
        print("\nℹ️  No --drop argument provided. Nothing will be deleted.")
        sys.exit(0)

    if args.drop == "ALL":
        confirm = input("⚠️  Are you sure you want to drop ALL collections? (y/N): ")
        if confirm.lower() != "y":
            print("❌ Aborted.")
            sys.exit(0)
        for col in collections:
            chroma_client.delete_collection(name=col.name)
            print(f"✅ Dropped collection '{col.name}'")
    else:
        match = [col for col in collections if col.name == args.drop]
        if not match:
            print(f"❌ Collection '{args.drop}' not found.")
            sys.exit(1)
        chroma_client.delete_collection(name=args.drop)
        print(f"✅ Dropped collection '{args.drop}'")

if __name__ == "__main__":
    main()