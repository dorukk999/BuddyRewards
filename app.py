import streamlit as st
import sqlite3
import pandas as pd
import datetime

st.set_page_config(page_title="Buddy Rewards - AI Engine", layout="wide")
DB_FILE = 'buddy_rewards_ultimate.db'

# --- 1. VERİ TABANI ŞEMASI (PDF KURALLARINA GÖRE) ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Global Users (Nationality & Labor Cluster eklendi - Section 8) [cite: 274, 296, 297]
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Nationality TEXT, Labor_Cluster TEXT, 
        Consent_Given BOOLEAN, Integrity_Status TEXT)''')
    # Event Stream (Section 25) [cite: 624]
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Action_ID TEXT, 
        Event_Timestamp DATETIME, Process_Status TEXT, Earned_Base_Points INTEGER)''')
    # Monthly Fairness Table [cite: 308]
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Scores (
        Master_ID TEXT, Total_Score REAL, Rollover_Bonus REAL)''')
    
    # Örnek Veri
    users = [('W-1', 'Ramesh', 'India', 'Camp-A', 1, 'Normal'), ('W-2', 'Ahmed', 'Egypt', 'Camp-A', 0, 'Normal'), ('W-3', 'John', 'Philippines', 'Camp-B', 1, 'Normal')]
    cursor.executemany("INSERT OR IGNORE INTO Global_Users VALUES (?, ?, ?, ?, ?, ?)", users)
    conn.commit()
    conn.close()

init_db()

# --- 2. ENGINE MANTIĞI (SIMULATION) ---
def execute_engine_action(master_id, action_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    
    # Cooldown Kontrolü (Section 12.1) [cite: 405-407]
    cursor.execute("SELECT Event_Timestamp FROM Event_Stream_Logs WHERE Master_ID=? AND Action_ID=? ORDER BY Event_Timestamp DESC LIMIT 1", (master_id, action_id))
    last = cursor.fetchone()
    
    if last and (now - datetime.datetime.fromisoformat(last[0])).total_seconds() < 5:
        status, pts = "Blocked (Spam)", 0
    else:
        status, pts = "Processed", 5
            
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Base_Points) VALUES (?, ?, ?, ?, ?)", 
                   (master_id, action_id, now, status, pts))
    conn.commit()
    conn.close()
    return status, pts

def run_fairness_engine(cap, nat_limit, cluster_limit):
    # Adalet Motoru (Section 8.4) [cite: 292-298]
    df = pd.read_sql_query("SELECT * FROM Global_Users", sqlite3.connect(DB_FILE))
    winners = []
    nat_counts, cluster_counts = {}, {}
    for _, row in df.iterrows():
        if len(winners) >= cap: break
        nat, cluster = row['Nationality'], row['Labor_Cluster']
        if nat_counts.get(nat, 0) < nat_limit and cluster_counts.get(cluster, 0) < cluster_limit:
            winners.append({**row, "Status": "✅ Selected"})
            nat_counts[nat] = nat_counts.get(nat, 0) + 1
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        else:
            winners.append({**row, "Status": "❌ Fairness Limit"})
    return pd.DataFrame(winners)

# --- 3. DASHBOARD UI ---
st.title("🌐 Buddy Rewards - AI Behavioral Economy Engine")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚖️ Weights", "👥 Scoreboard", "🏆 Fairness Engine", "🔔 Privacy", "⚙️ Engine & QA"])

with tab1:
    st.header("Dynamic Weight Engine")
    st.markdown("Ağırlıklar: Marketplace 30%, Referral 20%, Habit 15% [cite: 228]")
    weights = {'Marketplace': 30, 'Referral': 20, 'Habit': 15}
    st.dataframe(pd.DataFrame(list(weights.items()), columns=["Comp", "Weight"]), use_container_width=True)

with tab2:
    st.header("Global Users")
    st.dataframe(pd.read_sql_query("SELECT * FROM Global_Users", sqlite3.connect(DB_FILE)), use_container_width=True)

with tab3:
    st.header("Fairness & Diversity Engine")
    cap = st.slider("Max Winners", 1, 10, 3)
    n_lim = st.slider("Max per Nationality", 1, 5, 2)
    c_lim = st.slider("Max per Cluster", 1, 5, 2)
    st.dataframe(run_fairness_engine(cap, n_lim, c_lim), use_container_width=True)

with tab4:
    st.header("Privacy Layer (Section 22.3)")
    u = st.selectbox("Select User for Reward Test:", ['W-1', 'W-2'])
    if st.button("Simulate Public Reward"):
        user = pd.read_sql_query(f"SELECT * FROM Global_Users WHERE Master_ID='{u}'", sqlite3.connect(DB_FILE)).iloc[0]
        if user['Consent_Given']:
            st.success(f"🎉 {user['Name']} from {user['Location']} kazandı!")
        else:
            st.warning(f"🎉 A {user['Role']} from {user['Location']} kazandı! (İsim maskelendi) ")

with tab5:
    st.header("Engine Simulation & QA (Section 28)")
    
    st.subheader("Manual Event Simulation")
    u_sim, a_sim = st.columns(2)
    user_s = u_sim.selectbox("Worker:", ['W-1', 'W-2'])
    act_s = a_sim.selectbox("Action:", ['VIDEO', 'QUIZ'])
    
    if st.button("🚀 Execute Action"):
        s, p = execute_engine_action(user_s, act_s)
        st.write(f"Motor Kararı: {s} | Puan: {p}")
        
    st.divider()
    
    st.subheader("QA Compliance Triggers")
    c1, c2 = st.columns(2)
    if c1.button("Simulate Spam"):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Process_Status) VALUES ('W-1', 'VIDEO', 'Blocked (Spam)')")
        conn.commit(); conn.close()
        st.error("Spam Blocked[cite: 679].")
        
    if c2.button("Simulate Integrity Rollback"):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("UPDATE Global_Users SET Integrity_Status='Block' WHERE Master_ID='W-1'")
        conn.commit(); conn.close()
        st.warning("User Blocked[cite: 685].")
        
    if st.button("🔍 View Event Logs"):
        st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_Timestamp DESC", sqlite3.connect(DB_FILE)), use_container_width=True)
