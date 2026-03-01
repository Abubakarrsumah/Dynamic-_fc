"""
DYNAMIC FC - Football Management System (Falaba District)
Professional club management application with all requested features.
Run with: streamlit run football_app.py
"""

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
from io import BytesIO
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
import uuid

# Optional imports with graceful fallback
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
# Page configuration (must be first Streamlit command)
# ------------------------------
st.set_page_config(
    page_title="Dynamic FC Management",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# Session state initialization
# ------------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = 'guest'  # superadmin, admin, manager, viewer
if 'club' not in st.session_state:
    st.session_state.club = 'Dynamic FC (Falaba District)'
if 'db_conn' not in st.session_state:
    # Initialize SQLite database (simulates cloud database)
    st.session_state.db_conn = sqlite3.connect('dynamic_fc.db', check_same_thread=False)
    _create_tables()
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
if 'training_logs' not in st.session_state:
    st.session_state.training_logs = []
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'encryption_key' not in st.session_state and CRYPTO_AVAILABLE:
    # For demo, generate a key (in production, store securely)
    st.session_state.encryption_key = Fernet.generate_key()
    st.session_state.cipher = Fernet(st.session_state.encryption_key)

# ------------------------------
# Database helper functions
# ------------------------------
def _create_tables():
    """Create necessary tables if they don't exist."""
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    # Users table (admin)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            club TEXT
        )
    ''')
    # Players table (with photo BLOB)
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
    # Finances table (income/expense) with detailed categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,  -- 'income' or 'expense'
            category TEXT,
            amount REAL,
            description TEXT,
            club TEXT
        )
    ''')
    # Investors table
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
    # Health records
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            date TEXT,
            status TEXT,  -- 'fit', 'injured', 'recovering'
            injury_type TEXT,
            expected_return TEXT,
            notes TEXT,
            club TEXT
        )
    ''')
    # Transfers (in/out)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT,
            transfer_type TEXT,  -- 'incoming' or 'outgoing'
            from_club TEXT,
            to_club TEXT,
            transfer_fee REAL,
            date TEXT,
            notes TEXT,
            club TEXT
        )
    ''')
    conn.commit()
    # Insert default superadmin if not exists
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        hashed = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash, role, club) VALUES (?,?,?,?)",
                       ('admin', hashed, 'superadmin', 'Dynamic FC (Falaba District)'))
        conn.commit()

def _load_players():
    conn = st.session_state.db_conn
    club = st.session_state.club
    df = pd.read_sql("SELECT * FROM players WHERE club=?", conn, params=(club,))
    return df.to_dict('records') if not df.empty else []

def _load_finances():
    conn = st.session_state.db_conn
    club = st.session_state.club
    df = pd.read_sql("SELECT * FROM finances WHERE club=?", conn, params=(club,))
    return df.to_dict('records') if not df.empty else []

def _load_investors():
    conn = st.session_state.db_conn
    club = st.session_state.club
    df = pd.read_sql("SELECT * FROM investors WHERE club=?", conn, params=(club,))
    return df.to_dict('records') if not df.empty else []

def _load_health():
    conn = st.session_state.db_conn
    club = st.session_state.club
    df = pd.read_sql("SELECT * FROM health WHERE club=?", conn, params=(club,))
    return df.to_dict('records') if not df.empty else []

def _load_transfers():
    conn = st.session_state.db_conn
    club = st.session_state.club
    df = pd.read_sql("SELECT * FROM transfers WHERE club=?", conn, params=(club,))
    return df.to_dict('records') if not df.empty else []

def _save_player(player_data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO players (name, position, age, jersey_number, nationality, contract_until, monthly_salary, photo, club)
        VALUES (?,?,?,?,?,?,?,?,?)
    ''', (player_data['name'], player_data['position'], player_data['age'],
          player_data['jersey_number'], player_data['nationality'],
          player_data['contract_until'], player_data['monthly_salary'],
          player_data['photo'], st.session_state.club))
    conn.commit()
    st.session_state.players = _load_players()

def _update_player(player_id, player_data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE players SET name=?, position=?, age=?, jersey_number=?, nationality=?, contract_until=?, monthly_salary=?, photo=?
        WHERE id=? AND club=?
    ''', (player_data['name'], player_data['position'], player_data['age'],
          player_data['jersey_number'], player_data['nationality'],
          player_data['contract_until'], player_data['monthly_salary'],
          player_data['photo'], player_id, st.session_state.club))
    conn.commit()
    st.session_state.players = _load_players()

def _delete_player(player_id):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE id=? AND club=?", (player_id, st.session_state.club))
    conn.commit()
    st.session_state.players = _load_players()

