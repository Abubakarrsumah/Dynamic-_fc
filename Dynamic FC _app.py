# ==========================================================
# ⚽ DYNAMIC FC FALABA DISTRICT - CLOUD SAFE VERSION
# No psycopg2 | No external DB | SQLite only
# Run: streamlit run football_app.py
# ==========================================================

import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import datetime
import plotly.express as px
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import os

# ==========================================================
# CONFIG
# ==========================================================

TEAM_NAME = "Dynamic FC Falaba District"
st.set_page_config(page_title=TEAM_NAME, layout="wide")

# ==========================================================
# DATABASE (STREAMLIT SAFE)
# ==========================================================

conn = sqlite3.connect("dynamic_fc.db", check_same_thread=False)
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        category TEXT,
        amount REAL,
        description TEXT,
        date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contributions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        investor TEXT,
        amount REAL,
        date TEXT
    )
    """)

    conn.commit()

create_tables()

# Default Admin
cursor.execute("SELECT * FROM users WHERE username=?", ("admin",))
if not cursor.fetchone():
    cursor.execute("INSERT INTO users VALUES (?, ?, ?)",
                   ("admin", hash_password("admin123"), "Super Admin"))
    conn.commit()

# ==========================================================
# LOGIN SYSTEM
# ==========================================================

def login():
    st.title(f"🔐 {TEAM_NAME} Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                           (username, hash_password(password)))
            user = cursor.fetchone()

            if user:
                st.session_state["role"] = user[2]
                st.session_state["logged_in"] = True
                st.success("Login Successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

        except Exception as e:
            st.error(f"Login Error: {e}")

# ==========================================================
# PERFORMANCE AI SCORING
# ==========================================================

def calculate_score(goals, assists, fitness):
    return goals*4 + assists*3 + fitness*2

# ==========================================================
# PDF RECEIPT
# ==========================================================

def generate_pdf(text):
    doc = SimpleDocTemplate("receipt.pdf")
    styles = getSampleStyleSheet()
    doc.build([Paragraph(text, styles["Normal"])])

# ==========================================================
# DASHBOARD
# ==========================================================

def dashboard():

    st.title(f"🏢 {TEAM_NAME} Enterprise System")

    menu = st.sidebar.selectbox("Menu",
        ["Dashboard","Players","Finance","Admin","Reports"])

    # ================= DASHBOARD =================
    if menu == "Dashboard":
        df = pd.read_sql("SELECT * FROM finance", conn)

        if not df.empty:
            income = df[df["type"]=="Income"]["amount"].sum()
            expense = df[df["type"]=="Expenditure"]["amount"].sum()
            profit = income - expense

            col1,col2,col3 = st.columns(3)
            col1.metric("Income", income)
            col2.metric("Expense", expense)
            col3.metric("Profit", profit)

            fig = px.pie(df, names="type", values="amount")
            st.plotly_chart(fig)
        else:
            st.info("No financial records yet.")

    # ================= PLAYERS =================
    if menu == "Players":

        st.subheader("Register Player")

        with st.form("player_form"):
            name = st.text_input("Name")
            age = st.number_input("Age",10,50)
            position = st.text_input("Position")
            health = st.selectbox("Health",["Fit","Injured"])
            injury = st.text_input("Injury")
            status = st.selectbox("Status",["Active","Suspended"])
            fitness = st.slider("Fitness",1,10)
            goals = st.number_input("Goals",0)
            assists = st.number_input("Assists",0)

            submit = st.form_submit_button("Save")

        if submit:
            try:
                score = calculate_score(goals, assists, fitness)
                cursor.execute("""
                INSERT INTO players(name,age,position,health,injury,status,fitness,score)
                VALUES(?,?,?,?,?,?,?,?)
                """,(name,age,position,health,injury,status,fitness,score))
                conn.commit()
                st.success("Player Saved")
            except Exception as e:
                st.error(f"Player Error: {e}")

        st.dataframe(pd.read_sql("SELECT * FROM players", conn))

    # ================= FINANCE =================
    if menu == "Finance":

        with st.form("finance_form"):
            t = st.selectbox("Type",["Income","Expenditure"])
            category = st.text_input("Category")
            amount = st.number_input("Amount",0.0)
            description = st.text_input("Description")
            submit = st.form_submit_button("Record")

        if submit:
            try:
                cursor.execute("""
                INSERT INTO finance(type,category,amount,description,date)
                VALUES(?,?,?,?,?)
                """,(t,category,amount,description,str(datetime.date.today())))
                conn.commit()
                generate_pdf(f"{t} {amount}")
                st.success("Recorded & Receipt Generated")
            except Exception as e:
                st.error(f"Finance Error: {e}")

        st.subheader("Investor Contributions")

        investor = st.text_input("Investor Name")
        amount_c = st.number_input("Contribution",0.0)

        if st.button("Save Contribution"):
            cursor.execute("""
            INSERT INTO contributions(investor,amount,date)
            VALUES(?,?,?)
            """,(investor,amount_c,str(datetime.date.today())))
            conn.commit()
            st.success("Contribution Saved")

    # ================= ADMIN =================
    if menu == "Admin" and st.session_state["role"]=="Super Admin":

        st.subheader("Admin Master Controller")

        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password")
        role = st.selectbox("Role",["Super Admin","Finance","Coach"])

        if st.button("Add User"):
            cursor.execute("INSERT INTO users VALUES(?,?,?)",
                           (new_user,hash_password(new_pass),role))
            conn.commit()
            st.success("User Added")

        st.dataframe(pd.read_sql("SELECT username,role FROM users",conn))

    # ================= REPORTS =================
    if menu == "Reports":
        df = pd.read_sql("SELECT * FROM finance", conn)
        st.download_button("Download Financial Report",
                           df.to_csv(index=False),
                           file_name="finance_report.csv")

# ==========================================================
# MAIN
# ==========================================================

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
else:
    dashboard()
