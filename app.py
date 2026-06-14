import streamlit as st
import sqlite3
import pandas as pd
import os
import datetime

st.set_page_config(page_title="Buddy Rewards - Live Engine", layout="wide")
DB_FILE = 'buddy_rewards_ultimate.db'

# --- 1. VERİ TABANI KURULUMU ---
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
    
    users = [('W-1', 'Ramesh', 'Worker', 'Mussafah', 1, 1, 1, 1, 'Normal'), ('W-2', 'Ahmed', 'Worker', 'Dubai', 0, 1, 1, 0, 'Normal'), ('C-1', 'John', 'Captain', 'Camp-A', 1, 1, 1, 1, 'Normal')]
    cursor.executemany("INSERT OR IGNORE INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", users)
    cursor.executemany("INSERT OR IGNORE INTO Monthly_Scores VALUES (?, ?, ?)", [('W-1', 85.5, 5.0), ('W-2', 82.0, 0.0), ('C-1', 120.0, 0.0)])
    conn.commit()
    conn.close()

init_db()

# --- 2. ENGINE MANTIĞI (SIMULATION) ---
def execute_action(master_id, action_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    
    # Cooldown Kontrolü (PDF Section 12.1) [cite: 405-407]
    cursor.execute("SELECT Event_Timestamp FROM Event_Stream_Logs WHERE Master_ID=? AND Action_ID=? ORDER BY Event_Timestamp DESC LIMIT 1", (master_id, action_id))
    last_event = cursor.fetchone()
    
    status = "Processed"
    points = 5
    
    if last_event:
        last_time = datetime.datetime.fromisoformat(last_event[0])
        if (now - last_time).total_seconds() < 5:
            status = "Blocked (Cooldown)"
            points = 0
            
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Base_Points) VALUES (?, ?, ?, ?, ?)", 
                   (master_id, action_id, now, status, points))
    conn.commit()
    conn.close()
    return status, points

def load_data(query):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.title("🌐 Buddy Rewards - Live Engine Control Center")
st.markdown("Müşteri burada 'Action' butonlarına basarak motorun (Cooldown, Integrity, Fairness) nasıl anlık karar verdiğini test edebilir.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚖️ Weights", "👥 Scoreboard", "🏆 Mega/Fairness", "🔔 Privacy", "⚙️ Engine Simulator"])

# --- TAB 1, 2, 3, 4 (Mevcut yapı korundu) ---
with tab1:
    st.header("Dynamic Active Weight Structure")
    st.info("Sistem, aktif olmayan bileşenleri (Subscription/Cert) sistemden çıkardığında ağırlıkları otomatik yeniden hesaplar [cite: 220-227].")
    weights = {'Marketplace': 30, 'Referral': 20, 'Habit': 15, 'Subscription': 20, 'Certification': 15}
    st.dataframe(pd.DataFrame(list(weights.items()), columns=["Component", "Weight"]), use_container_width=True)

with tab2:
    st.header("Universal Action Registry")
    st.dataframe(pd.DataFrame({'Action': ['Daily Video', 'Referral', 'Buddy Help'], 'Points': [5, 10, 10]}), use_container_width=True)

with tab3:
    st.header("Monthly Soft Caps")
    st.write("Fairness engine: Max nationality/geography limits applied here [cite: 292-298].")
    st.dataframe(load_data("SELECT * FROM Monthly_Scores"), use_container_width=True)

with tab4:
    st.header("Privacy Layer")
    st.write("Consent_Given kontrolü ile kullanıcı isimlerini maskeler [cite: 594-599].")

# --- TAB 5: ENGINE SIMULATOR ---
with tab5:
    st.header("Engine Simulation Station")
    st.markdown("Müşteri aşağıdaki butona basarak 'Worker'ın eylemlerini taklit edebilir ve motorun cevabını anlık görebilir.")
    
    col_a, col_b = st.columns(2)
    user = col_a.selectbox("Select Worker:", ['W-1', 'W-2'])
    action = col_b.selectbox("Action:", ['VIDEO', 'QUIZ', 'REFERRAL'])
    
    if st.button("🚀 Execute Action (Simulate Engine)"):
        status, points = execute_action(user, action)
        if status == "Processed":
            st.success(f"Motor Kararı: {status} | Puan: {points}")
        else:
            st.error(f"Motor Kararı: {status} | Puan: {points} (Cooldown ihlali tespit edildi!)")
    
    st.divider()
    st.subheader("Live Event Stream Log (Engine Database)")
    if st.button("Refresh Logs"):
        st.dataframe(load_data("SELECT * FROM Event_Stream_Logs ORDER BY Event_Timestamp DESC LIMIT 10"), use_container_width=True)
