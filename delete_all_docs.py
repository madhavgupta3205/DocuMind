#!/usr/bin/env python3
"""
Script to delete all documents and chunks from ChromaDB.
WARNING: This will clear the entire vector database!
"""

from app.services.vector_db import ChromaDB
from loguru import logger


def main():
    print("\n" + "="*60)
    print("⚠️  WARNING: DELETE ALL DOCUMENTS")
    print("="*60)
    print("This will permanently delete ALL documents and chunks")
    print("from the ChromaDB vector database.")
    print("="*60 + "\n")

    # Get current count
    current_count = ChromaDB.get_collection_count()
    print(f"Current embeddings in database: {current_count}")

    if current_count == 0:
        print("\n✓ Database is already empty!")
        return

    confirm = input(
        f"\nType 'DELETE ALL' to confirm deletion of {current_count} chunks: ")

    if confirm.strip() == "DELETE ALL":
        print("\n🗑️  Deleting all documents...")
        deleted_count = ChromaDB.delete_all_documents()

        # Verify deletion
        remaining = ChromaDB.get_collection_count()

        print(f"\n✓ Successfully deleted {deleted_count} chunks")
        print(f"✓ Remaining embeddings: {remaining}")

        if remaining == 0:
            print("\n✅ Database is now completely empty!")
        else:
            print(f"\n⚠️  Warning: {remaining} embeddings still remain")
    else:
        print("\n❌ Deletion cancelled - you must type 'DELETE ALL' exactly")


if __name__ == "__main__":
    main()
