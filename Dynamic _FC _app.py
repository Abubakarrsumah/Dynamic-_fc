import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime
import base64

# ==========================================
# 1. SETTINGS & BRANDING
# ==========================================
st.set_page_config(page_title="Dynamic FC Pro", page_icon="⚽", layout="wide")

TEAM_NAME = "Dynamic FC Falaba District"
SLOGAN = "The Young Shall Grow - Since 2024"

# ==========================================
# 2. DATABASE ENGINE (BACK-END & SELF-HEALING)
# ==========================================
def get_connection():
    return sqlite3.connect("dynamic_fc_vault.db", check_same_thread=False)

def init_db():
    """Professional Self-Healing: Creates all SaaS tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()
    # Admin Table
    c.execute("CREATE TABLE IF NOT EXISTS admins (user TEXT PRIMARY KEY, pw TEXT, role TEXT)")
    # Players Table (Performance & Health)
    c.execute("""CREATE TABLE IF NOT EXISTS players 
              (id INTEGER PRIMARY KEY, name TEXT, pos TEXT, health TEXT, 
               performance_score INT, injury_status TEXT)""")
    # Finance Table (Income, Expenditure, Investor Contributions)
    c.execute("""CREATE TABLE IF NOT EXISTS finances 
              (id INTEGER PRIMARY KEY, date TEXT, category TEXT, type TEXT, 
               amount REAL, contributor TEXT, note TEXT)""")
    
    # Create Default Super Admin (Pass: Falaba2024)
    default_pw = hashlib.sha256("Falaba2024".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO admins VALUES ('admin', ?, 'SuperAdmin')", (default_pw,))
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. SECURITY & AUTHENTICATION
# ==========================================
def login():
    st.title(f"🦅 {TEAM_NAME}")
    st.subheader("SaaS Portal Login")
    with st.form("login"):
        u = st.text_input("Admin Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Secure Login"):
            hashed = hashlib.sha256(p.encode()).hexdigest()
            conn = get_connection()
            user = conn.execute("SELECT role FROM admins WHERE user=? AND pw=?", (u, hashed)).fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.role = user[0]
                st.rerun()
            else:
                st.error("Access Denied: Invalid Credentials")

# ==========================================
# 4. MAIN APPLICATION (FRONT-END)
# ==========================================
def main():
    st.sidebar.image("https://via.placeholder.com/150", caption=TEAM_NAME) # Replace with your logo path
    st.sidebar.title("Pro Dashboard")
    page = st.sidebar.selectbox("Navigate", 
        ["Analytics & Profit", "Squad & AI Scoring", "Financial Ledger", "AI Tactical Assistant", "System Integrations"])

    # --- SECTION: ANALYTICS ---
    if page == "Analytics & Profit":
        st.header("📊 Multi-Club Analytics")
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM finances", conn)
        
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            income = df[df['type']=='Income']['amount'].sum()
            expense = df[df['type']=='Expenditure']['amount'].sum()
            col1.metric("Total Income", f"${income:,.2f}")
            col2.metric("Total Expenditure", f"${expense:,.2f}")
            col3.metric("Net Profit", f"${income-expense:,.2f}")
            
            fig = px.bar(df, x='date', y='amount', color='type', title="Financial Flow")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet. Go to Financial Ledger to add records.")

    # --- SECTION: SQUAD & AI ---
    elif page == "Squad & AI Scoring":
        st.header("🏃‍♂️ Player Performance & Health AI")
        with st.expander("Register New Player / Record Status"):
            with st.form("p_form"):
                name = st.text_input("Full Name")
                pos = st.selectbox("Position", ["GK", "DEF", "MID", "FWD"])
                health = st.select_slider("Health Status", ["Injured", "Recovering", "Match Fit"])
                score = st.slider("Performance AI Score (0-100)", 0, 100, 50)
                if st.form_submit_button("Sync to Cloud"):
                    try:
                        conn = get_connection()
                        conn.execute("INSERT INTO players (name, pos, health, performance_score) VALUES (?,?,?,?)",
                                     (name, pos, health, score))
                        conn.commit()
                        st.success(f"{name} synced successfully.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # --- SECTION: FINANCES & INVESTORS ---
    elif page == "Financial Ledger":
        st.header("💰 Income, Expenditure & Investors")
        with st.form("fin_form"):
            f_type = st.selectbox("Type", ["Income", "Expenditure"])
            cat = st.selectbox("Category", ["Investor Contribution", "Match Fees", "Equipment", "Transport", "Salaries"])
            amt = st.number_input("Amount ($)", min_value=0.0)
            contributor = st.text_input("Contributor/Investor Name (If applicable)")
            note = st.text_area("Notes")
            if st.form_submit_button("Record Transaction"):
                conn = get_connection()
                date_now = datetime.now().strftime("%Y-%m-%d")
                conn.execute("INSERT INTO finances (date, category, type, amount, contributor, note) VALUES (?,?,?,?,?,?)",
                             (date_now, cat, f_type, amt, contributor, note))
                conn.commit()
                st.success("Record Saved. Profit summary updated.")

    # --- SECTION: AI ASSISTANT ---
    elif page == "AI Tactical Assistant":
        st.header("🤖 GPT-4 Coaching Assistant")
        prompt = st.text_input("Ask AI (e.g., 'Suggest a cone drill for 15-year-olds')")
        if st.button("Generate Tactical Report"):
            st.write("*(System Hook: Integration with OpenAI GPT-4 API occurs here)*")
            st.info("AI Logic: Based on your squad score (Avg 65%), I recommend high-intensity pressing drills.")

    # --- SECTION: INTEGRATIONS (WA/SMS/SaaS) ---
    elif page == "System Integrations":
        st.header("🔥 SaaS & API Control Panel")
        st.write("Activate your automated services here.")
        wa_key = st.text_input("WhatsApp Business API Key", type="password")
        if st.button("Send Daily WhatsApp Report to Investors"):
            st.warning("Connecting to Meta Cloud API...")
            st.error("Error: Valid API Key required.")

# ==========================================
# 5. EXECUTION LOGIC
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
else:
    main()
