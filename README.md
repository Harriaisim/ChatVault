# ✦ ChatVault

**Your AI conversations. Finally organised.**

ChatVault is a local-first, air-gapped personal intelligence vault. It transforms static AI chat exports (like Google Gemini Takeout data) into a searchable, evolution-aware knowledge base without relying on cloud APIs.

## 🔒 Privacy First
* **Zero Egress:** Everything stays on your local machine.
* **Local Inference:** Powered entirely by local models running via LM Studio.
* **Private Storage:** Uses local SQLite for conversation history and ChromaDB for vector embeddings.

## 🚀 Installation & Setup

### 1. Prerequisites
* Python 3.10+
* [LM Studio](https://lmstudio.ai/) installed and running.
* Load a local model (e.g., Gemma) in LM Studio and start the **Local Server** on port `1234`.

### 2. Install ChatVault
Open your terminal and run:
git clone https://github.com/Harriaisim/chatvault.git
cd chatvault
pip install -r requirements.txt

### 3. Launch & Configure
Simply double-click the `start.bat` file (or run `python -m streamlit run src/app.py`).

ChatVault features a built-in **Setup Wizard** that will run on your first launch. It will automatically:
1. Guide you to select your exported Markdown (.md) conversation files.
2. Verify your LM Studio connection.
3. Import and index your conversations into the secure local database.

### 4. Background Insight Extraction (Optional)
To populate the **Projects**, **Ideas**, and **Decisions** dashboards, ChatVault needs to deeply analyze your conversations. Because this takes time, it runs as a background script. 
Open a terminal in the chatvault folder and run:
python src/extract.py

Note: You can stop and restart this script at any time; it will pick up exactly where it left off.

## 🏛️ Architecture
* **UI:** Streamlit-powered dashboard featuring dynamic metrics, interactive source tracking, and the Setup Wizard.
* **Retrieval:** Dual-path RAG engine routes simple questions for fast answers, and history queries for deep chronological analysis.
* **Extraction:** Uses local LLMs to asynchronously extract metadata into a structured SQLite database.
