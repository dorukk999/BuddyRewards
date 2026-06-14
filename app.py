import streamlit as st
import sqlite3
import pandas as pd
import os
import datetime

# Page Settings
st.set_page_config(page_title="Buddy Rewards - Admin Dashboard", layout="wide")
DB_FILE = 'buddy_rewards.db'

# --- AUTO-SETUP MOCK DATABASE FOR CLOUD DEPLOYMENT ---
# Bu fonksiyon Streamlit Cloud üzerinde veri tabanını otomatik oluşturur
def init_db():
    if os.path.exists(DB_FILE):
        return # DB zaten varsa tekrar oluşturma
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Monthly Qualified Users Table & Data
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Qualified_Users (
        Master_ID TEXT PRIMARY KEY, Nationality TEXT, Labor_Cluster TEXT, Total_Score REAL, Rollover_Bonus REAL DEFAULT 0)''')
    users = [
        ('USER-1', 'India', 'Camp-A', 85.5, 5.0),
        ('USER-2', 'India', 'Camp-A', 82.0, 0.0),
        ('USER-3', 'India', 'Camp-B', 81.0, 10.0),
        ('USER-4', 'Pakistan', 'Camp-A', 79.0, 0.0),
        ('USER-5', 'Bangladesh', 'Camp-C', 75.0, 0.0),
        ('USER-6', 'India', 'Camp-A', 74.0, 0.0)
    ]
    cursor.executemany("INSERT OR IGNORE INTO Monthly_Qualified_Users VALUES (?, ?, ?, ?, ?)", users)
    
    # 2. Event Stream Logs Table & Data
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Action_ID TEXT, Event_Timestamp TEXT, Process_Status TEXT)''')
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status) VALUES ('USER-1', 'WORKER_VIDEO_WATCH', ?, 'Processed')", (str(datetime.datetime.now()),))
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status) VALUES ('USER-1', 'WORKER_REFERRAL', ?, 'Processed')", (str(datetime.datetime.now()),))
    
    # 3. Integrity Profiles Table & Data
    cursor.execute('''CREATE TABLE IF NOT EXISTS Integrity_Profiles (
        Master_ID TEXT PRIMARY KEY, Integrity_Score INTEGER DEFAULT 100, Action_Status TEXT DEFAULT 'Normal')''')
    cursor.executemany("INSERT OR IGNORE INTO Integrity_Profiles (Master_ID, Integrity_Score, Action_Status) VALUES (?, ?, ?)", 
                       [('USER-1', 100, 'Normal'), ('USER-SUSPECT', 60, 'Warning'), ('USER-SPAMMER', 30, 'Block')])
    
    conn.commit()
    conn.close()

# Sayfa yüklendiğinde DB kontrolü yap
init_db()

def load_data(query):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.title("🏆 Buddy Rewards Engine - Phase 1 Preview Dashboard")
st.markdown("This dashboard live-visualizes the background data of the AI-driven marketplace activation and fairness engine.")

# --- 1. MONTHLY SELECTION AND FAIRNESS ENGINE ---
st.header("1. Monthly Winners and Fairness Engine")
st.markdown("This module filters winners from the pool based on the admin-defined limits (Soft Cap) and fairness rules.")

col1, col2, col3 = st.columns(3)
total_winners_cap = col1.slider("Target Winner Count (Soft Cap)", 1, 50, 3)
max_per_nationality = col2.slider("Max Nationality Limit", 1, 20, 2)
max_per_cluster = col3.slider("Max Labor Cluster Limit", 1, 20, 2)

try:
    df_monthly = load_data("""
        SELECT Master_ID, Nationality, Labor_Cluster, Total_Score, Rollover_Bonus, 
               (Total_Score + Rollover_Bonus) as Final_Ranking_Score
        FROM Monthly_Qualified_Users
        ORDER BY Final_Ranking_Score DESC
    """)
    
    winners = []
    nat_counts = {}
    cluster_counts = {}
    
    for _, row in df_monthly.iterrows():
        if len(winners) >= total_winners_cap:
            break
        nat = row['Nationality']
        cluster = row['Labor_Cluster']
        
        if (nat_counts.get(nat, 0) < max_per_nationality) and (cluster_counts.get(cluster, 0) < max_per_cluster):
            row['Status'] = "✅ Selected"
            winners.append(row)
            nat_counts[nat] = nat_counts.get(nat, 0) + 1
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        else:
            row['Status'] = "❌ Eliminated (Fairness Limit)"
            winners.append(row) 

    st.dataframe(pd.DataFrame(winners)[['Master_ID', 'Nationality', 'Labor_Cluster', 'Final_Ranking_Score', 'Status']], use_container_width=True)
except Exception as e:
    st.warning("Monthly Reward test data has not been generated yet.")

st.divider()

# --- 2. MEGA REWARD QUALIFICATION TRACKING ---
st.header("2. Mega Reward Qualification Progress")
st.markdown("Displays the users' progress towards the locked Mega Reward targets.")

try:
    df_events = load_data("SELECT Master_ID, Action_ID, Process_Status FROM Event_Stream_Logs WHERE Process_Status = 'Processed'")
    
    mega_targets = {
        'WORKER_VIDEO_WATCH': 180, 'WORKER_QUIZ_ATTEMPT': 180, 'WORKER_REFERRAL': 150,
        'WORKER_ADD_SUPPLIER': 50, 'WORKER_FULFILLMENT': 10, 'WORKER_BUDDY_HELP': 12
    }
    
    if not df_events.empty:
        user_list = df_events['Master_ID'].unique()
        selected_user = st.selectbox("Select Worker (Master ID):", user_list)
        
        user_events = df_events[df_events['Master_ID'] == selected_user]
        
        cols = st.columns(3)
        idx = 0
        for action, target in mega_targets.items():
            count = len(user_events[user_events['Action_ID'] == action])
            progress = min(count / target, 1.0)
            
            with cols[idx % 3]:
                st.metric(label=action.replace("WORKER_", ""), value=f"{count} / {target}")
                st.progress(progress)
            idx += 1
except Exception as e:
    st.warning("Event test data has not been generated yet.")

st.divider()

# --- 3. INTEGRITY AND SECURITY ENGINE ---
st.header("3. Integrity Engine")
st.markdown("Actions applied by the AI-based security firewall on system accounts.")

try:
    df_integrity = load_data("SELECT * FROM Integrity_Profiles")
    
    def color_status(val):
        color = 'green' if val == 'Normal' else 'orange' if val == 'Warning' else 'red' if val == 'Block' else 'black'
        return f'color: {color}; font-weight: bold'
    
    st.dataframe(df_integrity.style.map(color_status, subset=['Action_Status']), use_container_width=True)
except Exception as e:
    st.warning("Integrity test data has not been generated yet.")
