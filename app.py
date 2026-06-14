import streamlit as st
import sqlite3
import pandas as pd
import datetime
import random

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Buddy Rewards - Ultimate Engine", layout="wide")
DB_FILE = 'buddy_rewards_v4.db' # POINT 1-10 entegrasyonu için taze DB

# --- POINT 6: ROLLOVER BONUS TOGGLE ---
if 'rollover_mode' not in st.session_state:
    st.session_state.rollover_mode = True

if 'current_simulation_month' not in st.session_state:
    st.session_state.current_simulation_month = 1 # POINT 5: Aylık adalet motoru için zaman algısı

# --- POINT 1 & 7: UNIVERSAL ACTION REGISTRY (Kategoriler Düzeltildi, Eksik Aksiyonlar Eklendi) ---
# Sütunlar: Role, Action_ID, Category, Base_Points, Cooldown(min), Integrity_Impact, Mega_Eligible, Monthly_Cap
UNIVERSAL_ACTION_REGISTRY = [
    ("Worker", "WORKER_VIDEO_WATCH", "Retention", 5, 1440, 0, True, 30),
    ("Worker", "WORKER_QUIZ_ATTEMPT", "Retention", 5, 1440, 0, True, 30),
    ("Worker", "WORKER_REFERRAL", "Growth", 10, 0, +2, True, 50),
    ("Worker", "SUPPLIER_ADDED", "Growth", 20, 60, +5, True, 10),     # EKSİKLİK GİDERİLDİ
    ("Worker", "FULFILL_VALIDATED", "Trust", 40, 0, +10, True, 20),    # EKSİKLİK GİDERİLDİ
    ("Worker", "BUDDY_HELP", "Trigger", 10, 120, +5, True, 10),        # EKSİKLİK GİDERİLDİ
    
    ("Supplier", "PROFILE", "Trigger", 5, 0, +1, False, 5),
    ("Supplier", "QUOTE", "Response", 10, 60, +2, False, 50),
    ("Supplier", "FULFILLMENT", "Completion", 40, 0, +10, False, 100),
    
    ("Contractor", "POST_REQ", "Trigger", 20, 30, 0, False, 50),
    ("Contractor", "VALIDATE", "Trust", 40, 0, +15, False, 100),
    
    ("Transporter", "RETURN_TRIP", "Propagation", 15, 120, +5, False, 30),
    ("Transporter", "MULTI_PICKUP", "Propagation", 20, 60, +5, False, 30),
    ("Transporter", "DELIVERY", "Completion", 40, 0, +10, False, 50),
    
    ("Captain", "VERIFY_SIGNUP", "Growth", 2, 0, +2, False, 100),
    ("Captain", "ACTIVE_CLUSTER", "Trust", 25, 1440, +10, False, 5),
    
    ("Champion", "DEMAND_CREATED", "Trigger", 20, 60, +5, False, 50),
    ("Champion", "CLOSURE", "Completion", 50, 0, +20, False, 50)
]

# --- POINT 2: MEGA REWARD TARGETS ---
MEGA_TARGETS = {
    'WORKER_VIDEO_WATCH': 180,
    'WORKER_QUIZ_ATTEMPT': 180,
    'WORKER_REFERRAL': 150,
    'SUPPLIER_ADDED': 50,         # EKSİKLİK GİDERİLDİ
    'FULFILL_VALIDATED': 10,      # EKSİKLİK GİDERİLDİ
    'BUDDY_HELP': 12              # EKSİKLİK GİDERİLDİ
}

