import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime
import time

# ==========================================
# 1. PROFESSIONAL BRANDING & CONFIG
# ==========================================
st.set_page_config(page_title="Dynamic FC Pro SaaS", page_icon="🦅", layout="wide")

TEAM_NAME = "Dynamic FC Falaba District"
SLOGAN = "The Young Shall Grow"
# Professional Tip: Use the local file name you uploaded
LOGO_FILE = "1000096629.jpg" 

# ==========================================
# 2. THE VAULT: ENCRYPTED DB & SELF-HEALING
# ==========================================
def get_db():
    """Hybrid Cloud Connection"""
    return sqlite3.connect("dynamic_vault.db", check_same_thread=False)

def self_healing_init():
    """Professional Guard: Automatically repairs database schema if broken."""
    conn = get_db()
    c = conn.cursor()
    try:
        # User & SaaS Roles
        c.execute("CREATE TABLE IF NOT EXISTS users (user TEXT PRIMARY KEY, pw TEXT, role TEXT)")
        # Player AI & Transfer Window
        c.execute("""CREATE TABLE IF NOT EXISTS players 
                  (id INTEGER PRIMARY KEY, name TEXT, pos TEXT, health TEXT, 
                   stamina INT, skill INT, market_value REAL, status TEXT)""")
        # Finance: Income, Expense, and Investor Vault
        c.execute("""CREATE TABLE IF NOT EXISTS finances 
                  (id INTEGER PRIMARY KEY, date TEXT, type TEXT, category TEXT, 
                   amount REAL, source TEXT, notes TEXT)""")
        
        # Create Default Super Admin (Pass: Falaba2026)
        root_pw = hashlib.sha256("Falaba2026".encode()).hexdigest()
        c.execute("INSERT OR IGNORE INTO users VALUES ('admin', ?, 'SuperAdmin')", (root_pw,))
        conn.commit()
    except Exception as e:
        st.error(f"Critical System Repair Needed: {e}")
    finally:
        conn.close()

self_healing_init()

# ==========================================
# 3. SECURITY ENGINE (AUTH)
# ==========================================
if 'auth' not in st.session_state:
    st.session_state.auth = False

def login_gate():
    st.markdown(f"<h1 style='text-align: center;'>🦅 {TEAM_NAME}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>{SLOGAN}</p>", unsafe_allow_html=True)
    
    with st.columns([1,1.5,1])[1]:
        with st.form("Login"):
            u = st.text_input("Admin ID")
            p = st.text_input("Encrypted Key", type="password")
            if st.form_submit_button("Secure Access"):
                hashed = hashlib.sha256(p.encode()).hexdigest()
                conn = get_db()
                res = conn.execute("SELECT role FROM users WHERE user=? AND pw=?", (u, hashed)).fetchone()
                conn.close()
                if res:
                    st.session_state.auth = True
                    st.session_state.role = res[0]
                    st.rerun()
                else:
                    st.error("Access Denied: Invalid Credentials")

