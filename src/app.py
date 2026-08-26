import os
import sqlite3
import chromadb
import streamlit as st
from openai import OpenAI
from pathlib import Path
import datetime
import random
import requests
import time
import shutil

# ---------------------------------------------------------
# Configuration & Relative Path Resolution
# ---------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
EXPORTS_DIR = ROOT_DIR / "exports"

DATA_DIR.mkdir(exist_ok=True, parents=True)
EXPORTS_DIR.mkdir(exist_ok=True, parents=True)

SQLITE_DB = DATA_DIR / "chatvault.db"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

st.set_page_config(
    page_title="ChatVault — Your AI conversations. Finally organised.",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed" if "wizard_complete" not in st.session_state else "expanded"
)

# ---------------------------------------------------------
# Custom CSS for Premium UI
# ---------------------------------------------------------
st.markdown("""
<style>
    .top-bar { display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px; border-bottom: 1px solid rgba(128, 128, 128, 0.2); margin-bottom: 30px; }
    .top-brand { font-size: 20px; font-weight: 700; color: var(--text-color); }
    .top-brand span { font-weight: 400; font-size: 14px; opacity: 0.7; margin-left: 10px; }
    .top-status { font-size: 13px; font-weight: 500; opacity: 0.85; }
    .metric-container { display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 40px; }
    .metric-card { flex: 1; min-width: 140px; background-color: rgba(128, 128, 128, 0.05); border-radius: 12px; padding: 20px; border-top: 4px solid; }
    .m-blue { border-top-color: #3b82f6; } .m-purple { border-top-color: #8b5cf6; } .m-yellow { border-top-color: #f59e0b; } .m-green { border-top-color: #10b981; } .m-cyan { border-top-color: #06b6d4; }
    .metric-icon { font-size: 22px; margin-bottom: 10px; }
    .metric-value { font-size: 32px; font-weight: 700; line-height: 1; margin-bottom: 4px; }
    .metric-label { font-size: 14px; font-weight: 600; opacity: 0.9; }
    .metric-sub { font-size: 12px; opacity: 0.6; margin-top: 5px; }
    [data-testid="stForm"] { background: linear-gradient(145deg, rgba(139, 92, 246, 0.05), rgba(59, 130, 246, 0.05)); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 16px; padding: 30px; box-shadow: 0 4px 30px rgba(0,0,0,0.03); margin-bottom: 40px; }
    .block-container { padding-top: 2rem; }
    .wizard-container { max-width: 600px; margin: 0 auto; text-align: center; padding-top: 5vh; }
    .wizard-step { font-size: 12px; font-weight: 700; letter-spacing: 1.5px; color: #888; text-transform: uppercase; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Backend Utilities
# ---------------------------------------------------------
@st.cache_resource
def get_clients():
    lm_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = chroma_client.get_or_create_collection(name="gemini_vault")
    return lm_client, collection, chroma_client

try:
    lm_client, collection, chroma_client = get_clients()
    lm_status = True
except Exception:
    lm_status = False

def check_lm_studio():
    try:
        r = requests.get("http://localhost:1234/v1/models", timeout=2)
        if r.status_code == 200:
            models = r.json().get('data', [])
            return True, (models[0]['id'] if models else "Local Model")
    except:
        pass
    return False, ""

def run_query(query, params=()):
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()
        cursor.execute(query, params)
        data = cursor.fetchall()
        conn.close()
        return data
    except sqlite3.OperationalError:
        return []

# Initialize DB tables if missing
def init_db():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT UNIQUE, raw_text TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS insights (id INTEGER PRIMARY KEY AUTOINCREMENT, insight_type TEXT, title TEXT, description TEXT, source_file TEXT)''')
    conn.commit()
    conn.close()

init_db()
total_chats_res = run_query("SELECT COUNT(*) FROM conversations")
total_chats = total_chats_res[0][0] if total_chats_res else 0

def clear_database():
    try:
        if SQLITE_DB.exists(): SQLITE_DB.unlink()
        if CHROMA_DB_DIR.exists(): shutil.rmtree(CHROMA_DB_DIR)
        st.session_state.clear()
    except Exception as e:
        st.error(f"Error clearing data: {e}")

# ---------------------------------------------------------
# SETUP WIZARD (Runs if 0 chats exist)
# ---------------------------------------------------------
if total_chats == 0 and not st.session_state.get("wizard_complete", False):
    st.markdown("<div class='wizard-container'>", unsafe_allow_html=True)
    
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 0
        
    step = st.session_state.wizard_step
    
    if step == 0:
        st.markdown("<h1>✦</h1>", unsafe_allow_html=True)
        st.markdown("<h2>Welcome to ChatVault</h2>", unsafe_allow_html=True)
        st.markdown("### Your AI conversations deserve a better home.")
        st.markdown("<p style='color: #888; font-size: 16px; margin: 20px 0;'>ChatVault helps you organise, explore and rediscover your AI conversation history.</p>", unsafe_allow_html=True)
        st.markdown("🔒 **Private and local**<br>🤖 **Your AI stays on your computer**", unsafe_allow_html=True)
        st.write("")
        if st.button("Get Started →", type="primary", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()

    elif step == 1:
        st.markdown("<div class='wizard-step'>Step 1 of 4</div>", unsafe_allow_html=True)
        st.markdown("<h2>📁 Where are your conversations?</h2>", unsafe_allow_html=True)
        st.markdown("Provide the path to the folder containing your exported Markdown `.md` files.")
        
        folder_path = st.text_input("Folder Path", value=str(EXPORTS_DIR))
        
        md_files = []
        if os.path.exists(folder_path):
            md_files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
            if md_files:
                st.success(f"✓ **{len(md_files)} conversations found**")
                st.markdown("Example conversations:")
                for f in md_files[:4]: st.caption(f"📄 {f}")
            else:
                st.warning("We couldn't find any Markdown conversations in this folder.")
        else:
            st.error("Folder does not exist.")
            
        st.write("")
        col1, col2 = st.columns(2)
        if col1.button("← Back", use_container_width=True):
            st.session_state.wizard_step = 0
            st.rerun()
        if col2.button("Continue →", type="primary", disabled=len(md_files)==0, use_container_width=True):
            st.session_state.import_folder = folder_path
            st.session_state.md_files = md_files
            st.session_state.wizard_step = 2
            st.rerun()

    elif step == 2:
        st.markdown("<div class='wizard-step'>Step 2 of 4</div>", unsafe_allow_html=True)
        st.markdown("<h2>🤖 Connect your local AI</h2>", unsafe_allow_html=True)
        st.markdown("ChatVault uses your local AI to understand and organise your conversations.")
        st.write("")
        
        with st.spinner("Checking for local AI..."):
            time.sleep(1)
            is_connected, model_name = check_lm_studio()
            
        if is_connected:
            st.success("🟢 **LM Studio connected**")
            st.info(f"**Model:** {model_name}\n\nEverything runs locally on your computer.")
            st.write("")
            col1, col2 = st.columns(2)
            if col1.button("← Back", use_container_width=True): st.session_state.wizard_step = 1; st.rerun()
            if col2.button("Continue →", type="primary", use_container_width=True): st.session_state.wizard_step = 3; st.rerun()
        else:
            st.error("⚪ **Local AI not detected**")
            st.markdown("Start LM Studio, load a model, and enable the Local Server on port `1234`.")
            col1, col2 = st.columns(2)
            if col1.button("← Back", use_container_width=True): st.session_state.wizard_step = 1; st.rerun()
            if col2.button("Try Again", type="primary", use_container_width=True): st.rerun()

    elif step == 3:
        st.markdown("<div class='wizard-step'>Step 3 of 4</div>", unsafe_allow_html=True)
        st.markdown("<h2>✨ Let's organise your history</h2>", unsafe_allow_html=True)
        st.markdown("ChatVault will import your files, create a searchable memory index, and keep everything on your computer.")
        st.write("")
        st.info(f"**{len(st.session_state.md_files)} conversations ready to import.**")
        
        btn_container = st.empty()
        if btn_container.button("Start Import", type="primary", use_container_width=True):
            btn_container.info("☕ Importing your conversations. Sit back and relax...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            conn = sqlite3.connect(SQLITE_DB)
            cursor = conn.cursor()
            
            files = st.session_state.md_files
            total = len(files)
            all_docs, all_metas, all_ids = [], [], []
            
            for idx, file_name in enumerate(files):
                status_text.markdown(f"📚 Reading your conversations... (`{file_name}`)")
                file_path = Path(st.session_state.import_folder) / file_name
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    cursor.execute("INSERT INTO conversations (file_name, raw_text) VALUES (?, ?)", (file_name, content))
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass
                
                chunks = content.split("---")
                for c_idx, chunk in enumerate(chunks):
                    clean_chunk = chunk.strip()
                    if len(clean_chunk) > 50:
                        all_docs.append(clean_chunk[:1500])
                        all_metas.append({"source": file_name})
                        all_ids.append(f"{file_name}_c_{c_idx}")
                        
                progress_bar.progress(int((idx / total) * 50))
            
            status_text.markdown("🔎 Building search memory... (This may take a moment)")
            if all_docs:
                BATCH_SIZE = 250
                for i in range(0, len(all_docs), BATCH_SIZE):
                    end_idx = min(i + BATCH_SIZE, len(all_docs))
                    collection.add(
                        documents=all_docs[i:end_idx], metadatas=all_metas[i:end_idx], ids=all_ids[i:end_idx]
                    )
                    progress_bar.progress(50 + int((end_idx / len(all_docs)) * 50))
            
            conn.close()
            status_text.markdown("✨ Almost ready...")
            time.sleep(1)
            st.session_state.wizard_step = 4
            st.rerun()

    elif step == 4:
        st.markdown("<h1>🎉</h1>", unsafe_allow_html=True)
        st.markdown("<h2>Your AI history is ready.</h2>", unsafe_allow_html=True)
        st.markdown(f"**{len(st.session_state.md_files)} conversations imported and indexed!**")
        st.markdown("<p style='color:#888; font-size:14px;'><i>Note: Deep project & idea extraction runs in the background. Run <code>python src/extract.py</code> in your terminal anytime to discover insights.</i></p>", unsafe_allow_html=True)
        st.write("")
        if st.button("Explore ChatVault →", type="primary", use_container_width=True):
            st.session_state.wizard_complete = True
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop() 

# ---------------------------------------------------------
# NORMAL DASHBOARD
# ---------------------------------------------------------
st.sidebar.markdown("### ✦ ChatVault")
st.sidebar.caption("Your AI conversations. Finally organised.")
st.sidebar.markdown("---")

def switch_page(page_name): st.session_state.nav_selection = page_name
def get_query_strategy(query_text):
    if any(k in query_text.lower() for k in ["evolve", "history", "change", "past", "decide", "compare"]):
        return {"n_results": 6, "messages": ["📅 Looking through your history..."], "prompt": "You are ChatVault... format as Answer, Key Points, Evolution.", "type_label": "Evolution Analysis"}
    return {"n_results": 3, "messages": ["🔎 Finding relevant conversations..."], "prompt": "Answer directly and concisely. Do not generate evolution analysis.", "type_label": "Direct Retrieval"}

if "nav_selection" not in st.session_state: st.session_state.nav_selection = "🏠 Overview"
page = st.sidebar.radio("Navigation", ["🏠 Overview", "💬 Conversations", "📁 Projects", "💡 Idea Garden", "🏗 Decisions", "🧠 Ask My History", "⚙ Settings"], key="nav_selection", label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.info("🔒 Your conversations stay on your computer.\n\n🤖 Your AI runs locally.")

insights_counts = run_query("SELECT insight_type, COUNT(*) FROM insights GROUP BY insight_type")
insight_dict = {row[0]: row[1] for row in insights_counts} if insights_counts else {}

if page == "🏠 Overview":
    st.markdown(f"<div class='top-bar'><div class='top-brand'>✦ ChatVault <span>Your AI conversations. Finally organised.</span></div><div class='top-status'>🔒 Private & Local &nbsp;•&nbsp; {'🟢 Connected' if lm_status else '🔴 Offline'}</div></div>", unsafe_allow_html=True)
    hour = datetime.datetime.now().hour
    st.markdown(f"## {'Good morning' if hour < 12 else 'Good afternoon' if hour < 18 else 'Good evening'} 👋")
    st.markdown("Here's what's happening across your AI history.")
    
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card m-blue"><div class="metric-icon">💬</div><div class="metric-value">{total_chats}</div><div class="metric-label">Conversations</div></div>
        <div class="metric-card m-purple"><div class="metric-icon">📁</div><div class="metric-value">{insight_dict.get('PROJECT', 0)}</div><div class="metric-label">Projects</div></div>
        <div class="metric-card m-yellow"><div class="metric-icon">💡</div><div class="metric-value">{insight_dict.get('IDEA', 0)}</div><div class="metric-label">Ideas</div></div>
        <div class="metric-card m-green"><div class="metric-icon">🏗</div><div class="metric-value">{insight_dict.get('DECISION', 0)}</div><div class="metric-label">Decisions</div></div>
    </div>
    """, unsafe_allow_html=True)

    if "home_answer" not in st.session_state: st.session_state.home_answer, st.session_state.home_sources, st.session_state.home_meta = "", [], ""

    with st.form(key='home_ask_form'):
        st.markdown("### ✦ Ask your AI history")
        st.markdown("Search through everything you've discussed, built, decided and explored.")
        user_home_query = st.text_input("Query", placeholder="What projects have I worked on?", label_visibility="collapsed")
        st.markdown("<span style='font-size:13px; opacity:0.7;'><b>Try asking:</b> <i>What projects have I worked on?</i> • <i>Show me ideas I never built.</i></span>", unsafe_allow_html=True)
        st.write("")
        submit_button = st.form_submit_button("Ask Local AI →", type="primary")
    
    if submit_button and user_home_query:
        strategy = get_query_strategy(user_home_query)
        with st.spinner(random.choice(strategy["messages"])):
            results = collection.query(query_texts=[user_home_query], n_results=strategy["n_results"])
            context_blocks, sources = [], set()
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    src = results['metadatas'][0][i]['source']
                    sources.add(src)
                    context_blocks.append(f"Source file: {src}\n{doc}\n")
            if context_blocks:
                try:
                    response = lm_client.chat.completions.create(model="local-model", messages=[{"role": "system", "content": strategy["prompt"]}, {"role": "user", "content": f"Historical context:\n{chr(10).join(context_blocks)}\n\nUser Query: {user_home_query}"}], temperature=0.1)
                    st.session_state.home_answer, st.session_state.home_sources, st.session_state.home_meta = response.choices[0].message.content, list(sources), f"🤖 {strategy['type_label']} · {len(sources)} sources"
                except Exception as e: st.error(f"Error: {e}")

    if st.session_state.home_answer:
        st.markdown("### 🤖 AI Answer")
        st.markdown(st.session_state.home_answer)
        if st.session_state.home_sources:
            for s in st.session_state.home_sources:
                with st.expander(f"View source: {s}"): st.text_area("Snippet", run_query("SELECT raw_text FROM conversations WHERE file_name = ?", (s,))[0][0][:1200], height=150, key=f"home_{s}")

    st.markdown("---")
    st.markdown("### Continue exploring")
    bc1, bc2, bc3 = st.columns(3)
    bc1.button("📁 View my projects", use_container_width=True, on_click=switch_page, args=("📁 Projects",))
    bc2.button("💡 Rediscover old ideas", use_container_width=True, on_click=switch_page, args=("💡 Idea Garden",))
    bc3.button("🏗 Review key decisions", use_container_width=True, on_click=switch_page, args=("🏗 Decisions",))