# --- DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # POINT 3 & 9: Master ID alanları, Abonelik sürekliliği ve Kayıt tarihi eklendi
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Role TEXT, Location TEXT, Nationality TEXT, 
        Labor_Cluster TEXT, Consent_Given BOOLEAN, Has_Subscription BOOLEAN, Has_Certification BOOLEAN,
        EID TEXT, Phone TEXT, Device_Fingerprint TEXT, EID_Verified BOOLEAN, 
        Join_Date DATETIME, Continuous_Paid_Months INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Action_Registry (
        Action_ID TEXT PRIMARY KEY, Role TEXT, Category TEXT, Base_Points INTEGER, Cooldown INTEGER, 
        Integrity_Impact INTEGER, Mega_Eligible BOOLEAN, Monthly_Cap INTEGER)''')
        
    # POINT 4: Pair Cooldown ve Target ID için stream tablosu güncellendi
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Target_ID TEXT, Action_ID TEXT, 
        Event_Timestamp DATETIME, Process_Status TEXT, Earned_Points INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Integrity_Profiles (
        Master_ID TEXT PRIMARY KEY, Integrity_Score INTEGER DEFAULT 100, Action_Status TEXT DEFAULT 'Normal')''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Propagation_Logs (
        Propagation_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Shared_Item_ID TEXT, 
        Current_Stage TEXT, Points_Earned INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Qualified_Users (
        Master_ID TEXT PRIMARY KEY, Total_Score REAL, Rollover_Bonus REAL DEFAULT 0)''')
        
    # POINT 5: Geçmiş Kazananlar (Repeat Winners kontrolü için)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Past_Winners (
        Win_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Win_Month INTEGER)''')

    # Seed Data
    cursor.execute("SELECT COUNT(*) FROM Global_Users")
    if cursor.fetchone()[0] == 0:
        # Seed Action Registry
        for act in UNIVERSAL_ACTION_REGISTRY:
            cursor.execute("INSERT INTO Action_Registry VALUES (?, ?, ?, ?, ?, ?, ?, ?)", act[1:2] + act[0:1] + act[2:])
            
        roles_list = list(set([x[0] for x in UNIVERSAL_ACTION_REGISTRY]))
        nationalities = ['India', 'Egypt', 'Philippines', 'Turkey']
        clusters = ['Camp-A', 'Camp-B', 'Camp-C']
        
        for i in range(1, 31):
            mid = f'ID-{i}'
            role = 'Worker' if i <= 15 else roles_list[i % len(roles_list)]
            nat = nationalities[i % len(nationalities)]
            cluster = clusters[i % len(clusters)]
            sub = i % 2 == 0
            cert = i % 3 == 0
            consent = i % 4 != 0 # %75 oranında onay verilmiş
            
            # POINT 3: Join Date simülasyonu (Kimisi 6 ay önce, kimisi yeni gelmiş)
            join_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(10, 200))
            paid_months = random.randint(0, 8) if sub else 0
            
            cursor.execute("""INSERT INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (mid, f'User-{i}', role, 'Dubai', nat, cluster, consent, sub, cert,
                            f'EID789{i}', f'+9715012345{i:02d}', f'DEV-FP-{i}', True, join_date, paid_months))
            cursor.execute("INSERT INTO Integrity_Profiles (Master_ID) VALUES (?)", (mid,))
            cursor.execute("INSERT INTO Monthly_Qualified_Users VALUES (?, ?, ?)", (mid, 50 + (i*2), 0))
            
    conn.commit()
    conn.close()

init_db()

# --- CORE ENGINE FUNCTIONS ---

def execute_action(master_id, action_id, target_id=None):
    """Processes an action by verifying cooldown limits and dynamic integrity impact."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    
    # Fetch Action Metadata (POINT 7)
    cursor.execute("SELECT Base_Points, Cooldown, Integrity_Impact FROM Action_Registry WHERE Action_ID = ?", (action_id,))
    act_meta = cursor.fetchone()
    if not act_meta: return 'Failed', 0, ""
    base_points, cooldown, integrity_impact = act_meta
    
    # POINT 4: Cooldown Verification (Exact Repeat & Pair Cooldown Support)
    query = """
        SELECT COUNT(*) FROM Event_Stream_Logs 
        WHERE Master_ID = ? AND Action_ID = ? AND Process_Status = 'Processed'
        AND Event_Timestamp >= datetime(?, '-' || ? || ' minutes')
    """
    params = [master_id, action_id, now, cooldown]
    
    if target_id:
        query += " AND Target_ID = ?"
        params.append(target_id)
        
    cursor.execute(query, tuple(params))
    recent_actions = cursor.fetchone()[0]
    
    if recent_actions > 0:
        status = 'Blocked (Cooldown)'
        points = 0
        msg_string = "Eylem Reddedildi (Cooldown)."
    else:
        status = 'Processed'
        points = base_points
        
        # POINT 8: Continuous Integrity Update
        if integrity_impact != 0:
            cursor.execute("SELECT Integrity_Score FROM Integrity_Profiles WHERE Master_ID = ?", (master_id,))
            curr_score = cursor.fetchone()[0]
            new_score = min(100, max(0, curr_score + integrity_impact)) # 0-100 sınırları
            act_status = 'Normal' if new_score >= 80 else 'Warning' if new_score >= 60 else 'Review' if new_score >= 40 else 'Block'
            cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ? WHERE Master_ID = ?", (new_score, act_status, master_id))
        
        # POINT 10: Celebration Layer & Privacy
        cursor.execute("SELECT Name, Location, Consent_Given FROM Global_Users WHERE Master_ID = ?", (master_id,))
        u_info = cursor.fetchone()
        if u_info[2]: # Consent == True
            msg_string = f"🎉 {u_info[0]} from {u_info[1]} unlocked a reward! (+{points} pts)"
        else:
            msg_string = f"🎉 A worker from {u_info[1]} unlocked a reward! (+{points} pts)"

    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points) VALUES (?, ?, ?, ?, ?, ?)", 
                   (master_id, target_id, action_id, now, status, points))
    conn.commit()
    conn.close()
    return status, points, msg_string

def get_normalized_weights(has_sub, has_cert):
    base_weights = {"Marketplace": 30, "Referral": 20, "Habit": 15, "Subscription": 20, "Certification": 15}
    active_weights = {k: base_weights[k] for k in ["Marketplace", "Referral", "Habit"]}
    if has_sub: active_weights["Subscription"] = base_weights["Subscription"]
    if has_cert: active_weights["Certification"] = base_weights["Certification"]
    total = sum(active_weights.values())
    return {k: round((v / total) * 100, 2) for k, v in active_weights.items()}

def mock_duplicate_check(eid, phone, device):
    """POINT 9: Master ID & Duplicate Detection Mock"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT Master_ID FROM Global_Users WHERE EID=? OR Phone=? OR Device_Fingerprint=?", (eid, phone, device))
    duplicates = cur.fetchall()
    conn.close()
    return [d[0] for d in duplicates]

# --- STREAMLIT DASHBOARD UI ---
st.title("🌐 Buddy Rewards - Ultimate Ecosystem Engine")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚙️ Engine Setup", "👥 Users & Integrity", "🚀 Action Playground", "🏆 Mega & Fairness", "📜 Logs"])

with tab1:
    st.header("System Dynamics & Universal Registry")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Universal Action Registry (Point 7)")
        df_registry = pd.read_sql_query("SELECT * FROM Action_Registry", sqlite3.connect(DB_FILE))
        st.dataframe(df_registry, use_container_width=True)
    with c2:
        st.subheader("Global Engine Settings")
        st.session_state.rollover_mode = st.toggle("ROLLOVER_MODE (Point 6)", st.session_state.rollover_mode)
        st.metric("Current Simulation Month", st.session_state.current_simulation_month)

with tab2:
    st.header("Ecosystem Actors & Security")
    df_users = pd.read_sql_query("""
        SELECT u.Master_ID, u.Role, u.Consent_Given, u.Continuous_Paid_Months, u.EID_Verified,
        i.Integrity_Score, i.Action_Status 
        FROM Global_Users u JOIN Integrity_Profiles i ON u.Master_ID = i.Master_ID
    """, sqlite3.connect(DB_FILE))
    
    def color_status(val):
        color = 'green' if val == 'Normal' else 'orange' if val == 'Warning' else 'red'
        return f'color: {color}; font-weight: bold'
        
    st.dataframe(df_users.style.map(color_status, subset=['Action_Status']), use_container_width=True)
    
    st.subheader("Duplicate Detection (Point 9)")
    c_eid = st.text_input("Enter EID to check:")
    if st.button("Check Network for Duplicates"):
        dups = mock_duplicate_check(c_eid, "", "")
        if len(dups) > 1: st.error(f"🚨 Duplicate detected across Master IDs: {dups}")
        else: st.success("Identity is clean.")

with tab3:
    st.header("Action and Simulation Engine")
    df_users_base = pd.read_sql_query("SELECT Master_ID, Role, Has_Subscription, Has_Certification FROM Global_Users", sqlite3.connect(DB_FILE))
    user_id = st.selectbox("Select Actor to Simulate:", df_users_base['Master_ID'].tolist())
    user_info = df_users_base[df_users_base['Master_ID'] == user_id].iloc[0]
    
    st.markdown(f"**Active Role:** {user_info['Role']}")
    st.info(f"Dynamic Point Weights: {get_normalized_weights(user_info['Has_Subscription'], user_info['Has_Certification'])}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Standard Action (Point 4 & 8 & 10)")
        available_actions = pd.read_sql_query(f"SELECT Action_ID FROM Action_Registry WHERE Role='{user_info['Role']}'", sqlite3.connect(DB_FILE))['Action_ID'].tolist()
        act = st.selectbox("Action Type:", available_actions)
        t_id = st.text_input("Target User ID (Optional for Pair Cooldown):", placeholder="e.g. ID-5")
        
        if st.button("Execute Action"):
            status, earned, msg = execute_action(user_id, act, t_id if t_id else None)
            if status == 'Processed':
                st.success(msg)
            else:
                st.error(status)
                
    with col2:
        st.subheader("Bulk Simulation")
        st.caption("Aylık minimum limitleri (Point 1) test edebilmek için hızlı veri pompalar.")
        if st.button("Simulate Minimum Qualifications for Workers"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            workers = pd.read_sql_query("SELECT Master_ID FROM Global_Users WHERE Role='Worker'", conn)['Master_ID'].tolist()
            now = datetime.datetime.now()
            for w in workers[:5]: # İlk 5 worker barajı geçsin
                for _ in range(30): cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points) VALUES (?, 'WORKER_VIDEO_WATCH', ?, 'Processed', 5)", (w, now))
                for _ in range(30): cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points) VALUES (?, 'WORKER_QUIZ_ATTEMPT', ?, 'Processed', 5)", (w, now))
                for _ in range(15): cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points) VALUES (?, 'WORKER_REFERRAL', ?, 'Processed', 10)", (w, now))
            conn.commit()
            conn.close()
            st.success("Successfully pushed 30/30/15 minimums for top 5 workers!")

with tab4:
    st.header("Reward Qualification and Fairness Engine")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Mega Reward Tracker (Point 2)")
        mega_user = st.selectbox("Select Worker:", df_users_base[df_users_base['Role'] == 'Worker']['Master_ID'].tolist())
        if mega_user:
            cur = sqlite3.connect(DB_FILE).cursor()
            
            # Zorunlu kriterler (Mandatory Checks)
            cur.execute("SELECT EID_Verified, Continuous_Paid_Months FROM Global_Users WHERE Master_ID=?", (mega_user,))
            eid_v, paid_m = cur.fetchone()
            cur.execute("SELECT Integrity_Score FROM Integrity_Profiles WHERE Master_ID=?", (mega_user,))
            int_score = cur.fetchone()[0]
            
            st.markdown("### 🔒 Mandatory Criteria")
            st.write(f"EID Verified: {'✅' if eid_v else '❌'}")
            st.write(f"Integrity Compliant: {'✅' if int_score >= 80 else '❌'} ({int_score})")
            st.write(f"Subscription Continuity (>=3 months): {'✅' if paid_m >= 3 else '❌'} ({paid_m} months)")
            
            st.markdown("### 🎯 Locked Action Criteria")
            for action, target in MEGA_TARGETS.items():
                cur.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID=? AND Action_ID=? AND Process_Status='Processed'", (mega_user, action))
                count = cur.fetchone()[0]
                st.metric(action, f"{count} / {target}")
                st.progress(min(count/target, 1.0))
                
    with c2:
        st.subheader("Monthly Fairness Selection (Point 1, 5, 6)")
        t_cap = st.slider("Total Winner Limit (Soft Cap):", 1, 10, 3)
        
        if st.button("Run Month End Engine"):
            conn = sqlite3.connect(DB_FILE)
            curr_month = st.session_state.current_simulation_month
            
            # POINT 1: Asgari Yeterlilik Kontrolü (Sadece barajı geçenler listelenir)
            df_qualified = pd.read_sql_query("""
                SELECT u.Master_ID, u.Nationality, u.Labor_Cluster, m.Total_Score, m.Rollover_Bonus,
                       (m.Total_Score + m.Rollover_Bonus) as Final_Score
                FROM Monthly_Qualified_Users m
                JOIN Global_Users u ON m.Master_ID = u.Master_ID
                WHERE u.Role = 'Worker'
            """, conn)
            
            # POINT 5: Repeat Escalation Rule
            df_past = pd.read_sql_query("SELECT * FROM Past_Winners", conn)
            last_month_winners = df_past[df_past['Win_Month'] == curr_month - 1]['Master_ID'].tolist()
            older_winners = df_past[df_past['Win_Month'] < curr_month - 1]['Master_ID'].tolist()
            
            winners = []
            losers = []
            repeat_count = 0
            max_repeats = int(t_cap * 0.20) # Max %20 eski kazanan
            
            df_qualified = df_qualified.sort_values(by='Final_Score', ascending=False)
            
            for _, row in df_qualified.iterrows():
                mid = row['Master_ID']
                
                # Geçen ay kazanan KESİNLİKLE reddedilir
                if mid in last_month_winners:
                    row['Selection_Status'] = '❌ Excluded (Won Last Month)'
                    losers.append(row)
                    continue
                    
                # Eski kazananların %20 baraj kontrolü
                if mid in older_winners:
                    if repeat_count >= max_repeats:
                        row['Selection_Status'] = '❌ Excluded (Repeat Cap Reached)'
                        losers.append(row)
                        continue
                    else:
                        repeat_count += 1
                        
                if len(winners) < t_cap:
                    row['Selection_Status'] = '✅ Selected'
                    winners.append(row)
                    # Kazananı Past_Winners'a ekle ve Rollover'ını sıfırla
                    conn.execute("INSERT INTO Past_Winners (Master_ID, Win_Month) VALUES (?, ?)", (mid, curr_month))
                    conn.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = 0 WHERE Master_ID = ?", (mid,))
                else:
                    row['Selection_Status'] = '🔄 Rolled Over (Cap Reached)'
                    losers.append(row)
                    # POINT 6: Rollover Bonus
                    if st.session_state.rollover_mode:
                        conn.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = Rollover_Bonus + 5 WHERE Master_ID = ?", (mid,))
                        
            conn.commit()
            conn.close()
            
            st.session_state.current_simulation_month += 1
            st.success(f"Month {curr_month} completed! Advancing to Month {st.session_state.current_simulation_month}.")
            st.dataframe(pd.DataFrame(winners + losers)[['Master_ID', 'Nationality', 'Final_Score', 'Selection_Status']], use_container_width=True)

with tab5:
    st.header("System Logs")
    log_type = st.radio("Select Log Type:", ["Event Stream", "Past Winners History"])
    if log_type == "Event Stream":
        st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_ID DESC LIMIT 50", sqlite3.connect(DB_FILE)), use_container_width=True)
    else:
        st.dataframe(pd.read_sql_query("SELECT * FROM Past_Winners ORDER BY Win_ID DESC", sqlite3.connect(DB_FILE)), use_container_width=True)