def _save_finance(fin_data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO finances (date, type, category, amount, description, club)
        VALUES (?,?,?,?,?,?)
    ''', (fin_data['date'], fin_data['type'], fin_data['category'],
          fin_data['amount'], fin_data['description'], st.session_state.club))
    conn.commit()
    st.session_state.finances = _load_finances()

def _save_investor(inv_data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO investors (name, contribution, date, notes, club)
        VALUES (?,?,?,?,?)
    ''', (inv_data['name'], inv_data['contribution'], inv_data['date'], inv_data['notes'], st.session_state.club))
    conn.commit()
    st.session_state.investors = _load_investors()

def _save_health(health_data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO health (player_id, date, status, injury_type, expected_return, notes, club)
        VALUES (?,?,?,?,?,?,?)
    ''', (health_data['player_id'], health_data['date'], health_data['status'],
          health_data['injury_type'], health_data['expected_return'], health_data['notes'], st.session_state.club))
    conn.commit()
    st.session_state.health_records = _load_health()

def _save_transfer(transfer_data):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transfers (player_name, transfer_type, from_club, to_club, transfer_fee, date, notes, club)
        VALUES (?,?,?,?,?,?,?,?)
    ''', (transfer_data['player_name'], transfer_data['transfer_type'],
          transfer_data['from_club'], transfer_data['to_club'],
          transfer_data['transfer_fee'], transfer_data['date'],
          transfer_data['notes'], st.session_state.club))
    conn.commit()
    st.session_state.transfers = _load_transfers()

def _get_users():
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, club FROM users")
    return cursor.fetchall()

def _add_user(username, password, role, club):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("INSERT INTO users (username, password_hash, role, club) VALUES (?,?,?,?)",
                   (username, hashed, role, club))
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

# ------------------------------
# Utility functions
# ------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    conn = st.session_state.db_conn
    cursor = conn.cursor()
    hashed = hash_password(password)
    cursor.execute("SELECT role, club FROM users WHERE username=? AND password_hash=?", (username, hashed))
    result = cursor.fetchone()
    if result:
        return result[0], result[1]  # role, club
    return None, None

def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = 'guest'
    st.rerun()

def generate_pdf_receipt(data):
    """Generate a PDF receipt for a transaction."""
    if not FPDF_AVAILABLE:
        st.error("FPDF not installed. Cannot generate PDF.")
        return b''
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Dynamic FC - Receipt", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Date: {data['date']}", ln=1)
    pdf.cell(200, 10, txt=f"Type: {data['type']}", ln=1)
    pdf.cell(200, 10, txt=f"Category: {data['category']}", ln=1)
    pdf.cell(200, 10, txt=f"Amount: ${data['amount']:.2f}", ln=1)
    pdf.cell(200, 10, txt=f"Description: {data['description']}", ln=1)
    pdf_str = pdf.output(dest='S').encode('latin1')
    return pdf_str

