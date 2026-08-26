import time
import chromadb
from openai import OpenAI
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
CHROMA_DB_DIR = ROOT_DIR / "data" / "chroma_db"

print("--- CHATVAULT PROFILER ---")
print("Initializing clients...")
lm_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
collection = chroma_client.get_or_create_collection(name="gemini_vault")

query = "What is FROC OS?"
print(f"\nTest Query: '{query}'")

# Profile Retrieval
t0 = time.time()
results = collection.query(query_texts=[query], n_results=6)
retrieval_time = time.time() - t0

chunks = results['documents'][0] if results['documents'] else []
context = "\n".join(chunks)
char_count = len(context)
estimated_tokens = char_count // 4

print(f"Retrieval & Embedding: {retrieval_time:.2f} sec")
print(f"Chunks retrieved:      {len(chunks)}")
print(f"Context size:          {char_count} chars (~{estimated_tokens} tokens)")

system_prompt = (
    "You are ChatVault, an intelligent personal knowledge assistant. "
    "Analyze the provided historical chat context. Distinguish clearly between current understanding (🟢), "
    "proposed/experimental (🟡), historical (⚪), and abandoned/superseded (🔴) concepts. "
    "Explicitly explain how the thinking evolved across conversations, preferring recent conclusions while maintaining historical context. "
    "Format your response into: Answer, Key points (3-6 points), and Evolution / history."
)

print("\nSending to LM Studio...")
t_request = time.time()
stream = lm_client.chat.completions.create(
    model="local-model",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Historical context:\n{context}\n\nUser Query: {query}"}
    ],
    temperature=0.1,
    stream=True
)

ttft = 0
generation_start = 0
token_count = 0

for chunk in stream:
    if ttft == 0:
        ttft = time.time() - t_request
        generation_start = time.time()
    
    delta = chunk.choices[0].delta.content or ""
    if delta:
        token_count += 1
        print(delta, end="", flush=True)

generation_time = time.time() - generation_start
total_time = time.time() - t_request

print("\n\n--- RESULTS ---")
print(f"Time to First Token: {ttft:.2f} sec")
print(f"Gemma Generation:    {generation_time:.2f} sec")
print(f"Total LLM Time:      {total_time:.2f} sec")
print(f"Generation Speed:    {token_count / generation_time:.2f} tokens/sec")