elif page == "⚙ Settings":
    st.markdown("# ⚙ Settings")
    st.markdown("### 🗄️ Data")
    st.text_input("Conversation Folder", value=str(EXPORTS_DIR), disabled=True)
    if st.button("Re-run Setup Wizard"): st.session_state.clear(); st.rerun()
    st.write("")
    with st.expander("⚠️ Danger Zone"):
        st.warning("Clearing data removes your SQLite and ChromaDB files. It DOES NOT delete your original Markdown exports.")
        if st.button("Clear local ChatVault data", type="primary"):
            clear_database(); st.rerun()
            
    st.markdown("### 🤖 Local AI")
    st.info(f"**Status:** {'🟢 Connected' if lm_status else '🔴 Offline'}\n\n**Model:** {check_lm_studio()[1] if lm_status else 'None'}")
    
    st.markdown("### 🔒 About Privacy")
    st.markdown("Your conversations stay on your computer. ChatVault does not upload your conversations to a cloud service. Your local AI processes your data completely locally.")

elif page == "💬 Conversations":
    st.markdown("# 💬 Conversations")
    for file_name, raw_text in run_query("SELECT file_name, raw_text FROM conversations LIMIT 30"):
        with st.expander(f"📄 {file_name}"): st.text_area("Content", raw_text, height=300, key=file_name)

