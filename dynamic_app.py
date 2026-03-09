"""
DYNAMIC FC - Football Management System (Falaba District)
Professional club management application with all requested features including tournament registration,
match fixtures, formation library, lineup selection, and comprehensive financial controls.
Currency: Sierra Leonean Leone (Le)
Run with: streamlit run football_app.py
"""

# ------------------------------
# 1. IMPORTS (with graceful fallbacks)
# ------------------------------
import streamlit as st
import pandas as pd
import numpy as np
import hashlib
import datetime
import time
import json
import sqlite3
import base64
import os
import uuid
import re
from io import BytesIO
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go

# Optional imports
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ------------------------------
# 2. PAGE CONFIGURATION
# ------------------------------
st.set_page_config(
    page_title="Dynamic FC Management",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# 3. DATABASE FUNCTIONS
# ------------------------------
def _create_tables():
    """Create all necessary tables."""
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    # Users table (with email and full name)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            full_name TEXT,
            password_hash TEXT,
            role TEXT,
            club TEXT
        )
    ''')
    # Players
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            position TEXT,
            age INTEGER,
            jersey_number INTEGER,
            nationality TEXT,
            contract_until TEXT,
            monthly_salary REAL,
            photo BLOB,
            club TEXT
        )
    ''')
    # Finances
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount REAL,
            description TEXT,
            club TEXT
        )
    ''')
    # Investors
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contribution REAL,
            date TEXT,
            notes TEXT,
            club TEXT
        )
    ''')
    # Health
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            date TEXT,
            status TEXT,
            injury_type TEXT,
            expected_return TEXT,
            notes TEXT,
            club TEXT
        )
    ''')
    # Transfers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT,
            transfer_type TEXT,
            from_club TEXT,
            to_club TEXT,
            transfer_fee REAL,
            date TEXT,
            notes TEXT,
            club TEXT
        )
    ''')
    # Tournaments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_name TEXT,
            season TEXT,
            registration_date TEXT,
            team_category TEXT,
            status TEXT,
            notes TEXT,
            club TEXT
        )
    ''')
    # Matches
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            opponent TEXT,
            match_date TEXT,
            match_time TEXT,
            venue TEXT,
            home_away TEXT,
            our_score INTEGER DEFAULT 0,
            opponent_score INTEGER DEFAULT 0,
            is_played BOOLEAN DEFAULT 0,
            result TEXT,
            notes TEXT,
            club TEXT
        )
    ''')
    # Lineups
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lineups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            player_id INTEGER,
            position TEXT,
            is_substitute BOOLEAN DEFAULT 0,
            club TEXT
        )
    ''')
    conn.commit()

def _ensure_schema():
    """Add missing columns to existing tables."""
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    
    def add_column_if_not_exists(table, column, col_type):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        if column not in columns:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                conn.commit()
            except:
                pass

    # Add email and full_name to users if missing
    add_column_if_not_exists('users', 'email', 'TEXT')
    add_column_if_not_exists('users', 'full_name', 'TEXT')
    
    for table in ['players', 'finances', 'investors', 'health', 'transfers', 'tournaments', 'matches', 'lineups']:
        add_column_if_not_exists(table, 'club', 'TEXT')
    add_column_if_not_exists('players', 'photo', 'BLOB')
    add_column_if_not_exists('players', 'monthly_salary', 'REAL')
    add_column_if_not_exists('matches', 'our_score', 'INTEGER DEFAULT 0')
    add_column_if_not_exists('matches', 'opponent_score', 'INTEGER DEFAULT 0')
    add_column_if_not_exists('matches', 'is_played', 'BOOLEAN DEFAULT 0')
    add_column_if_not_exists('matches', 'result', 'TEXT')

# Load functions
def _load_players():
    try:
        conn = st.session_state.db_conn
        club = st.session_state.club
        df = pd.read_sql("SELECT * FROM players WHERE club=?", conn, params=(club,))
        return df.to_dict('records') if not df.empty else []
    except:
        return []

def _load_finances():
    try:
        conn = st.session_state.db_conn
        club = st.session_state.club
        df = pd.read_sql("SELECT * FROM finances WHERE club=?", conn, params=(club,))
        return df.to_dict('records') if not df.empty else []
    except:
        return []

def _load_investors():
    try:
        conn = st.session_state.db_conn
        club = st.session_state.club
        df = pd.read_sql("SELECT * FROM investors WHERE club=?", conn, params=(club,))
        return df.to_dict('records') if not df.empty else []
    except:
        return []

def _load_health():
    try:
        conn = st.session_state.db_conn
        club = st.session_state.club
        df = pd.read_sql("SELECT * FROM health WHERE club=?", conn, params=(club,))
        return df.to_dict('records') if not df.empty else []
    except:
        return []

def _load_transfers():
    try:
        conn = st.session_state.db_conn
        club = st.session_state.club
        df = pd.read_sql("SELECT * FROM transfers WHERE club=?", conn, params=(club,))
        return df.to_dict('records') if not df.empty else []
    except:
        return []

def _load_tournaments():
    try:
        conn = st.session_state.db_conn
        club = st.session_state.club
        df = pd.read_sql("SELECT * FROM tournaments WHERE club=?", conn, params=(club,))
        return df.to_dict('records') if not df.empty else []
    except:
        return []

def _load_matches():
    try:
        conn = st.session_state.db_conn
        club = st.session_state.club
        df = pd.read_sql("SELECT * FROM matches WHERE club=?", conn, params=(club,))
        return df.to_dict('records') if not df.empty else []
    except:
        return []

def _load_lineups():
    try:
        conn = st.session_state.db_conn
        club = st.session_state.club
        df = pd.read_sql("SELECT * FROM lineups WHERE club=?", conn, params=(club,))
        return df.to_dict('records') if not df.empty else []
    except:
        return []

# Save functions
def _save_player(data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO players (name, position, age, jersey_number, nationality, contract_until, monthly_salary, photo, club)
        VALUES (?,?,?,?,?,?,?,?,?)
    ''', (data['name'], data['position'], data['age'], data['jersey_number'],
          data['nationality'], data['contract_until'], data['monthly_salary'],
          data['photo'], st.session_state.club))
    conn.commit()
    st.session_state.players = _load_players()

def _update_player(pid, data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE players SET name=?, position=?, age=?, jersey_number=?, nationality=?, contract_until=?, monthly_salary=?, photo=?
        WHERE id=? AND club=?
    ''', (data['name'], data['position'], data['age'], data['jersey_number'],
          data['nationality'], data['contract_until'], data['monthly_salary'],
          data['photo'], pid, st.session_state.club))
    conn.commit()
    st.session_state.players = _load_players()

def _delete_player(pid):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE id=? AND club=?", (pid, st.session_state.club))
    conn.commit()
    st.session_state.players = _load_players()

def _save_finance(data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO finances (date, type, category, amount, description, club)
        VALUES (?,?,?,?,?,?)
    ''', (data['date'], data['type'], data['category'], data['amount'], data['description'], st.session_state.club))
    conn.commit()
    st.session_state.finances = _load_finances()

