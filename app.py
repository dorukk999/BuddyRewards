import streamlit as st
import sqlite3
import pandas as pd
import datetime

# --- YAPI VE SAYFA AYARLARI ---
st.set_page_config(page_title="Buddy Rewards - Ultimate Engine", layout="wide")
DB_FILE = 'buddy_rewards_ultimate.db'

# --- 1. MERKEZİ ROL, YETENEK VE SOĞUMA SÜRESİ TANIMLARI ---
ROLE_REGISTRY = {
    "Worker": {"Actions": {"WORKER_VIDEO_WATCH": 5, "WORKER_QUIZ_ATTEMPT": 5, "WORKER_REFERRAL": 10}, "Category": "Engagement"},
    "Supplier": {"Actions": {"PROFILE": 5, "QUOTE": 10, "FULFILLMENT": 40}, "Category": "Commerce"},
    "Contractor": {"Actions": {"POST_REQ": 20, "VALIDATE": 40}, "Category": "Demand"},
    "Transporter": {"Actions": {"RETURN_TRIP": 15, "MULTI_PICKUP": 20, "DELIVERY": 40}, "Category": "Logistics"},
    "Captain": {"Actions": {"VERIFY_SIGNUP": 2, "ACTIVE_CLUSTER": 25}, "Category": "Growth"},
    "Champion": {"Actions": {"DEMAND_CREATED": 20, "CLOSURE": 50}, "Category": "Marketplace"}
}

ACTION_COOLDOWNS = {
    "WORKER_VIDEO_WATCH": 1440, # 24 saat (dakika)
    "WORKER_QUIZ_ATTEMPT": 1440,
    "WORKER_REFERRAL": 0,
    "PROFILE": 0, "QUOTE": 60, "FULFILLMENT": 0,
    "POST_REQ": 30, "VALIDATE": 0,
    "RETURN_TRIP": 120, "MULTI_PICKUP": 60, "DELIVERY": 0,
    "VERIFY_SIGNUP": 0, "ACTIVE_CLUSTER": 1440,
    "DEMAND_CREATED": 60, "CLOSURE": 0
}

MEGA_TARGETS = {
    'WORKER_VIDEO_WATCH': 180,
    'WORKER_QUIZ_ATTEMPT': 180,
    'WORKER_REFERRAL': 150
}