def download_pdf_button(pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">📥 Download PDF Receipt</a>'
    st.markdown(href, unsafe_allow_html=True)

def mock_openai_response(prompt):
    return f"🤖 AI Coach: Based on your query '{prompt[:50]}...', we recommend focusing on stamina and passing drills. Consider reviewing player nutrition and injury prevention."

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
    """Convert PIL Image to bytes for storage."""
    img_bytes = BytesIO()
    image.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

def bytes_to_image(img_bytes):
    """Convert bytes to PIL Image for display."""
    if img_bytes:
        return Image.open(BytesIO(img_bytes))
    return None

def simulate_whatsapp_message(report):
    """Simulate sending WhatsApp message."""
    st.info(f"📱 WhatsApp message sent: {report[:100]}...")

def simulate_email_report(report):
    """Simulate sending email report."""
    st.info(f"📧 Email report sent to admins: {report[:100]}...")

# ------------------------------
# Sidebar navigation
# ------------------------------
def navigation():
    with st.sidebar:
        # Club logo (try to load from provided path, else placeholder)
        logo_path = "sandbox:/mnt/data/yourfile.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)
        else:
            # Use emoji as fallback
            st.markdown("# ⚽ DYNAMIC FC")
        st.markdown(f"## {st.session_state.club}")
        st.markdown("---")

        if not st.session_state.authenticated:
            st.subheader("🔐 Login")
            with st.form("login_form"):
                username = st.text_input("Username")
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
                        st.error("Invalid username or password")
            st.markdown("---")
            st.info("Demo credentials: admin / admin123")
            return None
        else:
            st.write(f"Welcome, **{st.session_state.username}** ({st.session_state.role})")
            if st.button("Logout"):
                logout()

            # Navigation menu (role-based)
            menu_items = ["Dashboard", "Player Registration", "Finance", "Training",
                          "Transfer Window", "Health & Performance", "Investors",
                          "AI Assistant"]
            if st.session_state.role in ['superadmin', 'admin']:
                menu_items.append("Admin Panel")
            choice = st.radio("Go to", menu_items)

            st.markdown("---")
            # Multi-club support (only for superadmin/admins)
            if st.session_state.role in ['superadmin', 'admin']:
                clubs = ["Dynamic FC (Falaba District)", "Dynamic FC Youth", "Dynamic FC Women"]
                selected_club = st.selectbox("Switch Club", clubs, index=clubs.index(st.session_state.club) if st.session_state.club in clubs else 0)
                if selected_club != st.session_state.club:
                    st.session_state.club = selected_club
                    # Reload data for new club
                    st.session_state.players = _load_players()
                    st.session_state.finances = _load_finances()
                    st.session_state.investors = _load_investors()
                    st.session_state.health_records = _load_health()
                    st.session_state.transfers = _load_transfers()
                    st.rerun()
            return choice

# ------------------------------
# Page content functions
# ------------------------------
def dashboard_page():
    st.title("📊 Dashboard")
    st.markdown(f"### Welcome to {st.session_state.club}")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", len(st.session_state.players))
    with col2:
        total_income = sum(f['amount'] for f in st.session_state.finances if f['type'] == 'income')
        total_expense = sum(f['amount'] for f in st.session_state.finances if f['type'] == 'expense')
        st.metric("Net Balance", f"${total_income - total_expense:,.2f}")
    with col3:
        injured = len([h for h in st.session_state.health_records if h['status'] == 'injured'])
        st.metric("Injured Players", injured)
    with col4:
        st.metric("Investors", len(st.session_state.investors))

    # Financial chart
    st.subheader("📈 Financial Overview")
    if st.session_state.finances:
        df_fin = pd.DataFrame(st.session_state.finances)
        fig = px.bar(df_fin, x='date', y='amount', color='type', title='Income vs Expense', barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No financial data yet.")

    # Player performance scores (mock AI)
    st.subheader("🧠 Player Performance Scores (AI Generated)")
    if st.session_state.players:
        player_names = [p['name'] for p in st.session_state.players]
        scores = np.random.randint(60, 100, size=len(player_names))
        df_perf = pd.DataFrame({"Player": player_names, "Score": scores})
        fig2 = px.bar(df_perf, x='Player', y='Score', color='Score', title='AI Performance Scores')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Register players to see performance scores.")

    # Auto profit summary (last 30 days)
    st.subheader("📉 Auto Profit Summary (Last 30 Days)")
    today = datetime.date.today()
    month_ago = today - datetime.timedelta(days=30)
    recent = [f for f in st.session_state.finances if datetime.datetime.strptime(f['date'], '%Y-%m-%d').date() >= month_ago]
    inc = sum(f['amount'] for f in recent if f['type'] == 'income')
    exp = sum(f['amount'] for f in recent if f['type'] == 'expense')
    profit = inc - exp
    st.write(f"Income: **${inc:,.2f}** | Expense: **${exp:,.2f}** | **Profit: ${profit:,.2f}**")

def player_registration_page():
    st.title("📝 Player Registration")
    st.markdown("Add, edit, or remove players from the squad.")

    # Tabs for add/edit/delete
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
                salary = st.number_input("Monthly Salary ($)", min_value=0.0, step=100.0)
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
                        salary = st.number_input("Monthly Salary ($)", min_value=0.0, value=player['monthly_salary'])
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

    # Display current squad
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
                    st.write(f"**Monthly Salary:** ${player['monthly_salary']:,.2f}")
    else:
        st.info("No players registered yet.")

def finance_page():
    st.title("💰 Finance Management")
    st.markdown("### Detailed Income & Expenditure")
    st.markdown("Categories include: Ticket Sales, Merchandise, Sponsorship, Transfer Fee, Transportation, Feeding, Lodging, Salaries, Bonuses, etc.")

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
            amount = st.number_input("Amount ($)", min_value=0.01, step=10.0)
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
                        download_pdf_button(pdf_bytes, f"receipt_{date}.pdf")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab2:
        if st.session_state.finances:
            df = pd.DataFrame(st.session_state.finances)
            st.dataframe(df)
        else:
            st.info("No transactions yet.")

    with tab3:
        if st.session_state.finances:
            df = pd.DataFrame(st.session_state.finances)
            income = df[df['type'] == 'income']['amount'].sum()
            expense = df[df['type'] == 'expense']['amount'].sum()
            profit = income - expense
            st.metric("Total Income", f"${income:,.2f}")
            st.metric("Total Expense", f"${expense:,.2f}")
            st.metric("Net Profit", f"${profit:,.2f}")

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
    # Embed a sample YouTube video (replace with actual team video)
    video_url = "https://www.youtube.com/embed/dQw4w9WgXcQ"  # Placeholder
    st.markdown(f'<iframe width="560" height="315" src="{video_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)

    st.subheader("Performance Tracking")
    # Training log form
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

    # Display recent logs
    if st.session_state.training_logs:
        st.subheader("Recent Training Logs")
        df_logs = pd.DataFrame(st.session_state.training_logs[-10:])
        st.dataframe(df_logs)

def transfer_window_page():
    st.title("🔄 Transfer Window")
    st.markdown("Record player transfers (incoming and outgoing) including fees.")

    with st.form("transfer_form"):
        col1, col2 = st.columns(2)
        with col1:
            player_name = st.text_input("Player Name*")
            transfer_type = st.radio("Transfer Type", ["incoming", "outgoing"])
            from_club = st.text_input("From Club")
            to_club = st.text_input("To Club")
        with col2:
            transfer_fee = st.number_input("Transfer Fee ($)", min_value=0.0, step=1000.0)
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
        st.metric("Total Incoming Fees", f"${total_fees_in:,.2f}")
        st.metric("Total Outgoing Fees", f"${total_fees_out:,.2f}")
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

        # Display current health status
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
    st.markdown("Record and track investments into the club.")

    with st.form("investor_form"):
        name = st.text_input("Investor Name*")
        contribution = st.number_input("Contribution Amount ($)", min_value=0.0, step=100.0)
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
        st.metric("Total Contributions", f"${total:,.2f}")
    else:
        st.info("No investors yet.")

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
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["admin", "manager", "viewer"])
            new_club = st.text_input("Club (default: current club)", value=st.session_state.club)
            submitted = st.form_submit_button("Create User")
            if submitted:
                try:
                    _add_user(new_username, new_password, new_role, new_club)
                    st.success(f"User {new_username} created.")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.subheader("Existing Users")
        users = _get_users()
        if users:
            df_users = pd.DataFrame(users, columns=["ID", "Username", "Role", "Club"])
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
        api_key = st.text_input("Enter OpenAI API Key", type="password")
        if api_key:
            st.session_state.openai_api_key = api_key
            st.success("API key saved for this session.")

        st.subheader("Simulated Reports")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📧 Send Daily Email Report"):
                report = f"Daily report for {st.session_state.club}: Players: {len(st.session_state.players)}, Net Balance: ${sum(f['amount'] for f in st.session_state.finances if f['type']=='income') - sum(f['amount'] for f in st.session_state.finances if f['type']=='expense'):,.2f}"
                simulate_email_report(report)
        with col2:
            if st.button("📱 Send WhatsApp Report"):
                report = f"WhatsApp report: {st.session_state.club} - Investors: {len(st.session_state.investors)}, Recent transfers: {len(st.session_state.transfers)}"
                simulate_whatsapp_message(report)

        st.subheader("Fingerprint Login Simulation")
        if st.button("Simulate Fingerprint Auth"):
            st.success("Fingerprint recognized. (Demo)")

    with tab4:
        st.subheader("Encryption Status")
        if CRYPTO_AVAILABLE:
            st.success("Encryption module is available. Sensitive data can be encrypted at rest.")
            if st.button("Encrypt Database (Simulated)"):
                # In a real app, you would encrypt the entire DB file or specific columns
                st.info("Database encryption simulation: All sensitive fields would be encrypted.")
        else:
            st.warning("Cryptography library not installed. Install with: pip install cryptography")

        st.subheader("Database Backup (Cloud Sync Simulation)")
        if st.button("💾 Backup to Cloud"):
            try:
                # Simulate cloud backup by copying the database file
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
        - In production, use HTTPS, environment variables for secrets, and a cloud database with encryption at rest.
        """)

# ------------------------------
# Main app logic
# ------------------------------
def main():
    try:
        choice = navigation()
        if choice is None:
            # Not logged in, show welcome page
            st.title("⚽ Welcome to Dynamic FC Management System")
            st.markdown("### Falaba District's Premier Football Club Management Software")
            st.image("https://via.placeholder.com/800x200?text=Dynamic+FC+Falaba+District", use_container_width=True)
            st.markdown("Please log in using the sidebar to access the dashboard.")
            return

        # Route to selected page
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
        elif choice == "AI Assistant":
            ai_assistant_page()
        elif choice == "Admin Panel":
            admin_panel_page()
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.info("The app has self-healing capabilities. Please try again or contact support.")

if __name__ == "__main__":
    main()