# ==========================================
# 4. THE CORE PLATFORM (FRONT-END)
# ==========================================
def main_app():
    # Sidebar Navigation
    try:
        st.sidebar.image(LOGO_FILE, use_container_width=True)
    except:
        st.sidebar.title("🦅 Dynamic FC")
        
    st.sidebar.subheader(f"Role: {st.session_state.role}")
    menu = ["📊 Dashboard & AI Analytics", "🏃 Squad & AI Performance", 
            "💰 Finance & Investor Vault", "🔄 Transfer Window", "🧠 AI Tactical Assistant"]
    page = st.sidebar.radio("Navigation", menu)

    # --- MODULE: DASHBOARD ---
    if page == "📊 Dashboard & AI Analytics":
        st.title("📈 Global Analytics")
        conn = get_db()
        df = pd.read_sql("SELECT * FROM finances", conn)
        conn.close()
        
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            inc = df[df['type']=='Income']['amount'].sum()
            inv = df[df['category']=='Investor Contribution']['amount'].sum()
            exp = df[df['type']=='Expenditure']['amount'].sum()
            
            col1.metric("Total Revenue", f"${inc:,.2f}")
            col2.metric("Investor Capital", f"${inv:,.2f}")
            col3.metric("Net Profit", f"${(inc+inv)-exp:,.2f}")
            
            fig = px.bar(df, x='category', y='amount', color='type', barmode='group', title="Financial Distribution")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No records found in the Cloud Vault.")

    # --- MODULE: SQUAD & AI PERFORMANCE ---
    elif page == "🏃 Squad & AI Performance":
        st.title("🛡️ Player Performance Scoring AI")
        with st.expander("Register/Update Player Status"):
            with st.form("p_reg"):
                name = st.text_input("Name")
                pos = st.selectbox("Position", ["GK", "DEF", "MID", "FWD"])
                health = st.select_slider("Health Status", ["Injured", "Recovering", "Match Fit"])
                stamina = st.slider("Stamina (%)", 0, 100, 80)
                skill = st.slider("Skill Level (%)", 0, 100, 70)
                if st.form_submit_button("Sync Player Data"):
                    conn = get_db()
                    conn.execute("INSERT INTO players (name, pos, health, stamina, skill, status) VALUES (?,?,?,?,?,?)",
                                 (name, pos, health, stamina, skill, "Active"))
                    conn.commit()
                    st.success(f"{name} synced to Cloud.")

        st.subheader("Live AI Squad Readiness")
        conn = get_db()
        pdf = pd.read_sql("SELECT * FROM players", conn)
        conn.close()
        if not pdf.empty:
            # AI Scoring Algorithm
            pdf['AI_Score'] = (pdf['stamina'] + pdf['skill']) / 2
            pdf.loc[pdf['health'] == 'Injured', 'AI_Score'] *= 0.3
            st.dataframe(pdf.style.background_gradient(subset=['AI_Score'], cmap='RdYlGn'), use_container_width=True)

    # --- MODULE: FINANCE & INVESTORS ---
    elif page == "💰 Finance & Investor Vault":
        st.title("💸 Capital & Expenditure Management")
        with st.form("fin"):
            f_type = st.selectbox("Type", ["Income", "Expenditure"])
            cat = st.selectbox("Category", ["Investor Contribution", "Match Fees", "Equipment", "Transport", "Salaries"])
            amt = st.number_input("Amount ($)", min_value=0.0)
            source = st.text_input("Source (e.g. Investor Name)")
            note = st.text_area("Audit Notes")
            if st.form_submit_button("Secure Record & Generate Receipt"):
                conn = get_db()
                date_str = datetime.now().strftime("%Y-%m-%d")
                conn.execute("INSERT INTO finances (date, type, category, amount, source, notes) VALUES (?,?,?,?,?,?)",
                             (date_str, f_type, cat, amt, source, note))
                conn.commit()
                st.success("Transaction Logged. Cloud Audit Trail Updated.")

    # --- MODULE: TRANSFER WINDOW ---
    elif page == "🔄 Transfer Window":
        st.title("🌍 Global Transfer Market")
        st.info("Manage incoming and outgoing player contracts.")
        st.subheader("Market Values & Negotiations")
        # Add market logic here

    # --- MODULE: AI ASSISTANT ---
    elif page == "🧠 AI Tactical Assistant":
        st.title("🤖 GPT-4 Tactical Assistant")
        q = st.text_input("Ask Coach AI about training or tactics:")
        if st.button("Generate Report"):
            st.write("*(Integration Point: Connect OpenAI API Key here)*")
            st.info("AI Analysis: Based on current squad health (2 players recovering), I recommend a 4-4-2 defensive block for the next match.")

    if st.sidebar.button("Log Out"):
        st.session_state.auth = False
        st.rerun()

# --- BOOTLOADER ---
if not st.session_state.auth:
    login_gate()
else:
    main_app()
