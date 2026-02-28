# ==========================================================
# ⚽ DYNAMIC FC FALABA DISTRICT - ENTERPRISE SaaS v3
# Single File | Hybrid Cloud | Encrypted | AI Integrated
# Run: streamlit run football_app.py
# ==========================================================

import streamlit as st
import os
import hashlib
import sqlite3
import psycopg2
import pandas as pd
import datetime
import plotly.express as px
from cryptography.fernet import Fernet
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.mime.text import MIMEText
import openai

# ==========================================================
# CONFIG
# ==========================================================

TEAM_NAME = "Dynamic FC Falaba District"
st.set_page_config(page_title=TEAM_NAME, layout="wide")

# ==========================================================
# ENCRYPTION (MILITARY GRADE)
# ==========================================================

if not os.path.exists("secret.key"):
    with open("secret.key", "wb") as f:
        f.write(Fernet.generate_key())

key = open("secret.key", "rb").read()
cipher = Fernet(key)

def encrypt(data):
    return cipher.encrypt(data.encode()).decode()

def decrypt(data):
    return cipher.decrypt(data.encode()).decode()

# ==========================================================
# DATABASE HYBRID (Cloud PostgreSQL or Local SQLite)
# ==========================================================

def get_connection():
    if os.getenv("DATABASE_URL"):
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    else:
        return sqlite3.connect("dynamic_fc.db", check_same_thread=False)

conn = get_connection()
cursor = conn.cursor()

# ==========================================================
# SECURITY
# ==========================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================================
# CREATE TABLES
# ==========================================================

def create_tables():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players(
        id SERIAL PRIMARY KEY,
        name TEXT,
        age INTEGER,
        position TEXT,
        health TEXT,
        injury TEXT,
        status TEXT,
        fitness INTEGER,
        score REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS finance(
        id SERIAL PRIMARY KEY,
        type TEXT,
        category TEXT,
        amount REAL,
        description TEXT,
        date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contributions(
        id SERIAL PRIMARY KEY,
        investor TEXT,
        amount REAL,
        date TEXT
    )
    """)
    conn.commit()

create_tables()

# Default Admin
cursor.execute("SELECT * FROM users WHERE username='admin'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO users VALUES (%s,%s,%s)",
                   ("admin", hash_password("admin123"), "Super Admin"))
    conn.commit()

# ==========================================================
# LOGIN
# ==========================================================

def login():
    st.title(f"🔐 {TEAM_NAME} Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s",
                           (u, hash_password(p)))
            user = cursor.fetchone()
            if user:
                st.session_state["role"] = user[2]
                st.session_state["login"] = True
                st.success("Login Successful")
                st.rerun()
            else:
                st.error("Invalid credentials")
        except Exception as e:
            st.error(e)

# ==========================================================
# PERFORMANCE AI
# ==========================================================

def calculate_score(g, a, f):
    return g*4 + a*3 + f*2

# ==========================================================
# PDF GENERATOR
# ==========================================================

def generate_pdf(text):
    doc = SimpleDocTemplate("receipt.pdf")
    styles = getSampleStyleSheet()
    doc.build([Paragraph(text, styles["Normal"])])

# ==========================================================
# EMAIL REPORT
# ==========================================================

def send_email(report_text):
    try:
        msg = MIMEText(report_text)
        msg['Subject'] = "Daily Financial Report"
        msg['From'] = "club@email.com"
        msg['To'] = "admin@email.com"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("your_email", "your_password")
        server.send_message(msg)
        server.quit()
    except:
        pass

# ==========================================================
# WHATSAPP HOOK
# ==========================================================

def send_whatsapp(message):
    # Integrate Meta WhatsApp Business API here
    pass

# ==========================================================
# DASHBOARD
# ==========================================================

def dashboard():

    st.image("logo.png", width=150)
    st.title(f"{TEAM_NAME} Enterprise System")

    menu = st.sidebar.selectbox("Menu",
        ["Dashboard","Players","Finance","Admin","AI Assistant"])

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        df = pd.read_sql("SELECT * FROM finance", conn)

        if not df.empty:
            income = df[df.type=="Income"]["amount"].sum()
            expense = df[df.type=="Expenditure"]["amount"].sum()
            st.metric("Income", income)
            st.metric("Expense", expense)
            st.metric("Profit", income-expense)
            st.plotly_chart(px.pie(df, names="type", values="amount"))

    # ================= PLAYERS =================
    if menu == "Players":
        with st.form("player"):
            name = st.text_input("Name")
            age = st.number_input("Age",10,50)
            position = st.text_input("Position")
            health = st.selectbox("Health",["Fit","Injured"])
            injury = st.text_input("Injury")
            status = st.selectbox("Status",["Active","Suspended"])
            fitness = st.slider("Fitness",1,10)
            g = st.number_input("Goals",0)
            a = st.number_input("Assists",0)

            if st.form_submit_button("Save"):
                score = calculate_score(g,a,fitness)
                cursor.execute("""
                INSERT INTO players(name,age,position,health,injury,status,fitness,score)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                """,(name,age,position,health,injury,status,fitness,score))
                conn.commit()
                st.success("Player Saved")

        st.dataframe(pd.read_sql("SELECT * FROM players",conn))

    # ================= FINANCE =================
    if menu == "Finance":
        with st.form("finance"):
            t = st.selectbox("Type",["Income","Expenditure"])
            cat = st.text_input("Category")
            amt = st.number_input("Amount",0.0)
            desc = st.text_input("Description")
            if st.form_submit_button("Record"):
                cursor.execute("""
                INSERT INTO finance(type,category,amount,description,date)
                VALUES(%s,%s,%s,%s,%s)
                """,(t,cat,amt,desc,str(datetime.date.today())))
                conn.commit()
                generate_pdf(f"{t} {amt}")
                st.success("Recorded")

        st.subheader("Investor Contributions")
        inv = st.text_input("Investor Name")
        amt2 = st.number_input("Contribution",0.0)
        if st.button("Save Contribution"):
            cursor.execute("""
            INSERT INTO contributions(investor,amount,date)
            VALUES(%s,%s,%s)
            """,(inv,amt2,str(datetime.date.today())))
            conn.commit()
            st.success("Saved")

    # ================= ADMIN MASTER =================
    if menu == "Admin" and st.session_state["role"]=="Super Admin":
        st.subheader("Admin Master Controller")

        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password")
        role = st.selectbox("Role",["Super Admin","Finance","Coach"])

        if st.button("Add User"):
            cursor.execute("INSERT INTO users VALUES(%s,%s,%s)",
                           (new_user,hash_password(new_pass),role))
            conn.commit()
            st.success("User Added")

        st.dataframe(pd.read_sql("SELECT username,role FROM users",conn))

    # ================= AI =================
    if menu == "AI Assistant":
        openai.api_key = os.getenv("OPENAI_API_KEY")
        q = st.text_input("Ask AI about team or finance")

        if st.button("Ask AI"):
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role":"user","content":q}]
            )
            st.write(response['choices'][0]['message']['content'])

# ==========================================================
# MAIN
# ==========================================================

if "login" not in st.session_state:
    st.session_state["login"]=False

if not st.session_state["login"]:
    login()
else:
    dashboard()
