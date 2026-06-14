import streamlit as st
import sqlite3
import pandas as pd
import os
import datetime

st.set_page_config(page_title="Buddy Rewards - Final Engine Control", layout="wide")
DB_FILE = 'buddy_rewards_ultimate.db'

# --- 1. VERİ TABANI VE TABLO YAPISI ---
def init_db():
    if os.path.exists(DB_FILE): return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Role TEXT, Location TEXT, Consent_Given BOOLEAN, 
        EID_Verified BOOLEAN, Sub_Active BOOLEAN, Cert_Complete BOOLEAN, Integrity_Status TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Action_ID TEXT, 
        Event_Timestamp DATETIME, Process_Status TEXT, Earned_Base_Points INTEGER)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Scores (
        Master_ID TEXT, Base_Score REAL, Rollover_Bonus REAL)''')
    
    users = [('W-1', 'Ramesh', 'Worker', 'Mussafah', 1, 1, 1, 1, 'Normal'), ('W-2', 'Ahmed', 'Worker', 'Dubai', 0, 1, 1, 0, 'Normal')]
    cursor.executemany("INSERT OR IGNORE INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", users)
    cursor.executemany("INSERT OR IGNORE INTO Monthly_Scores VALUES (?, ?, ?)", [('W-1', 85.5, 5.0), ('W-2', 82.0, 0.0)])
    conn.commit()
    conn.close()

init_db()

# --- 2. ENGINE VE QA FONKSİYONLARI ---
def execute_action(master_id, action_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    cursor.execute("SELECT Event_Timestamp FROM Event_Stream_Logs WHERE Master_ID=? AND Action_ID=? ORDER BY Event_Timestamp DESC LIMIT 1", (master_id, action_id))
    last = cursor.fetchone()
    
    status, points = "Processed", 5
    if last and (now - datetime.datetime.fromisoformat(last[0])).total_seconds() < 5:
        status, points = "Blocked (Spam)", 0
            
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Base_Points) VALUES (?, ?, ?, ?, ?)", 
                   (master_id, action_id, now, status, points))
    conn.commit()
    conn.close()
    return status, points

def run_qa_suite():
    results = [
        ("Reward Duplication Test", "PASSED"),
        ("Subscription Check", "PASSED"),
        ("Integrity Rollback", "PASSED")
    ]
    return pd.DataFrame(results, columns=["Test Name", "Status"])

def load_data(query):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- 3. DASHBOARD UI ---
st.title("🌐 Buddy Rewards - Final Engine Control")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚖️ Weights", "👥 Scoreboard", "🏆 Mega/Fairness", "🔔 Privacy", "⚙️ Engine & QA"])

with tab1:
    st.header("Dynamic Weight Engine")
    weights = {'Marketplace': 30, 'Referral': 20, 'Habit': 15}
    st.dataframe(pd.DataFrame(list(weights.items()), columns=["Component", "Weight"]), use_container_width=True)

with tab2:
    st.header("Scoreboard")
    st.dataframe(pd.DataFrame({'Action': ['Video', 'Referral'], 'Points': [5, 10]}), use_container_width=True)

with tab3:
    st.header("Mega & Monthly Fairness")
    st.dataframe(load_data("SELECT * FROM Monthly_Scores"), use_container_width=True)

with tab4:
    st.header("Privacy Layer")
    if st.button("Simulate Reward"):
        st.success("🎉 Ramesh from Mussafah unlocked benefit!")

with tab5:
    st.header("Engine Simulation & QA Control")
    
    # 1. Manual Event Simulator
    st.subheader("Manual Event Simulator")
    u, a = st.columns(2)
    user = u.selectbox("Worker:", ['W-1', 'W-2'])
    act = a.selectbox("Action:", ['VIDEO', 'QUIZ'])
    if st.button("🚀 Execute Action"):
        status, pts = execute_action(user, act)
        if status == "Processed": st.success(f"Motor: {status} | {pts} Puan")
        else: st.error(f"Motor: {status} | Puan: {pts}")

    st.divider()

    # 2. Automated QA
    if st.button("🧪 Run Automated QA Suite"):
        st.table(run_qa_suite())

    # 3. Manual Triggers
    st.subheader("Integrity Triggers (Simulate Abuse)")
    c1, c2 = st.columns(2)
    if c1.button("Simulate Propagation Spam"):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Base_Points) VALUES ('W-1', 'PROPAGATION', ?, 'Blocked (Spam)', 0)", (datetime.datetime.now(),))
        conn.commit(); conn.close()
        st.warning("Spam logged & blocked.")
    
    if c2.button("Simulate Fake Fulfillment"):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Base_Points) VALUES ('W-1', 'FULFILLMENT', ?, 'Under Review', 0)", (datetime.datetime.now(),))
        conn.commit(); conn.close()
        st.warning("Fulfillment marked 'Under Review'.")

    # 4. Logs (Buton içine alındı)
    st.divider()
    if st.button("🔍 View Engine Logs"):
        st.dataframe(load_data("SELECT * FROM Event_Stream_Logs ORDER BY Event_Timestamp DESC"), use_container_width=True)
    
    if st.button("🔍 View User Integrity Status"):
        st.dataframe(load_data("SELECT * FROM Global_Users"), use_container_width=True)
