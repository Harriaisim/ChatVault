import os
import sqlite3
import chromadb
import streamlit as st
from openai import OpenAI
from pathlib import Path
import datetime
import random
from collections import Counter

# ---------------------------------------------------------
# Configuration & Relative Path Resolution
# ---------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
EXPORTS_DIR = ROOT_DIR / "exports"

SQLITE_DB = DATA_DIR / "chatvault.db"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

st.set_page_config(
    page_title="ChatVault — Your AI conversations. Finally organised.",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
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
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Client Initialization & Health Checks
# ---------------------------------------------------------
@st.cache_resource
def get_clients():
    lm_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = chroma_client.get_or_create_collection(name="gemini_vault")
    return lm_client, collection

try:
    lm_client, collection = get_clients()
    lm_status = True
except Exception:
    lm_status = False

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

total_chats_res = run_query("SELECT COUNT(*) FROM conversations")
total_chats = total_chats_res[0][0] if total_chats_res else 0

# Fetch dynamic counts if table exists
insights_counts = run_query("SELECT insight_type, COUNT(*) FROM insights GROUP BY insight_type")
insight_dict = {row[0]: row[1] for row in insights_counts} if insights_counts else {}
num_projects = insight_dict.get("PROJECT", 0)
num_ideas = insight_dict.get("IDEA", 0)
num_decisions = insight_dict.get("DECISION", 0)

# ---------------------------------------------------------
# Dual-Path Routing Logic
# ---------------------------------------------------------
def get_query_strategy(query_text):
    evolution_keywords = ["evolve", "evolution", "history", "change", "past", "decisions", "decide", "previous", "think", "compare"]
    is_evolution = any(keyword in query_text.lower() for keyword in evolution_keywords)
    
    if is_evolution:
        return {
            "n_results": 6,
            "messages": ["📅 Looking through your history...", "🧠 Tracing how your thinking evolved...", "🔗 Connecting conversations across time..."],
            "prompt": "You are ChatVault, an intelligent personal knowledge assistant. Analyze the historical context. Distinguish clearly between current understanding (🟢), proposed/experimental (🟡), historical (⚪), and abandoned/superseded (🔴) concepts. Format your response into: Answer, Key points, and Evolution / history.",
            "type_label": "Evolution Analysis"
        }
    else:
        return {
            "n_results": 3,
            "messages": ["🔎 Finding relevant conversations...", "🧠 Reading the most relevant context...", "✨ Preparing your concise answer..."],
            "prompt": "You are ChatVault, an intelligent personal knowledge assistant. Answer the user's question directly and concisely using ONLY the provided historical chat context. Do not generate an evolution analysis or a long structured report. Be direct and concise.",
            "type_label": "Direct Retrieval"
        }

def switch_page(page_name):
    st.session_state.nav_selection = page_name

if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "🏠 Overview"

page = st.sidebar.radio("Navigation", ["🏠 Overview", "💬 Conversations", "📁 Projects", "💡 Idea Garden", "🏗 Decisions", "🧠 Ask My History", "⚙ Settings"], key="nav_selection", label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption("ChatVault MVP · Local-First")

# ---------------------------------------------------------
# Page 1: Overview
# ---------------------------------------------------------
if page == "🏠 Overview":
    status_icon = "🟢" if lm_status else "🔴"
    status_text = "Local AI Connected" if lm_status else "Local AI Offline"
    st.markdown(f"""
    <div class="top-bar">
        <div class="top-brand">✦ ChatVault <span>Your AI conversations. Finally organised.</span></div>
        <div class="top-status">🔒 Private & Local &nbsp;&nbsp;•&nbsp;&nbsp; {status_icon} {status_text}</div>
    </div>
    """, unsafe_allow_html=True)

    hour = datetime.datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    st.markdown(f"## {greeting} 👋")
    st.markdown("Here's what's happening across your AI history.")
    st.write("")

    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card m-blue"><div class="metric-icon">💬</div><div class="metric-value">{total_chats}</div><div class="metric-label">Conversations</div><div class="metric-sub">All analysed</div></div>
        <div class="metric-card m-purple"><div class="metric-icon">📁</div><div class="metric-value">{num_projects}</div><div class="metric-label">Projects</div><div class="metric-sub">Discovered</div></div>
        <div class="metric-card m-yellow"><div class="metric-icon">💡</div><div class="metric-value">{num_ideas}</div><div class="metric-label">Ideas</div><div class="metric-sub">In the garden</div></div>
        <div class="metric-card m-green"><div class="metric-icon">🏗</div><div class="metric-value">{num_decisions}</div><div class="metric-label">Decisions</div><div class="metric-sub">Architecture log</div></div>
    </div>
    """, unsafe_allow_html=True)

    if "home_answer" not in st.session_state: st.session_state.home_answer, st.session_state.home_sources, st.session_state.home_meta = "", [], ""

    with st.form(key='home_ask_form'):
        st.markdown("### ✦ Ask your AI history")
        st.markdown("Search through everything you've discussed, built, decided and explored.", help="Your queries are processed 100% locally.")
        st.write("")
        user_home_query = st.text_input("Query", placeholder="What is FROC OS?", label_visibility="collapsed")
        st.markdown("<span style='font-size:13px; opacity:0.7;'><b>Try asking:</b> <i>What is FROC OS?</i> • <i>How did my FROC OS ideas evolve?</i></span>", unsafe_allow_html=True)
        st.write("")
        submit_button = st.form_submit_button("Ask Local AI →", type="primary")
    
    if submit_button:
        if not lm_status: st.error("Cannot query: LM Studio server is offline.")
        elif total_chats == 0: st.warning("Your vault is empty! Place your Markdown files in the 'exports' folder and run the ingestion script.")
        elif user_home_query:
            strategy = get_query_strategy(user_home_query)
            with st.spinner(random.choice(strategy["messages"])):
                results = collection.query(query_texts=[user_home_query], n_results=strategy["n_results"])
                context_blocks, sources = [], set()
                if results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        src = results['metadatas'][0][i]['source']
                        sources.add(src)
                        context_blocks.append(f"Source file: {src}\n{doc}\n")
                if not context_blocks:
                    st.warning("No relevant information found in your past conversations.")
                else:
                    context = "\n".join(context_blocks)
                    try:
                        response = lm_client.chat.completions.create(model="local-model", messages=[{"role": "system", "content": strategy["prompt"]}, {"role": "user", "content": f"Historical context:\n{context}\n\nUser Query: {user_home_query}"}], temperature=0.1)
                        st.session_state.home_answer = response.choices[0].message.content
                        st.session_state.home_sources = list(sources)
                        st.session_state.home_meta = f"🤖 {strategy['type_label']} · {len(sources)} sources"
                    except Exception as e: st.error(f"Error communicating with local LLM: {e}")
        else: st.warning("Please enter a question first.")

    if st.session_state.home_answer:
        st.markdown("### 🤖 AI Answer")
        st.markdown(st.session_state.home_answer)
        if st.session_state.home_meta: st.caption(st.session_state.home_meta)
        if st.session_state.home_sources:
            st.markdown("#### 📄 Sources Referenced")
            for s in st.session_state.home_sources:
                with st.expander(f"View source: {s}"):
                    match = run_query("SELECT raw_text FROM conversations WHERE file_name = ?", (s,))
                    if match: st.text_area("Snippet", match[0][0][:1200] + "\n...", height=150, key=f"home_{s}")

    st.markdown("---")
    st.markdown("### Continue exploring")
    st.write("")
    bc1, bc2, bc3 = st.columns(3)
    bc1.button("📁 View my projects", use_container_width=True, on_click=switch_page, args=("📁 Projects",))
    bc2.button("💡 Rediscover old ideas", use_container_width=True, on_click=switch_page, args=("💡 Idea Garden",))
    bc3.button("🏗 Review key decisions", use_container_width=True, on_click=switch_page, args=("🏗 Decisions",))

# ---------------------------------------------------------
# Dynamic Discovery Pages
# ---------------------------------------------------------
elif page == "📁 Projects":
    st.markdown("# 📁 Your Projects")
    st.markdown("Dynamic extraction of projects discussed in your history.")
    projects = run_query("SELECT title, description, source_file FROM insights WHERE insight_type='PROJECT'")
    if not projects:
        st.info("No projects extracted yet. Please run `python src/extract.py`.")
    else:
        for title, desc, source in projects:
            with st.expander(f"🟣 {title}"):
                st.markdown(desc)
                st.caption(f"Source: {source}")

elif page == "💡 Idea Garden":
    st.markdown("# 💡 Idea Garden")
    st.markdown("Concepts and brainstorms captured from your history.")
    ideas = run_query("SELECT title, description, source_file FROM insights WHERE insight_type='IDEA'")
    if not ideas:
        st.info("No ideas extracted yet. Please run `python src/extract.py`.")
    else:
        for title, desc, source in ideas:
            st.success(f"**{title}**: {desc}\n\n*(Source: {source})*")

elif page == "🏗 Decisions":
    st.markdown("# 🏗 Architecture Decisions")
    st.markdown("Technical choices you've logged in past conversations.")
    decisions = run_query("SELECT title, description, source_file FROM insights WHERE insight_type='DECISION'")
    if not decisions:
        st.info("No decisions extracted yet. Please run `python src/extract.py`.")
    else:
        for title, desc, source in decisions:
            st.info(f"**{title}**: {desc}\n\n*(Source: {source})*")

# ---------------------------------------------------------
# Static Pages
# ---------------------------------------------------------
elif page == "💬 Conversations":
    st.markdown("# 💬 Conversations")
    chats = run_query("SELECT file_name, raw_text FROM conversations LIMIT 30")
    if not chats: st.info("No conversations found.")
    else:
        for file_name, raw_text in chats:
            with st.expander(f"📄 {file_name}"): st.text_area("Content", raw_text, height=300, key=file_name)

elif page == "🧠 Ask My History":
    st.markdown("# 🧠 Ask My History")
    if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Hello! I am connected to your local history. What would you like to revisit or explore?"}]
    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"])
    if prompt := st.chat_input("What would you like to know?"):
        if not lm_status: st.error("Cannot query: LM Studio server is offline.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                strategy = get_query_strategy(prompt)
                with st.spinner(random.choice(strategy["messages"])):
                    results = collection.query(query_texts=[prompt], n_results=strategy["n_results"])
                    context_blocks, sources = [], set()
                    if results['documents'] and results['documents'][0]:
                        for i, doc in enumerate(results['documents'][0]):
                            src = results['metadatas'][0][i]['source']
                            sources.add(src)
                            context_blocks.append(f"Source file: {src}\n{doc}\n")
                    if not context_blocks: st.warning("No relevant information found.")
                    else:
                        context = "\n".join(context_blocks)
                        try:
                            stream = lm_client.chat.completions.create(model="local-model", messages=[{"role": "system", "content": strategy["prompt"]}, {"role": "user", "content": f"Historical context:\n{context}\n\nUser Query: {prompt}"}], temperature=0.1, stream=True)
                            response_container, full_response = st.empty(), ""
                            for chunk in stream:
                                delta = chunk.choices[0].delta.content or ""
                                full_response += delta
                                response_container.markdown(full_response + "▌")
                            response_container.markdown(full_response)
                            st.caption(f"🤖 {strategy['type_label']} · {len(sources)} sources")
                            if sources:
                                st.markdown("#### 📄 Sources Referenced")
                                for s in sources:
                                    with st.expander(f"View source: {s}"):
                                        match = run_query("SELECT raw_text FROM conversations WHERE file_name = ?", (s,))
                                        if match: st.text_area("Snippet", match[0][0][:1200] + "\n...", height=150, key=f"chat_{s}")
                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                        except Exception as e: st.error(f"Error communicating with local LLM: {e}")

elif page == "⚙ Settings":
    st.markdown("# ⚙ Settings")
    st.text_input("Markdown Export Directory", value=str(EXPORTS_DIR))
    st.text_input("SQLite Database Path", value=str(SQLITE_DB))
    st.text_input("ChromaDB Path", value=str(CHROMA_DB_DIR))
    st.success("🔒 Local privacy mode active. No data transmitted externally.")
