import streamlit as st
import sqlite3
import pandas as pd
import os
import datetime

# Page Settings
st.set_page_config(page_title="Buddy Rewards - Full Phase 1 Dashboard", layout="wide")
DB_FILE = 'buddy_rewards_final.db'

# --- AUTO-SETUP MOCK DATABASE WITH ADVANCED CORE ---
def init_db():
    if os.path.exists(DB_FILE):
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Monthly Qualified Users
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Qualified_Users (
        Master_ID TEXT PRIMARY KEY, Nationality TEXT, Labor_Cluster TEXT, Total_Score REAL, Rollover_Bonus REAL DEFAULT 0)''')
    users = [('USER-1', 'India', 'Camp-A', 85.5, 5.0), ('USER-2', 'India', 'Camp-A', 82.0, 0.0),
             ('USER-3', 'India', 'Camp-B', 81.0, 10.0), ('USER-INCOMPLETE', 'Pakistan', 'Camp-A', 79.0, 0.0)]
    cursor.executemany("INSERT OR IGNORE INTO Monthly_Qualified_Users VALUES (?, ?, ?, ?, ?)", users)
    
    # 2. Worker Profiles (For Mega Mandatory Checks)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Worker_Profiles (
        Master_ID TEXT PRIMARY KEY, EID_Verified BOOLEAN, Subscription_Continuity BOOLEAN, Certification_Complete BOOLEAN, Integrity_Status TEXT)''')
    profiles = [
        ('USER-1', 1, 1, 1, 'Normal'), # Perfect User
        ('USER-2', 1, 1, 0, 'Normal'), # No Certification
        ('USER-3', 1, 0, 1, 'Warning'), # Subscription Lapsed
        ('USER-INCOMPLETE', 0, 1, 0, 'Normal') # No EID
    ]
    cursor.executemany("INSERT OR IGNORE INTO Worker_Profiles VALUES (?, ?, ?, ?, ?)", profiles)

    # 3. Advanced Event Stream Logs (Base Points & Cooldowns)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Action_ID TEXT, 
        Target_User_ID TEXT, Target_Item_ID TEXT, Event_Timestamp DATETIME, Process_Status TEXT, Earned_Base_Points INTEGER)''')
    
    now = datetime.datetime.now()
    events = [
        ('USER-1', 'WORKER_FULFILLMENT', None, None, now, 'Processed', 40),
        ('USER-1', 'WORKER_REFERRAL', None, None, now, 'Processed', 10),
        # Pair Cooldown Spam Simulation
        ('USER-2', 'WORKER_BUDDY_HELP', 'USER-3', None, now, 'Blocked (Pair Cooldown)', 0),
        ('USER-2', 'WORKER_BUDDY_HELP', 'USER-3', None, now, 'Blocked (Pair Cooldown)', 0),
        # Marketplace Cooldown Spam Simulation
        ('USER-3', 'WORKER_ADD_SUPPLIER', None, 'SUPPLIER-99', now, 'Blocked (Market Cooldown)', 0)
    ]
    cursor.executemany("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Target_User_ID, Target_Item_ID, Event_Timestamp, Process_Status, Earned_Base_Points) VALUES (?, ?, ?, ?, ?, ?, ?)", events)

    # 4. Integrity Profiles
    cursor.execute('''CREATE TABLE IF NOT EXISTS Integrity_Profiles (
        Master_ID TEXT PRIMARY KEY, Integrity_Score INTEGER, Action_Status TEXT)''')
    cursor.executemany("INSERT OR IGNORE INTO Integrity_Profiles VALUES (?, ?, ?)", 
                       [('USER-1', 100, 'Normal'), ('USER-3', 60, 'Warning'), ('USER-SPAMMER', 30, 'Block')])
    
    conn.commit()
    conn.close()

init_db()

def load_data(query):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.title("🏆 Buddy Rewards Engine - Full Phase 1 Dashboard")
st.markdown("Live backend data visualization featuring Fairness limits, Mega qualifications, and Anti-Spam (Cooldown) systems.")

# --- 1. MEGA REWARD MANDATORY CHECKS ---
st.header("1. Mega Reward: Mandatory Qualification & Profiles")
st.markdown("Before counting events, users must pass these dynamic mandatory locks.")

col_a, col_b = st.columns([1, 2])
cert_required = col_a.toggle("CERTIFICATION_REQUIRED_FOR_MEGA", value=True)

df_profiles = load_data("SELECT * FROM Worker_Profiles")
def check_mega_eligibility(row):
    if not row['EID_Verified']: return "❌ Failed (No EID)"
    if not row['Subscription_Continuity']: return "❌ Failed (Subscription Lapsed)"
    if row['Integrity_Status'] in ['Review', 'Block']: return "❌ Failed (Integrity Alert)"
    if cert_required and not row['Certification_Complete']: return "❌ Failed (No Certification)"
    return "✅ Passed Mandatory Locks"

df_profiles['Mega_Eligibility_Status'] = df_profiles.apply(check_mega_eligibility, axis=1)

def highlight_status(val):
    color = 'green' if '✅' in str(val) else 'red' if '❌' in str(val) else ''
    return f'color: {color}; font-weight: bold'

col_b.dataframe(df_profiles[['Master_ID', 'EID_Verified', 'Subscription_Continuity', 'Certification_Complete', 'Mega_Eligibility_Status']].style.map(highlight_status, subset=['Mega_Eligibility_Status']), use_container_width=True)

st.divider()

# --- 2. ADVANCED COOLDOWN & BASE POINTS ENGINE ---
st.header("2. AI Event Stream: Base Points & Anti-Spam Logs")
st.markdown("Real-time logging of events showing earned Base Points and active Cooldown Blocks (Pair & Marketplace loops).")

df_events = load_data("SELECT Master_ID, Action_ID, Target_User_ID, Target_Item_ID, Earned_Base_Points, Process_Status FROM Event_Stream_Logs")

def format_process(val):
    color = 'red' if 'Blocked' in str(val) else 'green'
    return f'color: {color}; font-weight: bold'

st.dataframe(df_events.style.map(format_process, subset=['Process_Status']), use_container_width=True)

st.divider()

# --- 3. MONTHLY FAIRNESS ENGINE ---
st.header("3. Monthly Winners & Fairness Engine")
col1, col2, col3 = st.columns(3)
total_winners = col1.slider("Target Winner Count (Soft Cap)", 1, 50, 3)
max_nat = col2.slider("Max Nationality Limit", 1, 20, 2)
max_camp = col3.slider("Max Labor Cluster Limit", 1, 20, 2)

df_monthly = load_data("SELECT Master_ID, Nationality, Labor_Cluster, Total_Score, Rollover_Bonus, (Total_Score + Rollover_Bonus) as Final_Score FROM Monthly_Qualified_Users ORDER BY Final_Score DESC")
winners, nat_counts, cluster_counts = [], {}, {}

for _, row in df_monthly.iterrows():
    if len(winners) >= total_winners: break
    nat, cluster = row['Nationality'], row['Labor_Cluster']
    if nat_counts.get(nat, 0) < max_nat and cluster_counts.get(cluster, 0) < max_camp:
        row['Status'] = "✅ Selected"
        winners.append(row)
        nat_counts[nat] = nat_counts.get(nat, 0) + 1
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
    else:
        row['Status'] = "❌ Eliminated (Fairness)"
        winners.append(row)

st.dataframe(pd.DataFrame(winners)[['Master_ID', 'Nationality', 'Labor_Cluster', 'Final_Score', 'Status']].style.map(highlight_status, subset=['Status']), use_container_width=True)
