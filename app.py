import streamlit as st
import sqlite3
import pandas as pd
import os
import datetime

st.set_page_config(page_title="Buddy Rewards - Complete Phase 1", layout="wide")
DB_FILE = 'buddy_rewards_ultimate.db'

# --- 1. VERİ TABANI VE TÜM AKTÖRLERİN KURULUMU ---
def init_db():
    if os.path.exists(DB_FILE): return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tüm Kullanıcılar ve Gizlilik (Consent)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Role TEXT, Location TEXT, Consent_Given BOOLEAN, 
        EID_Verified BOOLEAN, Sub_Active BOOLEAN, Cert_Complete BOOLEAN, Integrity_Status TEXT)''')
    
    users = [
        ('W-1', 'Ramesh', 'Worker', 'Mussafah', 1, 1, 1, 1, 'Normal'),
        ('W-2', 'Ahmed', 'Worker', 'Dubai', 0, 1, 1, 0, 'Normal'),
        ('C-1', 'John', 'Captain', 'Camp-A', 1, 1, 1, 1, 'Normal'),
        ('CH-1', 'Sarah', 'Champion', 'Abu Dhabi', 1, 1, 1, 1, 'Normal'),
        ('T-1', 'Ali', 'Transporter', 'Sharjah', 1, 1, 1, 1, 'Normal'),
        ('S-1', 'MegaMart', 'Supplier', 'Dubai', 1, 1, 1, 1, 'Normal')
    ]
    cursor.executemany("INSERT INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", users)

    # Aylık Puan Tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Scores (
        Master_ID TEXT, Base_Score REAL, Rollover_Bonus REAL)''')
    cursor.executemany("INSERT INTO Monthly_Scores VALUES (?, ?, ?)", 
                       [('W-1', 85.5, 5.0), ('W-2', 82.0, 0.0), ('C-1', 120.0, 0.0)])
    
    conn.commit()
    conn.close()

init_db()

def load_data(query):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.title("🌐 Buddy Rewards - Ultimate Ecosystem Dashboard")
st.markdown("Includes Dynamic Weights, All Actors (Captains, Champions, Transporters), Mega Locks, and Privacy Layers.")

tab1, tab2, tab3, tab4 = st.tabs(["⚖️ Dynamic Weights Engine", "👥 Ecosystem Scoreboard", "🏆 Mega & Monthly Fairness", "🔔 UI Light Layer (Privacy)"])

# --- TAB 1: DYNAMIC ACTIVE WEIGHT STRUCTURE (Section 7.4) ---
with tab1:
    st.header("Dynamic Active Weight Structure")
    st.markdown("The system redistributes inactive weights to ensure fairness for new/uncertified users. [Section 7.4]")
    
    col_w1, col_w2 = st.columns(2)
    sub_active = col_w1.toggle("Subscription Phase Active (20%)", value=True)
    cert_active = col_w2.toggle("Certification Enabled (15%)", value=False)
    
    # Base Weights
    weights = {'Marketplace': 30, 'Referral': 20, 'Habit': 15, 'Subscription': 20 if sub_active else 0, 'Certification': 15 if cert_active else 0}
    
    total_active_weight = sum(weights.values())
    
    normalized = []
    for comp, weight in weights.items():
        norm = (weight / total_active_weight) * 100 if total_active_weight > 0 else 0
        status = "Active" if weight > 0 else "Ignored"
        normalized.append({'Component': comp, 'Base Weight': f"{weight}%", 'Normalized Weight': f"{norm:.2f}%", 'Status': status})
        
    st.dataframe(pd.DataFrame(normalized), use_container_width=True)

# --- TAB 2: ECOSYSTEM SCOREBOARD (Sections 15, 16, 17, 21, 27) ---
with tab2:
    st.header("Universal Action Registry - Points Dictionary")
    st.markdown("Every actor has a different point matrix. Select a role to see their reward mechanics.")
    
    role = st.selectbox("Select Actor Role:", ["Worker", "Captain (Community)", "Champion (Marketplace)", "Transporter", "Supplier"])
    
    if role == "Worker":
        data = {'Action': ['Daily Video', 'Daily Quiz', 'Referral', 'Supplier Added', 'Fulfill Validated', 'Buddy Help'], 'Points': [5, 5, 10, 20, 40, 10]}
    elif role == "Captain (Community)":
        data = {'Action': ['Verified Signup', 'Active User', 'Monthly Active Cluster', 'High Retention Cluster'], 'Points': [2, 10, 25, 40]}
    elif role == "Champion (Marketplace)":
        data = {'Action': ['Demand Created', 'Demand Propagated', 'Supplier Activated', 'Transporter Activated', 'Marketplace Closure'], 'Points': [20, 10, 15, 15, 50]}
    elif role == "Transporter":
        data = {'Action': ['Return Trip Enabled', 'Multi Pickup Enabled', 'Delivery Completed', 'Empty KM Reduction'], 'Points': [15, 20, 40, 25]}
    else:
        data = {'Action': ['Profile Update', 'Quote Response', 'Fulfillment Closed'], 'Points': [5, 10, 40]}
        
    st.dataframe(pd.DataFrame(data), use_container_width=True)

# --- TAB 3: MEGA & MONTHLY FAIRNESS (Sections 5, 6, 8, 10) ---
with tab3:
    st.header("Monthly Soft Caps & Rollover System")
    col_m1, col_m2 = st.columns([1, 2])
    
    rollover_mode = col_m1.toggle("ROLLOVER_MODE", value=True)
    target_winners = col_m1.slider("Target Winners (Soft Cap)", 1, 10, 2)
    
    df_scores = load_data("SELECT u.Master_ID, u.Role, s.Base_Score, s.Rollover_Bonus FROM Global_Users u JOIN Monthly_Scores s ON u.Master_ID = s.Master_ID")
    
    # Apply Rollover logic
    df_scores['Final_Score'] = df_scores.apply(lambda r: r['Base_Score'] + r['Rollover_Bonus'] if rollover_mode else r['Base_Score'], axis=1)
    df_scores = df_scores.sort_values(by='Final_Score', ascending=False)
    
    df_scores['Status'] = ["✅ Selected" if i < target_winners else "❌ Rolled Over" for i in range(len(df_scores))]
    
    col_m2.dataframe(df_scores[['Master_ID', 'Role', 'Final_Score', 'Status']], use_container_width=True)

# --- TAB 4: UI LIGHT LAYER & PRIVACY (Section 22) ---
with tab4:
    st.header("Reward Celebration Light Layer")
    st.markdown("Triggers FOMO and dopamine loops. Adheres to strict privacy (Consent) rules. [Section 22.3]")
    
    df_users = load_data("SELECT Master_ID, Name, Location, Consent_Given, Role FROM Global_Users")
    selected_user = st.selectbox("Simulate Reward For:", df_users['Master_ID'])
    
    user_row = df_users[df_users['Master_ID'] == selected_user].iloc[0]
    
    if st.button("Trigger Celebration Banner"):
        if user_row['Consent_Given']:
            # Consent True -> Show First Name [Section 22.3]
            st.success(f"🎉 {user_row['Name']} from {user_row['Location']} unlocked a Monthly Benefit!")
        else:
            # Consent False -> Fully Anonymous [Section 22.3]
            st.success(f"🎉 A {user_row['Role'].lower()} from {user_row['Location']} unlocked a Monthly Benefit!")
        
        st.info("Pulse notification and ticker celebration activated.")