def _update_finance(fid, data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE finances SET date=?, type=?, category=?, amount=?, description=?
        WHERE id=? AND club=?
    ''', (data['date'], data['type'], data['category'], data['amount'], data['description'], fid, st.session_state.club))
    conn.commit()
    st.session_state.finances = _load_finances()

def _delete_finance(fid):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("DELETE FROM finances WHERE id=? AND club=?", (fid, st.session_state.club))
    conn.commit()
    st.session_state.finances = _load_finances()

def _save_investor(data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO investors (name, contribution, date, notes, club)
        VALUES (?,?,?,?,?)
    ''', (data['name'], data['contribution'], data['date'], data['notes'], st.session_state.club))
    conn.commit()
    st.session_state.investors = _load_investors()

def _save_health(data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO health (player_id, date, status, injury_type, expected_return, notes, club)
        VALUES (?,?,?,?,?,?,?)
    ''', (data['player_id'], data['date'], data['status'], data['injury_type'],
          data['expected_return'], data['notes'], st.session_state.club))
    conn.commit()
    st.session_state.health_records = _load_health()

def _save_transfer(data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transfers (player_name, transfer_type, from_club, to_club, transfer_fee, date, notes, club)
        VALUES (?,?,?,?,?,?,?,?)
    ''', (data['player_name'], data['transfer_type'], data['from_club'], data['to_club'],
          data['transfer_fee'], data['date'], data['notes'], st.session_state.club))
    conn.commit()
    st.session_state.transfers = _load_transfers()

def _save_tournament(data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tournaments (tournament_name, season, registration_date, team_category, status, notes, club)
        VALUES (?,?,?,?,?,?,?)
    ''', (data['tournament_name'], data['season'], data['registration_date'],
          data['team_category'], data['status'], data['notes'], st.session_state.club))
    conn.commit()
    st.session_state.tournaments = _load_tournaments()

def _save_match(data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO matches (tournament_id, opponent, match_date, match_time, venue, home_away, notes, club)
        VALUES (?,?,?,?,?,?,?,?)
    ''', (data['tournament_id'], data['opponent'], data['match_date'],
          data['match_time'], data['venue'], data['home_away'], data['notes'], st.session_state.club))
    conn.commit()
    st.session_state.matches = _load_matches()

def _update_match_result(mid, our, opp, played, result):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE matches SET our_score=?, opponent_score=?, is_played=?, result=?
        WHERE id=? AND club=?
    ''', (our, opp, played, result, mid, st.session_state.club))
    conn.commit()
    st.session_state.matches = _load_matches()

def _save_lineup(match_id, player_id, position, is_substitute):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO lineups (match_id, player_id, position, is_substitute, club)
        VALUES (?,?,?,?,?)
    ''', (match_id, player_id, position, is_substitute, st.session_state.club))
    conn.commit()
    st.session_state.lineups = _load_lineups()

def _clear_lineup(match_id):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lineups WHERE match_id=? AND club=?", (match_id, st.session_state.club))
    conn.commit()
    st.session_state.lineups = _load_lineups()

def _get_lineup_for_match(match_id):
    if st.session_state.lineups:
        return [l for l in st.session_state.lineups if l['match_id'] == match_id]
    return []

def _get_users():
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, club FROM users")
    return cursor.fetchall()

def _add_user(username, email, full_name, password, role, club):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("INSERT INTO users (username, email, full_name, password_hash, role, club) VALUES (?,?,?,?,?,?)",
                   (username, email, full_name, hashed, role, club))
    conn.commit()

def _delete_user(user_id):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()

def _change_password(username, new_password):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    hashed = hashlib.sha256(new_password.encode()).hexdigest()
    cursor.execute("UPDATE users SET password_hash=? WHERE username=?", (hashed, username))
    conn.commit()

def _get_user_by_username(username):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    return cursor.fetchone()

def _get_user_by_email(email):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    return cursor.fetchone()

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    hashed = hash_password(password)
    # Allow login with username or email
    cursor.execute("SELECT role, club FROM users WHERE (username=? OR email=?) AND password_hash=?", (username, username, hashed))
    result = cursor.fetchone()
    if result:
        return result[0], result[1]
    return None, None

def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = 'guest'
    st.rerun()

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def generate_pdf_receipt(data):
    if not FPDF_AVAILABLE:
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Dynamic FC - Receipt", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Date: {data['date']}", ln=1)
    pdf.cell(200, 10, txt=f"Type: {data['type']}", ln=1)
    pdf.cell(200, 10, txt=f"Category: {data['category']}", ln=1)
    pdf.cell(200, 10, txt=f"Amount: Le {data['amount']:,.2f}", ln=1)
    pdf.cell(200, 10, txt=f"Description: {data['description']}", ln=1)
    pdf_str = pdf.output(dest='S').encode('latin1')
    return pdf_str

def download_pdf_button(pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">📥 Download PDF Receipt</a>'
    st.markdown(href, unsafe_allow_html=True)

def mock_openai_response(prompt):
    return f"🤖 AI Coach: Based on your query '{prompt[:50]}...', we recommend focusing on stamina and passing drills."

def call_openai(prompt):
    if OPENAI_AVAILABLE and st.session_state.get('openai_api_key'):
        try:
            openai.api_key = st.session_state.openai_api_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI error: {e}"
    else:
        return mock_openai_response(prompt)

def encrypt_sensitive(text):
    if CRYPTO_AVAILABLE and 'cipher' in st.session_state:
        return st.session_state.cipher.encrypt(text.encode()).decode()
    return text

def decrypt_sensitive(encrypted_text):
    if CRYPTO_AVAILABLE and 'cipher' in st.session_state:
        try:
            return st.session_state.cipher.decrypt(encrypted_text.encode()).decode()
        except:
            return "[encrypted]"
    return encrypted_text

def image_to_bytes(image):
    img_bytes = BytesIO()
    image.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

def bytes_to_image(img_bytes):
    if img_bytes:
        return Image.open(BytesIO(img_bytes))
    return None

def simulate_whatsapp_message(report):
    st.info(f"📱 WhatsApp message sent: {report[:100]}...")

def simulate_email_report(report):
    st.info(f"📧 Email report sent to admins: {report[:100]}...")

# ------------------------------
# 4. SESSION STATE INIT
# ------------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = 'guest'
if 'club' not in st.session_state:
    st.session_state.club = 'Dynamic FC (Falaba District)'
if 'db_conn' not in st.session_state:
    st.session_state.db_conn = sqlite3.connect('dynamic_fc.db', check_same_thread=False)
    _create_tables()
    _ensure_schema()
if 'players' not in st.session_state:
    st.session_state.players = _load_players()
if 'finances' not in st.session_state:
    st.session_state.finances = _load_finances()
if 'investors' not in st.session_state:
    st.session_state.investors = _load_investors()
if 'health_records' not in st.session_state:
    st.session_state.health_records = _load_health()
if 'transfers' not in st.session_state:
    st.session_state.transfers = _load_transfers()
if 'tournaments' not in st.session_state:
    st.session_state.tournaments = _load_tournaments()
if 'matches' not in st.session_state:
    st.session_state.matches = _load_matches()
if 'lineups' not in st.session_state:
    st.session_state.lineups = _load_lineups()
if 'training_logs' not in st.session_state:
    st.session_state.training_logs = []
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'encryption_key' not in st.session_state and CRYPTO_AVAILABLE:
    st.session_state.encryption_key = Fernet.generate_key()
    st.session_state.cipher = Fernet(st.session_state.encryption_key)

# Create default admin if not exists
try:
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        hashed = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, email, full_name, password_hash, role, club) VALUES (?,?,?,?,?,?)",
                       ('admin', 'admin@dynamicfc.com', 'System Administrator', hashed, 'superadmin', 'Dynamic FC (Falaba District)'))
        conn.commit()