# --- 2. VERİ TABANI BAŞLATMA ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Core Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Role TEXT, Location TEXT, Nationality TEXT, 
        Labor_Cluster TEXT, Consent_Given BOOLEAN, Has_Subscription BOOLEAN, Has_Certification BOOLEAN)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Action_ID TEXT, 
        Event_Timestamp DATETIME, Process_Status TEXT, Earned_Points INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Integrity_Profiles (
        Master_ID TEXT PRIMARY KEY, Integrity_Score INTEGER DEFAULT 100, Action_Status TEXT DEFAULT 'Normal')''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Propagation_Logs (
        Propagation_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Shared_Item_ID TEXT, 
        Current_Stage TEXT, Points_Earned INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Qualified_Users (
        Master_ID TEXT PRIMARY KEY, Total_Score REAL, Rollover_Bonus REAL DEFAULT 0)''')

    # Tohum Veri (Seed Data)
    cursor.execute("SELECT COUNT(*) FROM Global_Users")
    if cursor.fetchone()[0] == 0:
        roles_list = list(ROLE_REGISTRY.keys())
        nationalities = ['India', 'Egypt', 'Philippines', 'Turkey']
        clusters = ['Camp-A', 'Camp-B', 'Camp-C']
        
        for i in range(1, 21):
            mid = f'ID-{i}'
            role = roles_list[i % len(roles_list)]
            nat = nationalities[i % len(nationalities)]
            cluster = clusters[i % len(clusters)]
            sub = i % 2 == 0
            cert = i % 3 == 0
            
            cursor.execute("INSERT INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (mid, f'User-{i}', role, 'Dubai', nat, cluster, 1, sub, cert))
            cursor.execute("INSERT INTO Integrity_Profiles (Master_ID) VALUES (?)", (mid,))
            cursor.execute("INSERT INTO Monthly_Qualified_Users VALUES (?, ?, ?)", (mid, 50 + (i*2), i%5 * 5))
            
        conn.commit()
    conn.close()

init_db()

# --- 3. CORE ENGINE FONKSİYONLARI ---

# Eksik 1: Bekleme Süresi (Cooldown) ve Asenkron İşlem Yönetimi
def execute_action(master_id, action_id, base_points):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    cooldown = ACTION_COOLDOWNS.get(action_id, 0)
    
    # Cooldown Kontrolü
    cursor.execute("""
        SELECT COUNT(*) FROM Event_Stream_Logs 
        WHERE Master_ID = ? AND Action_ID = ? AND Process_Status = 'Processed'
        AND Event_Timestamp >= datetime(?, '-' || ? || ' minutes')
    """, (master_id, action_id, now, cooldown))
    
    recent_actions = cursor.fetchone()[0]
    
    if recent_actions > 0:
        status = 'Blocked' # Cooldown ihlali
        points = 0
    else:
        status = 'Processed'
        points = base_points
        
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points) VALUES (?, ?, ?, ?, ?)", 
                   (master_id, action_id, now, status, points))
    conn.commit()
    conn.close()
    return status, points

# Eksik 2: Dinamik Puan Ağırlıklandırma
def get_normalized_weights(has_sub, has_cert):
    base_weights = {"Marketplace": 30, "Referral": 20, "Habit": 15, "Subscription": 20, "Certification": 15}
    active_weights = {k: base_weights[k] for k in ["Marketplace", "Referral", "Habit"]}
    
    if has_sub: active_weights["Subscription"] = base_weights["Subscription"]
    if has_cert: active_weights["Certification"] = base_weights["Certification"]
        
    total = sum(active_weights.values())
    return {k: round((v / total) * 100, 2) for k, v in active_weights.items()}

# Eksik 5: Yayılım Zinciri (Propagation)
def trigger_propagation(master_id, item_id, stage):
    matrix = {'SHARE': 2, 'OPEN': 5, 'ENGAGE': 10, 'FULFILL': 50}
    pts = matrix.get(stage, 0)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Propagation_Logs (Master_ID, Shared_Item_ID, Current_Stage, Points_Earned) VALUES (?, ?, ?, ?)", 
                   (master_id, item_id, stage, pts))
    conn.commit()
    conn.close()
    return pts

# Eksik 6: Güvenlik ve Dürüstlük (Integrity)
def flag_user(master_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT Integrity_Score FROM Integrity_Profiles WHERE Master_ID = ?", (master_id,))
    score = cursor.fetchone()[0]
    
    new_score = max(0, score - 15) # Her bayrak -15 puan
    status = 'Normal' if new_score >= 80 else 'Warning' if new_score >= 60 else 'Review' if new_score >= 40 else 'Block'
    
    cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ? WHERE Master_ID = ?", (new_score, status, master_id))
    conn.commit()
    conn.close()
    return new_score, status

# --- 4. STREAMLIT DASHBOARD ARAYÜZÜ ---
st.title("🌐 Buddy Rewards - Ultimate Ecosystem Engine")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚙️ Engine Setup", "👥 Users & Integrity", "🚀 Action Playground", "🏆 Mega & Fairness", "📜 Logs"])

with tab1:
    st.header("Sistem Dinamikleri")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Action Registry & Limits")
        st.json(ROLE_REGISTRY)
    with c2:
        st.subheader("Cooldown Matrix (Minutes)")
        st.json(ACTION_COOLDOWNS)

with tab2:
    st.header("Ecosystem Actors & Security")
    df_users = pd.read_sql_query("""
        SELECT u.Master_ID, u.Role, u.Nationality, u.Has_Subscription, u.Has_Certification, i.Integrity_Score, i.Action_Status 
        FROM Global_Users u JOIN Integrity_Profiles i ON u.Master_ID = i.Master_ID
    """, sqlite3.connect(DB_FILE))
    
    def color_status(val):
        color = 'green' if val == 'Normal' else 'orange' if val == 'Warning' else 'red'
        return f'color: {color}; font-weight: bold'
        
    st.dataframe(df_users.style.map(color_status, subset=['Action_Status']), use_container_width=True)

with tab3:
    st.header("Aksiyon ve Simülasyon Motoru")
    user_id = st.selectbox("Simüle Edilecek Aktör Seç:", df_users['Master_ID'].tolist())
    user_info = pd.read_sql_query(f"SELECT * FROM Global_Users WHERE Master_ID='{user_id}'", sqlite3.connect(DB_FILE)).iloc[0]
    
    st.markdown(f"**Aktif Rol:** {user_info['Role']} | **Abonelik:** {user_info['Has_Subscription']} | **Sertifika:** {user_info['Has_Certification']}")
    
    # Eksik 2 Testi
    st.info(f"Dinamik Puan Ağırlığı: {get_normalized_weights(user_info['Has_Subscription'], user_info['Has_Certification'])}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("1. Standart Aksiyon")
        available_actions = list(ROLE_REGISTRY[user_info['Role']]["Actions"].keys())
        act = st.selectbox("Eylem:", available_actions)
        if st.button("Çalıştır"):
            pts = ROLE_REGISTRY[user_info['Role']]["Actions"][act]
            status, earned = execute_action(user_id, act, pts)
            if status == 'Processed':
                st.success(f"Başarılı! {earned} Puan eklendi.")
            else:
                st.error(f"Engellendi: Cooldown süresi dolmadı.")
                
    with col2:
        st.subheader("2. Yayılım (Propagation)")
        prop_stage = st.selectbox("Yayılım Aşaması:", ["SHARE", "OPEN", "ENGAGE", "FULFILL"])
        if st.button("Zinciri Tetikle"):
            earned = trigger_propagation(user_id, "REQ-101", prop_stage)
            st.success(f"Yayılım Başarılı: +{earned} Puan")
            
    with col3:
        st.subheader("3. Dürüstlük (Integrity)")
        if st.button("Şüpheli İşlem Bildir (Flag)"):
            n_score, n_status = flag_user(user_id)
            st.warning(f"Kullanıcı Flaglendi! Yeni Puan: {n_score} | Durum: {n_status}")

with tab4:
    st.header("Ödül Kalifikasyonu ve Adil Seçim Motoru")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Eksik 3: Mega Ödül İlerlemesi")
        mega_user = st.selectbox("İşçi Seç:", df_users[df_users['Role'] == 'Worker']['Master_ID'].tolist())
        if mega_user:
            for action, target in MEGA_TARGETS.items():
                cur = sqlite3.connect(DB_FILE).cursor()
                cur.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID=? AND Action_ID=? AND Process_Status='Processed'", (mega_user, action))
                count = cur.fetchone()[0]
                st.metric(action, f"{count} / {target}")
                st.progress(min(count/target, 1.0))
                
    with c2:
        st.subheader("Eksik 4: Aylık Adil Seçim (Fairness)")
        t_cap = st.slider("Toplam Kazanan Limiti:", 1, 20, 5)
        n_cap = st.slider("Aynı Uyruk Limiti:", 1, 10, 2)
        c_cap = st.slider("Aynı Kamp Limiti:", 1, 10, 2)
        
        if st.button("Motoru Çalıştır"):
            df_monthly = pd.read_sql_query("""
                SELECT u.Master_ID, u.Nationality, u.Labor_Cluster, m.Total_Score, m.Rollover_Bonus,
                       (m.Total_Score + m.Rollover_Bonus) as Final_Score
                FROM Monthly_Qualified_Users m
                JOIN Global_Users u ON m.Master_ID = u.Master_ID
                ORDER BY Final_Score DESC
            """, sqlite3.connect(DB_FILE))
            
            winners = []
            nat_count = {}
            cluster_count = {}
            
            for _, row in df_monthly.iterrows():
                if len(winners) >= t_cap: break
                nat, cluster = row['Nationality'], row['Labor_Cluster']
                
                if nat_count.get(nat, 0) < n_cap and cluster_count.get(cluster, 0) < c_cap:
                    row['Status'] = '✅ Seçildi'
                    winners.append(row)
                    nat_count[nat] = nat_count.get(nat, 0) + 1
                    cluster_count[cluster] = cluster_count.get(cluster, 0) + 1
                else:
                    row['Status'] = '❌ Elendi (Adalet Limiti)'
                    winners.append(row)
            
            st.dataframe(pd.DataFrame(winners)[['Master_ID', 'Nationality', 'Labor_Cluster', 'Final_Score', 'Status']], use_container_width=True)

with tab5:
    st.header("Sistem Logları")
    log_type = st.radio("Log Tipi:", ["Event Stream", "Propagation Log"])
    if log_type == "Event Stream":
        st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_ID DESC LIMIT 50", sqlite3.connect(DB_FILE)), use_container_width=True)
    else:
        st.dataframe(pd.read_sql_query("SELECT * FROM Propagation_Logs ORDER BY Propagation_ID DESC LIMIT 50", sqlite3.connect(DB_FILE)), use_container_width=True)
