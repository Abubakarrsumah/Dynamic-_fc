import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime

# ==========================================
# 1. SETTINGS & BRANDING (DYNAMIC FC)
# ==========================================
st.set_page_config(page_title="Dynamic FC Pro", page_icon="⚽", layout="wide")

TEAM_NAME = "Dynamic FC Falaba District"
# Professional Tip: Use the raw URL of your logo if hosted on GitHub
LOGO_URL = "https://raw.githubusercontent.com/your-username/your-repo/main/1000096629.jpg" 

# ==========================================
# 2. DATABASE ENGINE (FIXED FOR CLOUD)
# ==========================================
def get_connection():
    # Cloud-compatible connection
    return sqlite3.connect("dynamic_fc_vault.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS admins (user TEXT PRIMARY KEY, pw TEXT, role TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS players 
              (id INTEGER PRIMARY KEY, name TEXT, pos TEXT, health TEXT, 
               performance_score INT, injury_status TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS finances 
              (id INTEGER PRIMARY KEY, date TEXT, category TEXT, type TEXT, 
               amount REAL, contributor TEXT, note TEXT)""")
    
    default_pw = hashlib.sha256("Falaba2024".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO admins VALUES ('admin', ?, 'SuperAdmin')", (default_pw,))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. AUTHENTICATION
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{TEAM_NAME}</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>'The Young Shall Grow'</p>", unsafe_allow_html=True)
    
    with st.columns([1,2,1])[1]: # Center the login form
        with st.form("login_gate"):
            u = st.text_input("Admin Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Secure Access"):
                hashed = hashlib.sha256(p.encode()).hexdigest()
                conn = get_connection()
                user = conn.execute("SELECT role FROM admins WHERE user=? AND pw=?", (u, hashed)).fetchone()
                conn.close()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.role = user[0]
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
def main_app():
    # Sidebar with Logo
    st.sidebar.markdown(f"## 🦅 {TEAM_NAME}")
    st.sidebar.info("Motto: The Young Shall Grow")
    
    page = st.sidebar.radio("Navigation", 
        ["Dashboard", "Squad Management", "Finance & Investors", "AI Coach"])

    if page == "Dashboard":
        st.title("📊 Club Performance")
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM finances", conn)
        conn.close()
        
        if not df.empty:
            income = df[df['type']=='Income']['amount'].sum()
            expense = df[df['type']=='Expenditure']['amount'].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Total Revenue", f"${income:,.2f}")
            c2.metric("Profit/Loss", f"${income-expense:,.2f}", delta=float(income-expense))
            
            fig = px.pie(df, values='amount', names='category', title="Spending vs Investment")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No financial data found in the cloud vault.")

    elif page == "Finance & Investors":
        st.title("💰 Investor & Expense Tracking")
        with st.form("fin"):
            t_type = st.selectbox("Type", ["Income", "Expenditure"])
            cat = st.selectbox("Category", ["Investor Contribution", "Sponsorship", "Kits/Equip", "Travel", "Other"])
            amt = st.number_input("Amount ($)", min_value=0.0)
            note = st.text_input("Details (e.g. Investor Name)")
            if st.form_submit_button("Record Transaction"):
                conn = get_connection()
                conn.execute("INSERT INTO finances (date, category, type, amount, note) VALUES (?,?,?,?,?)",
                             (datetime.now().strftime("%Y-%m-%d"), cat, t_type, amt, note))
                conn.commit()
                conn.close()
                st.success("Transaction Synced")

    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# Logic Gate
if not st.session_state.logged_in:
    login()
else:
    main_app()