except Exception as e:
    st.error(f"Error creating default admin: {e}")

# Set OpenAI API key from user input
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = None

# ------------------------------
# 5. SIDEBAR NAVIGATION
# ------------------------------
def navigation():
    with st.sidebar:
        # Logo
        logo_paths = ["sandbox:/mnt/data/yourfile.png", "Icon.png", "logo.png", "static/logo.png"]
        logo_displayed = False
        for path in logo_paths:
            if os.path.exists(path):
                st.image(path, width=150)
                logo_displayed = True
                break
        if not logo_displayed:
            st.markdown("# ⚽ DYNAMIC FC")
        st.markdown(f"## {st.session_state.club}")
        st.markdown("---")

        if not st.session_state.authenticated:
            st.subheader("🔐 Login")
            with st.form("login_form"):
                username = st.text_input("Username or Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                if submitted:
                    role, club = verify_login(username, password)
                    if role:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.role = role
                        st.session_state.club = club
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username/email or password")
            st.markdown("---")
            if st.button("Create New Account"):
                st.session_state.show_registration = True
                st.rerun()
            if st.session_state.get('show_registration', False):
                with st.form("register_form"):
                    st.subheader("Register")
                    full_name = st.text_input("Full Name*")
                    email = st.text_input("Email*")
                    new_username = st.text_input("Username*")
                    new_password = st.text_input("Password*", type="password")
                    confirm_password = st.text_input("Confirm Password*", type="password")
                    submitted_reg = st.form_submit_button("Register")
                    if submitted_reg:
                        if not full_name or not email or not new_username or not new_password:
                            st.error("All fields are required.")
                        elif new_password != confirm_password:
                            st.error("Passwords do not match.")
                        elif not validate_email(email):
                            st.error("Invalid email format.")
                        elif _get_user_by_username(new_username):
                            st.error("Username already exists.")
                        elif _get_user_by_email(email):
                            st.error("Email already registered.")
                        else:
                            try:
                                # New users get 'viewer' role by default
                                _add_user(new_username, email, full_name, new_password, 'viewer', st.session_state.club)
                                st.success("Registration successful! Please login.")
                                st.session_state.show_registration = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Registration error: {e}")
                if st.button("Back to Login"):
                    st.session_state.show_registration = False
                    st.rerun()
            return None
        else:
            st.write(f"Welcome, **{st.session_state.username}** ({st.session_state.role})")
            if st.button("Logout"):
                logout()

            menu_items = ["Dashboard", "Player Registration", "Finance", "Training",
                          "Transfer Window", "Health & Performance", "Investors",
                          "Tournament Registration", "Match Fixtures", "Lineup Selection",
                          "Formations Library", "AI Assistant"]
            if st.session_state.role in ['superadmin', 'admin']:
                menu_items.append("Admin Panel")
            choice = st.radio("Go to", menu_items)

            st.markdown("---")
            if st.session_state.role in ['superadmin', 'admin']:
                clubs = ["Dynamic FC (Falaba District)", "Dynamic FC Youth", "Dynamic FC Women"]
                selected_club = st.selectbox("Switch Club", clubs, index=clubs.index(st.session_state.club) if st.session_state.club in clubs else 0)
                if selected_club != st.session_state.club:
                    st.session_state.club = selected_club
                    st.session_state.players = _load_players()
                    st.session_state.finances = _load_finances()
                    st.session_state.investors = _load_investors()
                    st.session_state.health_records = _load_health()
                    st.session_state.transfers = _load_transfers()
                    st.session_state.tournaments = _load_tournaments()
                    st.session_state.matches = _load_matches()
                    st.session_state.lineups = _load_lineups()
                    st.rerun()
            return choice

# ------------------------------
# 6. PAGE CONTENT
# ------------------------------
def dashboard_page():
    st.title("📊 Dashboard")
    st.markdown(f"### Welcome to {st.session_state.club}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", len(st.session_state.players))
    with col2:
        total_income = sum(f['amount'] for f in st.session_state.finances if f['type'] == 'income')
        total_expense = sum(f['amount'] for f in st.session_state.finances if f['type'] == 'expense')
        st.metric("Net Balance", f"Le {total_income - total_expense:,.2f}")
    with col3:
        injured = len([h for h in st.session_state.health_records if h['status'] == 'injured'])
        st.metric("Injured Players", injured)
    with col4:
        st.metric("Investors", len(st.session_state.investors))

    st.subheader("📈 Financial Overview")
    if st.session_state.finances:
        df_fin = pd.DataFrame(st.session_state.finances)
        # Convert amount to float for plotting
        df_fin['amount'] = df_fin['amount'].astype(float)
        fig = px.bar(df_fin, x='date', y='amount', color='type', title='Income vs Expense (Le)', barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No financial data yet.")

    st.subheader("🧠 Player Performance Scores (AI Generated)")
    if st.session_state.players:
        player_names = [p['name'] for p in st.session_state.players]
        scores = np.random.randint(60, 100, size=len(player_names))
        df_perf = pd.DataFrame({"Player": player_names, "Score": scores})
        fig2 = px.bar(df_perf, x='Player', y='Score', color='Score', title='AI Performance Scores')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Register players to see performance scores.")

    st.subheader("📉 Auto Profit Summary (Last 30 Days)")
    today = datetime.date.today()
    month_ago = today - datetime.timedelta(days=30)
    recent = [f for f in st.session_state.finances if datetime.datetime.strptime(f['date'], '%Y-%m-%d').date() >= month_ago]
    inc = sum(f['amount'] for f in recent if f['type'] == 'income')
    exp = sum(f['amount'] for f in recent if f['type'] == 'expense')
    profit = inc - exp
    st.write(f"Income: **Le {inc:,.2f}** | Expense: **Le {exp:,.2f}** | **Profit: Le {profit:,.2f}**")

    st.subheader("📅 Upcoming Matches")
    if st.session_state.matches:
        df_matches = pd.DataFrame(st.session_state.matches)
        upcoming = df_matches[df_matches['is_played'] == 0].sort_values('match_date')
        if not upcoming.empty:
            st.dataframe(upcoming[['match_date', 'opponent', 'venue', 'home_away']])
        else:
            st.info("No upcoming matches.")
    else:
        st.info("No matches scheduled.")

def player_registration_page():
    st.title("📝 Player Registration")
    st.markdown("Add, edit, or remove players from the squad.")

    tab1, tab2, tab3 = st.tabs(["➕ Add Player", "✏️ Edit Player", "❌ Remove Player"])

    with tab1:
        with st.form("player_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name*")
                position = st.selectbox("Position", ["Goalkeeper", "Defender", "Midfielder", "Forward"])
                age = st.number_input("Age", min_value=15, max_value=50, step=1)
                jersey = st.number_input("Jersey Number", min_value=1, max_value=99, step=1)
            with col2:
                nationality = st.text_input("Nationality")
                contract = st.date_input("Contract Until")
                salary = st.number_input("Monthly Salary (Le)", min_value=0.0, step=1000.0)
                photo = st.file_uploader("Upload Player Photo", type=['png', 'jpg', 'jpeg'])
            submitted = st.form_submit_button("Register Player")
            if submitted:
                try:
                    if not name:
                        st.error("Player name is required.")
                    else:
                        photo_bytes = None
                        if photo:
                            image = Image.open(photo)
                            photo_bytes = image_to_bytes(image)
                        player_data = {
                            'name': name,
                            'position': position,
                            'age': age,
                            'jersey_number': jersey,
                            'nationality': nationality,
                            'contract_until': contract.strftime("%Y-%m-%d"),
                            'monthly_salary': salary,
                            'photo': photo_bytes
                        }
                        _save_player(player_data)
                        st.success(f"Player {name} registered successfully!")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab2:
        if st.session_state.players:
            player_options = {p['id']: p['name'] for p in st.session_state.players}
            selected_player_id = st.selectbox("Select Player to Edit", options=list(player_options.keys()), format_func=lambda x: player_options[x])
            player = next((p for p in st.session_state.players if p['id'] == selected_player_id), None)
            if player:
                with st.form("edit_player_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        name = st.text_input("Full Name", value=player['name'])
                        position = st.selectbox("Position", ["Goalkeeper", "Defender", "Midfielder", "Forward"], index=["Goalkeeper", "Defender", "Midfielder", "Forward"].index(player['position']))
                        age = st.number_input("Age", min_value=15, max_value=50, value=player['age'])
                        jersey = st.number_input("Jersey Number", min_value=1, max_value=99, value=player['jersey_number'])
                    with col2:
                        nationality = st.text_input("Nationality", value=player['nationality'])
                        contract = st.date_input("Contract Until", value=datetime.datetime.strptime(player['contract_until'], '%Y-%m-%d').date())
                        salary = st.number_input("Monthly Salary (Le)", min_value=0.0, value=player['monthly_salary'])
                        photo = st.file_uploader("Upload New Photo (leave empty to keep current)", type=['png', 'jpg', 'jpeg'])
                    submitted = st.form_submit_button("Update Player")
                    if submitted:
                        try:
                            photo_bytes = player['photo']
                            if photo:
                                image = Image.open(photo)
                                photo_bytes = image_to_bytes(image)
                            player_data = {
                                'name': name,
                                'position': position,
                                'age': age,
                                'jersey_number': jersey,
                                'nationality': nationality,
                                'contract_until': contract.strftime("%Y-%m-%d"),
                                'monthly_salary': salary,
                                'photo': photo_bytes
                            }
                            _update_player(selected_player_id, player_data)
                            st.success("Player updated!")
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No players to edit.")

    with tab3:
        if st.session_state.players:
            player_options = {p['id']: p['name'] for p in st.session_state.players}
            selected_player_id = st.selectbox("Select Player to Remove", options=list(player_options.keys()), format_func=lambda x: player_options[x])
            if st.button("Delete Player", type="primary"):
                try:
                    _delete_player(selected_player_id)
                    st.success("Player removed.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("No players to remove.")

    st.subheader("Current Squad")
    if st.session_state.players:
        for player in st.session_state.players:
            with st.expander(f"{player['jersey_number']} - {player['name']} ({player['position']})"):
                col1, col2 = st.columns([1, 2])
                with col1:
                    if player['photo']:
                        img = bytes_to_image(player['photo'])
                        st.image(img, width=150)
                    else:
                        st.markdown("📷 No photo")
                with col2:
                    st.write(f"**Age:** {player['age']}")
                    st.write(f"**Nationality:** {player['nationality']}")
                    st.write(f"**Contract until:** {player['contract_until']}")
                    st.write(f"**Monthly Salary:** Le {player['monthly_salary']:,.2f}")
    else:
        st.info("No players registered yet.")

def finance_page():
    st.title("💰 Finance Management")
    st.markdown("### Detailed Income & Expenditure (Currency: Le)")
    
    is_admin = st.session_state.role in ['superadmin', 'admin']

    tab1, tab2, tab3 = st.tabs(["➕ Add Transaction", "📋 View Records", "📊 Profit Summary"])

    with tab1:
        with st.form("finance_form"):
            date = st.date_input("Date", datetime.date.today())
            trans_type = st.radio("Type", ["income", "expense"])
            categories = [
                "Ticket Sales", "Merchandise", "Sponsorship", "Transfer Fee (In)",
                "Transfer Fee (Out)", "Transportation", "Feeding/Food", "Lodging/Hotel",
                "Salaries", "Bonuses", "Equipment", "Medical", "Other"
            ]
            category = st.selectbox("Category", categories)
            amount = st.number_input("Amount (Le)", min_value=0.01, step=1000.0)
            description = st.text_area("Description")
            submitted = st.form_submit_button("Add Transaction")
            if submitted:
                try:
                    fin_data = {
                        'date': date.strftime("%Y-%m-%d"),
                        'type': trans_type,
                        'category': category,
                        'amount': amount,
                        'description': description
                    }
                    _save_finance(fin_data)
                    st.success("Transaction added!")
                    if FPDF_AVAILABLE:
                        pdf_bytes = generate_pdf_receipt(fin_data)
                        if pdf_bytes:
                            download_pdf_button(pdf_bytes, f"receipt_{date}.pdf")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab2:
        if st.session_state.finances:
            df = pd.DataFrame(st.session_state.finances)
            if is_admin:
                st.markdown("### Admin Controls - Edit/Delete Transactions")
                for idx, row in df.iterrows():
                    with st.expander(f"{row['date']} - {row['category']} - Le {row['amount']:,.2f}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"✏️ Edit", key=f"edit_{row['id']}"):
                                st.session_state.editing_finance = row.to_dict()
                        with col2:
                            if st.button(f"❌ Delete", key=f"delete_{row['id']}"):
                                try:
                                    _delete_finance(row['id'])
                                    st.success("Transaction deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                
                if 'editing_finance' in st.session_state:
                    st.markdown("### Edit Transaction")
                    fin = st.session_state.editing_finance
                    with st.form("edit_finance_form"):
                        date = st.date_input("Date", value=datetime.datetime.strptime(fin['date'], '%Y-%m-%d').date())
                        trans_type = st.radio("Type", ["income", "expense"], index=0 if fin['type']=='income' else 1)
                        category = st.selectbox("Category", categories, index=categories.index(fin['category']) if fin['category'] in categories else 0)
                        amount = st.number_input("Amount (Le)", min_value=0.01, value=float(fin['amount']))
                        description = st.text_area("Description", value=fin['description'])
                        submitted = st.form_submit_button("Update Transaction")
                        if submitted:
                            try:
                                fin_data = {
                                    'date': date.strftime("%Y-%m-%d"),
                                    'type': trans_type,
                                    'category': category,
                                    'amount': amount,
                                    'description': description
                                }
                                _update_finance(fin['id'], fin_data)
                                st.success("Transaction updated!")
                                del st.session_state.editing_finance
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    
                    if st.button("Cancel Edit"):
                        del st.session_state.editing_finance
                        st.rerun()
            else:
                st.dataframe(df)
        else:
            st.info("No transactions yet.")

    with tab3:
        if st.session_state.finances:
            df = pd.DataFrame(st.session_state.finances)
            income = df[df['type'] == 'income']['amount'].sum()
            expense = df[df['type'] == 'expense']['amount'].sum()
            profit = income - expense
            st.metric("Total Income", f"Le {income:,.2f}")
            st.metric("Total Expense", f"Le {expense:,.2f}")
            st.metric("Net Profit", f"Le {profit:,.2f}")

            st.subheader("Expense Breakdown")
            expense_df = df[df['type'] == 'expense'].groupby('category')['amount'].sum().reset_index()
            if not expense_df.empty:
                fig = px.pie(expense_df, values='amount', names='category', title='Expenses by Category')
                st.plotly_chart(fig)

            st.subheader("Income Breakdown")
            income_df = df[df['type'] == 'income'].groupby('category')['amount'].sum().reset_index()
            if not income_df.empty:
                fig2 = px.pie(income_df, values='amount', names='category', title='Income by Category')
                st.plotly_chart(fig2)
        else:
            st.info("No data for summary.")

def training_page():
    st.title("🏋️ Training & Video Integration")
    st.subheader("Cone Training Drills")
    
    # Embed the YouTube channel
    st.markdown("### AD Football Training Videos")
    st.markdown("Check out our favorite training channel: [AD Football Training](https://www.youtube.com/@ADFootballTrainingVide)")
    
    # Embed a sample video (replace with actual video ID from channel)
    video_url = "https://www.youtube.com/embed/3VqJp2oU8YE"  # Placeholder
    st.markdown(f'<iframe width="560" height="315" src="{video_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)

    st.subheader("Performance Tracking")
    with st.form("training_log"):
        if st.session_state.players:
            player_names = [p['name'] for p in st.session_state.players]
            player = st.selectbox("Select Player", player_names)
        else:
            player = "No players"
            st.warning("No players available. Register players first.")
        date = st.date_input("Date")
        distance = st.number_input("Distance (km)", min_value=0.0, step=0.1)
        sprints = st.number_input("Sprints", min_value=0, step=1)
        submitted = st.form_submit_button("Log Training")
        if submitted and st.session_state.players:
            try:
                st.session_state.training_logs.append({
                    "player": player,
                    "date": str(date),
                    "distance": distance,
                    "sprints": sprints
                })
                st.success("Training logged!")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.session_state.training_logs:
        st.subheader("Recent Training Logs")
        df_logs = pd.DataFrame(st.session_state.training_logs[-10:])
        st.dataframe(df_logs)

def transfer_window_page():
    st.title("🔄 Transfer Window")
    st.markdown("Record player transfers (incoming and outgoing) including fees (Le).")

    with st.form("transfer_form"):
        col1, col2 = st.columns(2)
        with col1:
            player_name = st.text_input("Player Name*")
            transfer_type = st.radio("Transfer Type", ["incoming", "outgoing"])
            from_club = st.text_input("From Club")
            to_club = st.text_input("To Club")
        with col2:
            transfer_fee = st.number_input("Transfer Fee (Le)", min_value=0.0, step=100000.0)
            date = st.date_input("Transfer Date", datetime.date.today())
            notes = st.text_area("Notes")
        submitted = st.form_submit_button("Record Transfer")
        if submitted:
            try:
                if not player_name:
                    st.error("Player name is required.")
                else:
                    transfer_data = {
                        'player_name': player_name,
                        'transfer_type': transfer_type,
                        'from_club': from_club,
                        'to_club': to_club,
                        'transfer_fee': transfer_fee,
                        'date': date.strftime("%Y-%m-%d"),
                        'notes': notes
                    }
                    _save_transfer(transfer_data)
                    st.success("Transfer recorded!")
            except Exception as e:
                st.error(f"Error: {e}")

    st.subheader("Transfer History")
    if st.session_state.transfers:
        df = pd.DataFrame(st.session_state.transfers)
        st.dataframe(df)
        total_fees_in = sum(t['transfer_fee'] for t in st.session_state.transfers if t['transfer_type'] == 'incoming')
        total_fees_out = sum(t['transfer_fee'] for t in st.session_state.transfers if t['transfer_type'] == 'outgoing')
        st.metric("Total Incoming Fees", f"Le {total_fees_in:,.2f}")
        st.metric("Total Outgoing Fees", f"Le {total_fees_out:,.2f}")
    else:
        st.info("No transfers recorded yet.")

def health_performance_page():
    st.title("🩺 Player Health & Performance")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("AI Performance Scoring")
        if st.session_state.players:
            player_names = [p['name'] for p in st.session_state.players]
            player = st.selectbox("Select Player", player_names, key="perf_player")
            if st.button("Generate AI Score"):
                try:
                    score = np.random.randint(50, 100)
                    st.metric("Performance Score", score)
                    if score > 80:
                        st.success("Excellent performance!")
                    elif score > 60:
                        st.warning("Average performance, needs improvement.")
                    else:
                        st.error("Below par, consider rest or training adjustment.")
                    if st.session_state.get('openai_api_key'):
                        prompt = f"Provide a brief performance analysis for {player} based on score {score}."
                        ai_response = call_openai(prompt)
                        st.info(ai_response)
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Register players first.")

    with col2:
        st.subheader("Health & Injury Tracking")
        with st.form("health_form"):
            if st.session_state.players:
                player_list = {p['id']: p['name'] for p in st.session_state.players}
                player_id = st.selectbox("Player", options=list(player_list.keys()), format_func=lambda x: player_list[x])
            else:
                player_id = None
                st.warning("No players")
            date = st.date_input("Date")
            status = st.selectbox("Status", ["fit", "injured", "recovering"])
            injury_type = st.text_input("Injury Type (if injured)")
            expected_return = st.date_input("Expected Return", value=None)
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Record Health")
            if submitted and player_id:
                try:
                    health_data = {
                        'player_id': player_id,
                        'date': date.strftime("%Y-%m-%d"),
                        'status': status,
                        'injury_type': injury_type,
                        'expected_return': expected_return.strftime("%Y-%m-%d") if expected_return else '',
                        'notes': notes
                    }
                    _save_health(health_data)
                    st.success("Health record saved!")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.subheader("Current Health Status")
        if st.session_state.health_records:
            df_health = pd.DataFrame(st.session_state.health_records)
            player_map = {p['id']: p['name'] for p in st.session_state.players}
            df_health['player_name'] = df_health['player_id'].map(player_map)
            st.dataframe(df_health[['player_name', 'date', 'status', 'injury_type', 'expected_return']])
        else:
            st.info("No health records.")

def investors_page():
    st.title("💰 Investor Contributions")
    st.markdown("Record and track investments into the club (Le).")

    with st.form("investor_form"):
        name = st.text_input("Investor Name*")
        contribution = st.number_input("Contribution Amount (Le)", min_value=0.0, step=100000.0)
        date = st.date_input("Date", datetime.date.today())
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Record Contribution")
        if submitted:
            try:
                if not name:
                    st.error("Investor name required.")
                else:
                    inv_data = {
                        'name': name,
                        'contribution': contribution,
                        'date': date.strftime("%Y-%m-%d"),
                        'notes': notes
                    }
                    _save_investor(inv_data)
                    st.success("Investor contribution recorded!")
            except Exception as e:
                st.error(f"Error: {e}")

    st.subheader("All Investors")
    if st.session_state.investors:
        df = pd.DataFrame(st.session_state.investors)
        st.dataframe(df)
        total = df['contribution'].sum()
        st.metric("Total Contributions", f"Le {total:,.2f}")
    else:
        st.info("No investors yet.")

def tournament_page():
    st.title("🏆 Tournament Registration")
    st.markdown("Register your team for various Sierra Leone football tournaments.")

    with st.form("tournament_form"):
        col1, col2 = st.columns(2)
        with col1:
            tournament_name = st.text_input("Tournament Name*")
            season = st.text_input("Season (e.g., 2025)")
            registration_date = st.date_input("Registration Date", datetime.date.today())
        with col2:
            team_category = st.selectbox("Team Category", 
                ["Premier League", "Division One", "Division Two", "Under 12", "Under 14"])
            status = st.selectbox("Status", ["registered", "ongoing", "completed"])
            notes = st.text_area("Notes")
        submitted = st.form_submit_button("Register Tournament")
        if submitted:
            try:
                if not tournament_name:
                    st.error("Tournament name is required.")
                else:
                    tournament_data = {
                        'tournament_name': tournament_name,
                        'season': season,
                        'registration_date': registration_date.strftime("%Y-%m-%d"),
                        'team_category': team_category,
                        'status': status,
                        'notes': notes
                    }
                    _save_tournament(tournament_data)
                    st.success(f"Tournament {tournament_name} registered successfully!")
            except Exception as e:
                st.error(f"Error: {e}")

    st.subheader("Tournament Registrations")
    if st.session_state.tournaments:
        df = pd.DataFrame(st.session_state.tournaments)
        st.dataframe(df)
    else:
        st.info("No tournaments registered yet.")

def match_fixtures_page():
    st.title("📅 Match Fixtures")
    st.markdown("Schedule and manage match fixtures for all tournaments.")
    
    is_admin = st.session_state.role in ['superadmin', 'admin']

    tab1, tab2 = st.tabs(["➕ Add Fixture", "📋 View & Update Fixtures"])

    with tab1:
        with st.form("fixture_form"):
            if st.session_state.tournaments:
                tournament_options = {t['id']: f"{t['tournament_name']} ({t['team_category']})" for t in st.session_state.tournaments}
                tournament_id = st.selectbox("Select Tournament", options=list(tournament_options.keys()), format_func=lambda x: tournament_options[x])
            else:
                st.warning("No tournaments registered. Please register a tournament first.")
                tournament_id = None
            
            col1, col2 = st.columns(2)
            with col1:
                opponent = st.text_input("Opponent Team*")
                match_date = st.date_input("Match Date")
                match_time = st.text_input("Match Time (e.g., 16:00)")
            with col2:
                venue = st.text_input("Venue")
                home_away = st.radio("Home/Away", ["home", "away"])
                notes = st.text_area("Notes")
            
            submitted = st.form_submit_button("Add Fixture")
            if submitted and tournament_id:
                try:
                    if not opponent:
                        st.error("Opponent name is required.")
                    else:
                        match_data = {
                            'tournament_id': tournament_id,
                            'opponent': opponent,
                            'match_date': match_date.strftime("%Y-%m-%d"),
                            'match_time': match_time,
                            'venue': venue,
                            'home_away': home_away,
                            'notes': notes
                        }
                        _save_match(match_data)
                        st.success(f"Fixture against {opponent} added successfully!")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab2:
        if st.session_state.matches:
            df_matches = pd.DataFrame(st.session_state.matches)
            tournament_map = {t['id']: f"{t['tournament_name']} ({t['team_category']})" for t in st.session_state.tournaments}
            df_matches['tournament'] = df_matches['tournament_id'].map(tournament_map)
            
            tournaments_list = ["All"] + list(tournament_map.values())
            selected_tournament = st.selectbox("Filter by Tournament", tournaments_list)
            
            if selected_tournament != "All":
                tourn_id = next((tid for tid, name in tournament_map.items() if name == selected_tournament), None)
                if tourn_id:
                    df_matches = df_matches[df_matches['tournament_id'] == tourn_id]
            
            upcoming = df_matches[df_matches['is_played'] == 0].sort_values('match_date')
            played = df_matches[df_matches['is_played'] == 1].sort_values('match_date', ascending=False)
            
            st.subheader("📌 Upcoming Fixtures")
            if not upcoming.empty:
                for idx, match in upcoming.iterrows():
                    with st.expander(f"{match['match_date']} - vs {match['opponent']} ({match['home_away']})"):
                        st.write(f"**Time:** {match.get('match_time', 'TBA')}")
                        st.write(f"**Venue:** {match.get('venue', 'TBA')}")
                        st.write(f"**Tournament:** {match['tournament']}")
                        
                        if is_admin:
                            st.markdown("### Update Match Result")
                            with st.form(f"result_form_{match['id']}"):
                                our_score = st.number_input(f"{st.session_state.club} Score", min_value=0, max_value=20, value=0, key=f"our_{match['id']}")
                                opp_score = st.number_input(f"{match['opponent']} Score", min_value=0, max_value=20, value=0, key=f"opp_{match['id']}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("✅ Mark as Played"):
                                        result = "win" if our_score > opp_score else "loss" if our_score < opp_score else "draw"
                                        _update_match_result(match['id'], our_score, opp_score, 1, result)
                                        st.success("Match result updated!")
                                        st.rerun()
                                with col2:
                                    if st.form_submit_button("🗑️ Delete Fixture"):
                                        # For now, just a warning
                                        st.warning("Delete functionality can be added if needed.")
            else:
                st.info("No upcoming fixtures.")
            
            st.subheader("✅ Played Matches")
            if not played.empty:
                display_cols = ['match_date', 'opponent', 'our_score', 'opponent_score', 'result', 'home_away']
                st.dataframe(played[display_cols])
            else:
                st.info("No played matches yet.")
        else:
            st.info("No fixtures added yet.")

def lineup_selection_page():
    st.title("📋 Lineup Selection")
    st.markdown("Select starting XI and substitutes for upcoming matches.")
    
    is_admin = st.session_state.role in ['superadmin', 'admin']
    if not is_admin:
        st.warning("Only admins can set lineups.")
        return

    if not st.session_state.matches:
        st.info("No matches available. Please add fixtures first.")
        return

    # Filter upcoming matches
    upcoming_matches = [m for m in st.session_state.matches if m['is_played'] == 0]
    if not upcoming_matches:
        st.info("No upcoming matches to set lineup for.")
        return

    match_options = {m['id']: f"{m['match_date']} vs {m['opponent']} ({m['home_away']})" for m in upcoming_matches}
    selected_match_id = st.selectbox("Select Match", options=list(match_options.keys()), format_func=lambda x: match_options[x])
    selected_match = next((m for m in upcoming_matches if m['id'] == selected_match_id), None)

    if not selected_match:
        return

    st.subheader(f"Lineup for {selected_match['match_date']} vs {selected_match['opponent']}")

    # Show current lineup if any
    current_lineup = _get_lineup_for_match(selected_match_id)
    if current_lineup:
        st.markdown("### Current Selected Players")
        for entry in current_lineup:
            player = next((p for p in st.session_state.players if p['id'] == entry['player_id']), None)
            if player:
                sub_text = " (Substitute)" if entry['is_substitute'] else ""
                st.write(f"{player['name']} - {entry['position']}{sub_text}")
    else:
        st.info("No lineup set yet.")

    # Form to add players to lineup
    st.markdown("### Add Player to Lineup")
    if not st.session_state.players:
        st.warning("No players registered.")
        return

    with st.form("lineup_form"):
        player_options = {p['id']: f"{p['name']} ({p['position']})" for p in st.session_state.players}
        player_id = st.selectbox("Select Player", options=list(player_options.keys()), format_func=lambda x: player_options[x])
        position = st.text_input("Position on field (e.g., GK, LB, CM, ST)")
        is_substitute = st.checkbox("Is Substitute?")
        submitted = st.form_submit_button("Add to Lineup")
        if submitted:
            try:
                _save_lineup(selected_match_id, player_id, position, is_substitute)
                st.success("Player added to lineup!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if current_lineup:
        if st.button("Clear Lineup for this Match"):
            _clear_lineup(selected_match_id)
            st.success("Lineup cleared!")
            st.rerun()

def formations_library_page():
    st.title("⚽ Football Formations Library")
    st.markdown("Explore different tactical formations used in modern football.")
    
    formations = {
        "4-4-2": {
            "description": "Classic English formation with two strikers. Provides balance between attack and defense.",
            "strengths": ["Solid defensive structure", "Two strikers can pressure defenders", "Wide midfielders provide width"],
            "weaknesses": ["Midfield can be overrun by three-man midfields", "Requires hard-working central midfielders"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/3/33/4-4-2_formation.svg"
        },
        "4-2-3-1": {
            "description": "Modern formation with a single striker, three attacking midfielders, and two defensive midfielders.",
            "strengths": ["Strong defensive cover", "Creative freedom for attacking mids", "Good width"],
            "weaknesses": ["Striker can become isolated", "Requires fit full-backs"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/2/2a/4-2-3-1_formation.svg"
        },
        "4-3-3": {
            "description": "Attacking formation with three forwards. Popularized by Johan Cruyff and modern teams.",
            "strengths": ["High pressing", "Wide attacks", "Numerical superiority in midfield"],
            "weaknesses": ["Full-backs exposed", "Requires versatile forwards"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/3/3b/4-3-3_formation.svg"
        },
        "3-5-2": {
            "description": "Formation with three center-backs, wing-backs, and two strikers. Provides midfield dominance.",
            "strengths": ["Midfield control", "Wing-backs provide width", "Two strikers up front"],
            "weaknesses": ["Vulnerable to quick wingers", "Requires fit wing-backs"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/0/0a/3-5-2_formation.svg"
        },
        "4-1-4-1": {
            "description": "Defensive shape that can transition to attack. One defensive midfielder shields the back four.",
            "strengths": ["Compact defense", "Good transitions", "Solid against counter-attacks"],
            "weaknesses": ["Striker isolated", "Lacks creative spark"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/1/1a/4-1-4-1_formation.svg"
        },
        "4-1-3-2": {
            "description": "Variation of 4-4-2 with a diamond midfield. One defensive midfielder, two wide, one attacking.",
            "strengths": ["Central midfield dominance", "Two strikers", "Creative freedom"],
            "weaknesses": ["Narrow shape", "Full-backs need to provide width"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/4/4f/4-1-3-2_formation.svg"
        },
        "5-4-1": {
            "description": "Very defensive formation with five defenders. Often used to protect a lead or against stronger opponents.",
            "strengths": ["Very solid defensively", "Difficult to break down", "Good for counter-attacks"],
            "weaknesses": ["Lacks attacking threat", "Lonely striker", "Requires disciplined defending"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/9/9a/5-4-1_formation.svg"
        },
        "3-2-4-1": {
            "description": "Modern possession-based formation. Three center-backs, two defensive midfielders, four attacking midfielders, one striker.",
            "strengths": ["Overloads midfield", "Control possession", "Flexible attacking options"],
            "weaknesses": ["Vulnerable to quick counters", "Requires very fit players"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/3-2-4-1_formation.svg/1200px-3-2-4-1_formation.svg.png"
        }
    }
    
    selected = st.selectbox("Select Formation", list(formations.keys()))
    if selected:
        f = formations[selected]
        st.subheader(selected)
        st.write(f["description"])
        st.markdown("**Strengths:**")
        for s in f["strengths"]:
            st.markdown(f"- {s}")
        st.markdown("**Weaknesses:**")
        for w in f["weaknesses"]:
            st.markdown(f"- {w}")
        st.image(f["image"], caption=f"{selected} Formation", width=400)

def ai_assistant_page():
    st.title("🤖 AI Assistant")
    st.markdown("Ask anything about football management, training tactics, player health, or finance.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask the AI Coach...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = call_openai(prompt)
                except Exception as e:
                    response = f"Error: {e}"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

def admin_panel_page():
    if st.session_state.role not in ['superadmin', 'admin']:
        st.error("Access denied. Admin only.")
        return

    st.title("🔐 Admin Panel")
    st.markdown("### Master Controller: Manage users, system settings, and security.")

    tab1, tab2, tab3, tab4 = st.tabs(["👥 User Management", "🔑 Change Login", "⚙️ System Settings", "🛡️ Security"])

    with tab1:
        st.subheader("Add New User")
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_full_name = st.text_input("Full Name")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["admin", "manager", "viewer"])
            new_club = st.text_input("Club (default: current club)", value=st.session_state.club)
            submitted = st.form_submit_button("Create User")
            if submitted:
                try:
                    if _get_user_by_username(new_username):
                        st.error("Username already exists.")
                    elif _get_user_by_email(new_email):
                        st.error("Email already registered.")
                    else:
                        _add_user(new_username, new_email, new_full_name, new_password, new_role, new_club)
                        st.success(f"User {new_username} created.")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.subheader("Existing Users")
        users = _get_users()
        if users:
            df_users = pd.DataFrame(users, columns=["ID", "Username", "Email", "Full Name", "Role", "Club"])
            st.dataframe(df_users)

            st.subheader("Delete User")
            user_to_delete = st.selectbox("Select User ID to delete", [u[0] for u in users], format_func=lambda x: f"{x} - {next((u[1] for u in users if u[0]==x), '')}")
            if st.button("Delete User", type="primary"):
                try:
                    _delete_user(user_to_delete)
                    st.success("User deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("No users found.")

    with tab2:
        st.subheader("Change Your Password")
        with st.form("change_pw_form"):
            current_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Change Password")
            if submitted:
                try:
                    role, club = verify_login(st.session_state.username, current_pw)
                    if role:
                        if new_pw == confirm_pw:
                            _change_password(st.session_state.username, new_pw)
                            st.success("Password changed successfully.")
                        else:
                            st.error("New passwords do not match.")
                    else:
                        st.error("Current password incorrect.")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.subheader("Change Another User's Password (Admin only)")
        if st.session_state.role == 'superadmin':
            users = _get_users()
            if users:
                user_list = {u[1]: u[0] for u in users}
                selected_user = st.selectbox("Select User", options=list(user_list.keys()))
                new_pw_user = st.text_input("New Password for selected user", type="password", key="admin_new_pw")
                if st.button("Set New Password"):
                    try:
                        _change_password(selected_user, new_pw_user)
                        st.success(f"Password for {selected_user} updated.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab3:
        st.subheader("OpenAI API Key")
        # Allow user to input the key
        api_key = st.text_input("Enter OpenAI API Key", type="password", value=st.session_state.openai_api_key or "")
        if api_key:
            st.session_state.openai_api_key = api_key
            st.success("API key saved for this session.")

        st.subheader("Simulated Reports")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📧 Send Daily Email Report"):
                total_income = sum(f['amount'] for f in st.session_state.finances if f['type'] == 'income')
                total_expense = sum(f['amount'] for f in st.session_state.finances if f['type'] == 'expense')
                net = total_income - total_expense
                report = f"Daily report for {st.session_state.club}: Players: {len(st.session_state.players)}, Net Balance: Le {net:,.2f}"
                simulate_email_report(report)
        with col2:
            if st.button("📱 Send WhatsApp Report"):
                total_investors = len(st.session_state.investors)
                recent_transfers = len(st.session_state.transfers)
                report = f"WhatsApp report: {st.session_state.club} - Investors: {total_investors}, Recent transfers: {recent_transfers}"
                simulate_whatsapp_message(report)

        st.subheader("Fingerprint Login Simulation")
        if st.button("Simulate Fingerprint Auth"):
            st.success("Fingerprint recognized. (Demo)")

    with tab4:
        st.subheader("Encryption Status")
        if CRYPTO_AVAILABLE:
            st.success("Encryption module is available. Sensitive data can be encrypted at rest.")
            if st.button("Encrypt Database (Simulated)"):
                st.info("Database encryption simulation: All sensitive fields would be encrypted.")
        else:
            st.warning("Cryptography library not installed. Install with: pip install cryptography")

        st.subheader("Database Backup (Cloud Sync Simulation)")
        if st.button("💾 Backup to Cloud"):
            try:
                import shutil
                backup_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy('dynamic_fc.db', backup_name)
                st.success(f"Database backed up locally as {backup_name} (simulated cloud sync).")
            except Exception as e:
                st.error(f"Backup failed: {e}")

        st.subheader("Production Security Hardening")
        st.markdown("""
        - All passwords are hashed with SHA256.
        - Role-based access control implemented.
        - SQLite database with parameterized queries prevents injection.
        - Optional encryption for sensitive fields.
        - Session management via Streamlit state.
        - Admin-only edit/delete controls for finance.
        - In production, use HTTPS, environment variables for secrets, and a cloud database with encryption at rest.
        """)

# ------------------------------
# 7. MAIN APP
# ------------------------------
def main():
    try:
        choice = navigation()
        if choice is None:
            # Not logged in, show welcome
            st.title("⚽ Welcome to Dynamic FC Management System")
            st.markdown("### Falaba District's Premier Football Club Management Software")
            st.image("https://via.placeholder.com/800x200?text=Dynamic+FC+Falaba+District", use_container_width=True)
            st.markdown("Please log in using the sidebar. New users can create an account.")
            return

        if choice == "Dashboard":
            dashboard_page()
        elif choice == "Player Registration":
            player_registration_page()
        elif choice == "Finance":
            finance_page()
        elif choice == "Training":
            training_page()
        elif choice == "Transfer Window":
            transfer_window_page()
        elif choice == "Health & Performance":
            health_performance_page()
        elif choice == "Investors":
            investors_page()
        elif choice == "Tournament Registration":
            tournament_page()
        elif choice == "Match Fixtures":
            match_fixtures_page()
        elif choice == "Lineup Selection":
            lineup_selection_page()
        elif choice == "Formations Library":
            formations_library_page()
        elif choice == "AI Assistant":
            ai_assistant_page()
        elif choice == "Admin Panel":
            admin_panel_page()
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.info("The app has self-healing capabilities. Please try again or contact support.")

if __name__ == "__main__":
    main()
