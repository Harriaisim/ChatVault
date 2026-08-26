# ✦ ChatVault

**Your AI conversations. Finally organised.**

<img width="1850" height="777" alt="image" src="https://github.com/user-attachments/assets/ca4ff801-bf22-49d0-95ff-538c49ba5d83" />


## What is ChatVault?

ChatVault helps you take exported AI conversations and turn them into a private, searchable personal knowledge vault.

Instead of letting your brilliant brainstorming sessions, technical architectures, and creative ideas gather dust in a zip file, ChatVault brings them back to life.

You can:
* **Browse** old conversations in a clean UI.
* **Search** semantically through your entire history.
* **Ask** your local AI questions about previous conversations.
* **Discover** implicit Projects, Ideas, and Decisions.
* **Explore** how your thinking and architectures evolved over time.
* **Verify** by seeing the original conversations used as sources.

## 🔒 Privacy & Local-First
* **Zero Egress:** Your data never leaves your machine. No cloud AI API required.
* **Local Inference:** Powered entirely by local models running via LM Studio.
* **Private Storage:** Uses local SQLite for conversation history and ChromaDB for vector embeddings.

---

## 🚀 Quick Start

### 1. Clone or download ChatVault
`ash
git clone [https://github.com/Harriaisim/chatvault.git](https://github.com/Harriaisim/chatvault.git)
cd chatvault
`

### 2. Install dependencies
`ash
pip install -r requirements.txt
`

### 3. Start Local AI
1. Open **LM Studio**.
2. Load a supported local model (e.g., Gemma).
3. Start the **Local Server** on port 1234.

### 4. Launch ChatVault
For Windows users, double-click the included batch launcher:
`ash
start.bat
`
Alternatively, run it manually:
`ash
python -m streamlit run src/app.py
`

### 5. Follow the Setup Wizard
On first launch, ChatVault guides you through importing your files.

---

## 📥 Preparing Your Conversations

**Current requirement:** ChatVault currently works exclusively with **Markdown (.md)** conversation files.

Your original exports are never modified. ChatVault copies and processes conversation content into its own local database and search index.

### Google Gemini
1. Export your Gemini activity via Google Takeout.
2. Download and extract the ZIP archive.
3. Convert the exported data into .md files (*direct ZIP import is planned*).
4. Select the folder during the Setup Wizard.

### ChatGPT
1. Request export via Settings -> Data Controls -> Export Data.
2. Download and extract the ZIP.
3. Convert conversations.json into .md files (*direct JSON import is planned*).
4. Select the folder during the Setup Wizard.

### Other AI Platforms
Any AI conversations exported or converted into Markdown format can be indexed by ChatVault.

---

## ✨ First Run Experience

1. **Select folder:** Point ChatVault to your .md folder.
2. **Connect local AI:** Verifies LM Studio on port 1234.
3. **Import & index:** Builds SQLite store and ChromaDB vector index.
4. **Start exploring:** Immediate access to semantic search.

---

## 🏛️ Architecture
* **UI:** Streamlit dashboard with Setup Wizard and timeline inspection.
* **Retrieval:** Dual-path RAG engine for direct answers and evolution queries.
* **Extraction:** Local LLM asynchronous metadata extractor.

---

## 🛠️ Troubleshooting
* **LM Studio not detected:** Verify the Local Server is running on port 1234 with a model loaded.
* **No conversations found:** Verify .md files exist in the selected folder.
* **Empty Projects/Decisions:** Run python src/extract.py in the terminal to trigger deep insight parsing.

---

## ⚠️ Current Limitations
* Tested primarily on Windows.
* Requires LM Studio running locally.
* Input files must be .md format.

---

## 🗺️ Roadmap
- [x] Local Markdown ingestion & SQLite store
- [x] ChromaDB vector indexing & local RAG
- [x] Dual-path historical analysis
- [x] First-run Setup Wizard & start.bat
- [ ] Direct Google Takeout ZIP parser
- [ ] Direct ChatGPT JSON parser

---

## 📝 License
MIT License - see LICENSE file for details.