elif page == "📁 Projects":
    st.markdown("# 📁 Your Projects")
    for title, desc, source in run_query("SELECT title, description, source_file FROM insights WHERE insight_type='PROJECT'"):
        with st.expander(f"🟣 {title}"): st.markdown(desc); st.caption(f"Source: {source}")

elif page == "💡 Idea Garden":
    st.markdown("# 💡 Idea Garden")
    for title, desc, source in run_query("SELECT title, description, source_file FROM insights WHERE insight_type='IDEA'"):
        st.success(f"**{title}**: {desc}\n\n*(Source: {source})*")

elif page == "🏗 Decisions":
    st.markdown("# 🏗 Architecture Decisions")
    for title, desc, source in run_query("SELECT title, description, source_file FROM insights WHERE insight_type='DECISION'"):
        st.info(f"**{title}**: {desc}\n\n*(Source: {source})*")

elif page == "🧠 Ask My History":
    st.markdown("# 🧠 Ask My History")
    if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Hello! I am connected to your local history. What would you like to revisit or explore?"}]
    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"])
    if prompt := st.chat_input("What would you like to know?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            strategy = get_query_strategy(prompt)
            with st.spinner(random.choice(strategy["messages"])):
                results = collection.query(query_texts=[prompt], n_results=strategy["n_results"])
                context_blocks = [f"Source file: {src}\n{doc}\n" for i, doc in enumerate(results['documents'][0]) for src in [results['metadatas'][0][i]['source']]] if results['documents'] else []
                if not context_blocks: st.warning("No relevant information found.")
                else:
                    stream = lm_client.chat.completions.create(model="local-model", messages=[{"role": "system", "content": strategy["prompt"]}, {"role": "user", "content": f"Historical context:\n{chr(10).join(context_blocks)}\n\nUser Query: {prompt}"}], temperature=0.1, stream=True)
                    response_container, full_response = st.empty(), ""
                    for chunk in stream:
                        full_response += (chunk.choices[0].delta.content or "")
                        response_container.markdown(full_response + "▌")
                    response_container.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
