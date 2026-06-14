import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os

st.set_page_config(page_title="Buddy Rewards - Ecosystem Engine", layout="wide")
DB_FILE = 'buddy_rewards_ultimate.db'

# --- 1. MERKEZİ ROL VE YETENEK TANIMLARI (ROLE REGISTRY) ---
ROLE_REGISTRY = {
    "Worker": {"Actions": {"VIDEO": 5, "QUIZ": 5, "REFERRAL": 10}, "Category": "Engagement"},
    "Supplier": {"Actions": {"PROFILE": 5, "QUOTE": 10, "FULFILLMENT": 40}, "Category": "Commerce"},
    "Contractor": {"Actions": {"POST_REQ": 20, "VALIDATE": 40}, "Category": "Demand"},
    "Transporter": {"Actions": {"RETURN_TRIP": 15, "MULTI_PICKUP": 20, "DELIVERY": 40}, "Category": "Logistics"},
    "Captain": {"Actions": {"VERIFY_SIGNUP": 2, "ACTIVE_CLUSTER": 25}, "Category": "Growth"},
    "Champion": {"Actions": {"DEMAND_CREATED": 20, "CLOSURE": 50}, "Category": "Marketplace"}
}

# --- 2. VERİ TABANI ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Role TEXT, Location TEXT, Nationality TEXT, 
        Labor_Cluster TEXT, Consent_Given BOOLEAN, Integrity_Status TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Action_ID TEXT, 
        Event_Timestamp DATETIME, Process_Status TEXT, Earned_Base_Points INTEGER)''')
    
    # 20 Kullanıcıyı ROLE_REGISTRY'den rolleri alarak oluştur
    roles_list = list(ROLE_REGISTRY.keys())
    nationalities = ['India', 'Egypt', 'Philippines', 'Turkey']
    clusters = ['Camp-A', 'Camp-B', 'Camp-C']
    
    users = []
    for i in range(1, 21):
        users.append((f'ID-{i}', f'User-{i}', roles_list[i % len(roles_list)], 'Dubai', 
                      nationalities[i % len(nationalities)], clusters[i % len(clusters)], 
                      1, 'Normal'))
    
    cursor.executemany("INSERT OR IGNORE INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", users)
    conn.commit()
    conn.close()

init_db()

# --- 3. ENGINE MANTIĞI ---
def execute_action(master_id, role, action_id):
    # Puanı merkezi registry'den al
    points = ROLE_REGISTRY[role]["Actions"].get(action_id, 0)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Base_Points) VALUES (?, ?, ?, ?, ?)", 
                   (master_id, action_id, now, "Processed", points))
    conn.commit()
    conn.close()
    return "Processed", points

# --- 4. DASHBOARD ---
st.title("🌐 Buddy Rewards - Ecosystem Engine")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚖️ Registry", "👥 Ecosystem", "🏆 Fairness", "🔔 Privacy", "⚙️ Engine"])

with tab1:
    st.header("Role & Action Registry")
    st.write("Sistemin tüm kuralları ve puanları buradan yönetilir:")
    st.json(ROLE_REGISTRY) # Merkezi sözlüğü burada görebilirsin

with tab2:
    st.header("Ecosystem Actors (20 Users)")
    st.dataframe(pd.read_sql_query("SELECT * FROM Global_Users", sqlite3.connect(DB_FILE)), use_container_width=True)

with tab3:
    st.header("Fairness Engine")
    df = pd.read_sql_query("SELECT Nationality, Labor_Cluster, COUNT(*) as Count FROM Global_Users GROUP BY Nationality, Labor_Cluster", sqlite3.connect(DB_FILE))
    st.dataframe(df, use_container_width=True)

with tab4:
    st.header("Privacy Layer")
    u = st.selectbox("Kullanıcı Seç:", pd.read_sql_query("SELECT Master_ID FROM Global_Users", sqlite3.connect(DB_FILE))['Master_ID'])
    if st.button("Ödül Duyurusu Test"):
        user = pd.read_sql_query(f"SELECT * FROM Global_Users WHERE Master_ID='{u}'", sqlite3.connect(DB_FILE)).iloc[0]
        st.write(f"🎉 {'Görünür İsim: ' + user['Name'] if user['Consent_Given'] else 'Anonim (A ' + user['Role'] + ')'} ödül kazandı!")

with tab5:
    st.header("Engine Simulation")
    user_row = st.selectbox("Aktör Seç:", pd.read_sql_query("SELECT * FROM Global_Users", sqlite3.connect(DB_FILE))['Master_ID'])
    
    # Kullanıcının rolüne göre sadece onun yapabileceği eylemleri göster
    user_role = pd.read_sql_query(f"SELECT Role FROM Global_Users WHERE Master_ID='{user_row}'", sqlite3.connect(DB_FILE)).iloc[0]['Role']
    act_s = st.selectbox("Action:", list(ROLE_REGISTRY[user_role]["Actions"].keys()))
    
    if st.button("🚀 Execute Action"):
        s, p = execute_action(user_row, user_role, act_s)
        st.write(f"Motor Kararı: **{s}** | Puan: {p}")
        
    if st.button("🔍 View Logs"):
        st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_Timestamp DESC", sqlite3.connect(DB_FILE)), use_container_width=True)
