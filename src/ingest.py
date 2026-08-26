import os
import sqlite3
import chromadb
from pathlib import Path

# Resolve relative paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
EXPORTS_DIR = ROOT_DIR / "exports"

SQLITE_DB = DATA_DIR / "chatvault.db"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

def init_db():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT UNIQUE,
            raw_text TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

def run_ingestion():
    if not EXPORTS_DIR.exists():
        print(f"[-] Directory not found: {EXPORTS_DIR}")
        return

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = chroma_client.get_or_create_collection(name="gemini_vault")
    
    conn, cursor = init_db()

    all_docs = []
    all_metas = []
    all_ids = []

    print("[*] Scanning 'exports' directory for Markdown files...")
    files = [f for f in os.listdir(EXPORTS_DIR) if f.endswith(".md")]
    
    if not files:
        print("[-] No Markdown files found in the 'exports' folder.")
        return

    for file_name in files:
        file_path = EXPORTS_DIR / file_name
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Insert into SQLite
        try:
            cursor.execute("INSERT INTO conversations (file_name, raw_text) VALUES (?, ?)", (file_name, content))
            conn.commit()
            print(f"[+] Loaded into SQLite: {file_name}")
        except sqlite3.IntegrityError:
            print(f"[~] Skipping (already exists): {file_name}")
            continue
            
        # 2. Chunk for Vector DB
        chunks = content.split("---")
        for idx, chunk in enumerate(chunks):
            clean_chunk = chunk.strip()
            if len(clean_chunk) > 50:
                all_docs.append(clean_chunk[:1500])
                all_metas.append({"source": file_name})
                all_ids.append(f"{file_name}_chunk_{idx}")

    # 3. Batch Embed into Chroma
    if all_docs:
        print(f"\n[*] Batch embedding {len(all_docs)} total chunks into ChromaDB...")
        BATCH_SIZE = 250
        for i in range(0, len(all_docs), BATCH_SIZE):
            end_idx = min(i + BATCH_SIZE, len(all_docs))
            collection.add(
                documents=all_docs[i:end_idx],
                metadatas=all_metas[i:end_idx],
                ids=all_ids[i:end_idx]
            )
            print(f"    -> Embedded {end_idx}/{len(all_docs)} chunks...")
    
    print("\n[+] Ingestion complete. Your dashboard is ready.")

if __name__ == "__main__":
    run_ingestion()
