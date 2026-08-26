import sqlite3
import time
from openai import OpenAI
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
SQLITE_DB = ROOT_DIR / "data" / "chatvault.db"

print("--- CHATVAULT EXTRACTION ENGINE ---")

def init_insights_table(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_type TEXT,
            title TEXT,
            description TEXT,
            source_file TEXT
        )
    ''')

def run_extraction():
    lm_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    init_insights_table(cursor)
    
    # Check what has already been processed to allow resuming
    cursor.execute("SELECT DISTINCT source_file FROM insights")
    processed_files = {row[0] for row in cursor.fetchall()}
    
    cursor.execute("SELECT file_name, raw_text FROM conversations")
    all_chats = cursor.fetchall()
    
    pending_chats = [chat for chat in all_chats if chat[0] not in processed_files]
    
    if not pending_chats:
        print("[+] All chats have already been processed. Dashboard is up to date!")
        return

    print(f"[*] Found {len(pending_chats)} chats pending extraction. This may take a while depending on your hardware.")
    print("[*] Starting local LLM processing...\n")

    system_prompt = (
        "You are an AI data extractor. Read the following conversation and identify any Projects, Ideas, or Architecture Decisions.\n"
        "Format your output EXACTLY like this (one per line). Do not use bolding or markdown. Use a pipe '|' to separate title and description.\n"
        "PROJECT: Project Name | Brief description\n"
        "IDEA: Idea Name | Brief description\n"
        "DECISION: Decision Name | Brief description\n"
        "If you find none, output NONE."
    )

    for idx, (file_name, raw_text) in enumerate(pending_chats, 1):
        print(f"[{idx}/{len(pending_chats)}] Analyzing: {file_name}...")
        
        # We only send the first 4000 characters to save time and context window limits
        chat_snippet = raw_text[:4000] 
        
        try:
            response = lm_client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Conversation:\n{chat_snippet}"}
                ],
                temperature=0.1
            )
            
            output = response.choices[0].message.content
            
            # Parse the LLM's formatted response
            lines = output.split('\n')
            inserts = 0
            for line in lines:
                line = line.strip()
                if not line or line == "NONE": continue
                
                if line.startswith("PROJECT:") or line.startswith("IDEA:") or line.startswith("DECISION:"):
                    parts = line.split(":", 1)
                    insight_type = parts[0].strip()
                    content = parts[1].split("|", 1)
                    
                    title = content[0].strip()
                    description = content[1].strip() if len(content) > 1 else ""
                    
                    # Clean up random markdown artifacts the LLM might have hallucinated
                    title = title.replace('*', '').replace('#', '')
                    
                    cursor.execute(
                        "INSERT INTO insights (insight_type, title, description, source_file) VALUES (?, ?, ?, ?)",
                        (insight_type, title, description, file_name)
                    )
                    inserts += 1
            
            conn.commit()
            print(f"    -> Extracted {inserts} insights.")
            
        except Exception as e:
            print(f"    [!] Error processing {file_name}: {e}")

    conn.close()
    print("\n[+] Extraction complete! You can now open the dashboard.")

if __name__ == "__main__":
    run_extraction()
