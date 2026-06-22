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
UNIVERSAL_ACTION_REGISTRY = [
    ("Worker", "WORKER_VIDEO_WATCH", "Retention", 5, 1440, 0, True, 30),
    ("Worker", "WORKER_QUIZ_ATTEMPT", "Retention", 5, 1440, 0, True, 30),
    ("Worker", "WORKER_REFERRAL", "Growth", 10, 0, +2, True, 50),
    ("Worker", "SUPPLIER_ADDED", "Growth", 20, 60, +5, True, 10),      
    ("Worker", "FULFILL_VALIDATED", "Trust", 40, 0, +10, True, 20),    
    ("Worker", "BUDDY_HELP", "Trigger", 10, 120, +5, True, 10),        
    
    ("Supplier", "PROFILE", "Trigger", 5, 0, +1, False, 5),
    ("Supplier", "QUOTE", "Response", 10, 60, +2, False, 50),
    ("Supplier", "FULFILLMENT", "Completion", 40, 0, +10, False, 100),
    
    ("Contractor", "POST_REQ", "Trigger", 20, 30, 0, False, 50),
    ("Contractor", "VALIDATE", "Trust", 40, 0, +15, False, 100),
    
    ("Transporter", "RETURN_TRIP", "Propagation", 15, 120, +5, False, 30),
    ("Transporter", "MULTI_PICKUP", "Propagation", 20, 60, +5, False, 30),
    ("Transporter", "DELIVERY", "Completion", 40, 0, +10, False, 50),
    
  # Mevcut Captain aksiyonları
    ("Captain", "VERIFY_SIGNUP", "Growth", 2, 0, +2, False, 100),
    ("Captain", "ACTIVE_CLUSTER", "Trust", 25, 1440, +10, False, 5),
    
    # EKSİK OLAN YENİ CAPTAIN AKSİYONLARI
    ("Captain", "USER_ACTIVE", "Retention", 10, 0, +2, False, 100),
    ("Captain", "WORKER_RETAINED", "Retention", 15, 0, +5, False, 100),
    ("Captain", "HIGH_RETENTION_CLUSTER", "Trust", 40, 1440, +15, False, 1),
    ("Captain", "DAILY_TASK_ACTIVATION", "Retention", 5, 0, +1, False, 20),
    ("Captain", "SESSION_COMPLETED", "Community", 20, 1440, +5, False, 4),
    ("Captain", "INACTIVE_REACTIVATED", "Retention", 10, 0, +3, False, 20),
    ("Captain", "REFERRAL_RETAINED", "Growth", 15, 0, +4, False, 20),
    ("Captain", "CAMP_CHALLENGE", "Community", 25, 1440, +5, False, 4),
    
    ("Champion", "DEMAND_CREATED", "Trigger", 20, 60, +5, False, 50),
    ("Champion", "CLOSURE", "Completion", 50, 0, +20, False, 50)
]

# --- POINT 2: MEGA REWARD TARGETS ---
MEGA_TARGETS = {
    'WORKER_VIDEO_WATCH': 180,
    'WORKER_QUIZ_ATTEMPT': 180,
    'WORKER_REFERRAL': 150,
    'SUPPLIER_ADDED': 50,         
    'FULFILL_VALIDATED': 10,      
    'BUDDY_HELP': 12              
}

# --- DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # YENİLİK 1: Role sütunu yerine Primary_Role ve Secondary_Roles eklendi
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Primary_Role TEXT, Secondary_Roles TEXT, Location TEXT, Nationality TEXT, 
        Labor_Cluster TEXT, Consent_Given BOOLEAN, Has_Subscription BOOLEAN, Has_Certification BOOLEAN,
        EID TEXT, Phone TEXT, Device_Fingerprint TEXT, EID_Verified BOOLEAN, 
        Join_Date DATETIME, Continuous_Paid_Months INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Action_Registry (
        Action_ID TEXT PRIMARY KEY, Role TEXT, Category TEXT, Base_Points INTEGER, Cooldown INTEGER, 
        Integrity_Impact INTEGER, Mega_Eligible BOOLEAN, Monthly_Cap INTEGER)''')
        
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
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Past_Winners (
        Win_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Win_Month INTEGER)''')

    # YENİLİK 2: Bağımsız Cüzdanlar (Ledgers) Tablosu Eklendi
    cursor.execute('''CREATE TABLE IF NOT EXISTS Reward_Ledgers (
        Ledger_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Master_ID TEXT,
        Role_Ledger TEXT,
        Pending_Points INTEGER DEFAULT 0,
        Settled_Points INTEGER DEFAULT 0,
        Reversed_Points INTEGER DEFAULT 0)''')

    # Seed Data
    cursor.execute("SELECT COUNT(*) FROM Global_Users")
    if cursor.fetchone()[0] == 0:
        for act in UNIVERSAL_ACTION_REGISTRY:
            cursor.execute("INSERT INTO Action_Registry VALUES (?, ?, ?, ?, ?, ?, ?, ?)", act[1:2] + act[0:1] + act[2:])
            
        roles_list = list(set([x[0] for x in UNIVERSAL_ACTION_REGISTRY if x[0] not in ['Captain', 'Champion']]))
        nationalities = ['India', 'Egypt', 'Philippines', 'Turkey']
        clusters = ['Camp-A', 'Camp-B', 'Camp-C']
        
        for i in range(1, 31):
            mid = f'ID-{i}'
            
            # YENİLİK 3: Birincil ve İkincil Rol Ataması
            primary_role = 'Worker' if i <= 15 else roles_list[i % len(roles_list)]
            secondary_roles = ""
            if primary_role == 'Worker':
                if i % 3 == 0: secondary_roles = "Captain"
                elif i % 5 == 0: secondary_roles = "Champion"
                
            nat = nationalities[i % len(nationalities)]
            cluster = clusters[i % len(clusters)]
            sub = i % 2 == 0
            cert = i % 3 == 0
            consent = i % 4 != 0 
            
            join_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(10, 200))
            paid_months = random.randint(0, 8) if sub else 0
            
            cursor.execute("""INSERT INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (mid, f'User-{i}', primary_role, secondary_roles, 'Dubai', nat, cluster, consent, sub, cert,
                            f'EID789{i}', f'+9715012345{i:02d}', f'DEV-FP-{i}', True, join_date, paid_months))
            cursor.execute("INSERT INTO Integrity_Profiles (Master_ID) VALUES (?)", (mid,))
            cursor.execute("INSERT INTO Monthly_Qualified_Users VALUES (?, ?, ?)", (mid, 50 + (i*2), 0))
            
            # YENİLİK 4: Roller İçin Bağımsız Ledger Kayıtları
            cursor.execute("INSERT INTO Reward_Ledgers (Master_ID, Role_Ledger) VALUES (?, ?)", (mid, primary_role))
            if secondary_roles:
                cursor.execute("INSERT INTO Reward_Ledgers (Master_ID, Role_Ledger) VALUES (?, ?)", (mid, secondary_roles))
            
    conn.commit()
    conn.close()

init_db()

# --- CORE ENGINE FUNCTIONS ---

# YENİLİK 5: execute_action fonksiyonu artık hangi rolde (acting_role) aksiyon alındığını biliyor
def execute_action(master_id, acting_role, action_id, target_id=None):
    """Processes an action by verifying cooldown limits and dynamic integrity impact."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    
    cursor.execute("SELECT Base_Points, Cooldown, Integrity_Impact FROM Action_Registry WHERE Action_ID = ?", (action_id,))
    act_meta = cursor.fetchone()
    if not act_meta: return 'Failed', 0, ""
    base_points, cooldown, integrity_impact = act_meta
    
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
        
        # YENİLİK 6: Kazanılan puanlar doğrudan kullanıcının işlemi yaptığı role ait Ledger'a yazılıyor
        cursor.execute("""
            UPDATE Reward_Ledgers 
            SET Settled_Points = Settled_Points + ? 
            WHERE Master_ID = ? AND Role_Ledger = ?
        """, (points, master_id, acting_role))
        
        if integrity_impact != 0:
            cursor.execute("SELECT Integrity_Score FROM Integrity_Profiles WHERE Master_ID = ?", (master_id,))
            curr_score = cursor.fetchone()[0]
            new_score = min(100, max(0, curr_score + integrity_impact)) 
            act_status = 'Normal' if new_score >= 80 else 'Warning' if new_score >= 60 else 'Review' if new_score >= 40 else 'Block'
            cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ? WHERE Master_ID = ?", (new_score, act_status, master_id))
        
        cursor.execute("SELECT Name, Location, Consent_Given FROM Global_Users WHERE Master_ID = ?", (master_id,))
        u_info = cursor.fetchone()
        if u_info[2]: 
            msg_string = f"🎉 {u_info[0]} from {u_info[1]} unlocked a reward as {acting_role}! (+{points} pts)"
        else:
            msg_string = f"🎉 A user from {u_info[1]} unlocked a reward as {acting_role}! (+{points} pts)"

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
        st.subheader("Universal Action Registry")
        df_registry = pd.read_sql_query("SELECT * FROM Action_Registry", sqlite3.connect(DB_FILE))
        st.dataframe(df_registry, use_container_width=True)
    with c2:
        st.subheader("Global Engine Settings")
        st.session_state.rollover_mode = st.toggle("ROLLOVER_MODE", st.session_state.rollover_mode)
        st.metric("Current Simulation Month", st.session_state.current_simulation_month)

with tab2:
    st.header("Ecosystem Actors & Security")
    df_users = pd.read_sql_query("""
        SELECT u.Master_ID, u.Primary_Role, u.Secondary_Roles, u.Consent_Given, u.Continuous_Paid_Months, u.EID_Verified,
        i.Integrity_Score, i.Action_Status 
        FROM Global_Users u JOIN Integrity_Profiles i ON u.Master_ID = i.Master_ID
    """, sqlite3.connect(DB_FILE))
    
    def color_status(val):
        color = 'green' if val == 'Normal' else 'orange' if val == 'Warning' else 'red'
        return f'color: {color}; font-weight: bold'
        
    st.dataframe(df_users.style.map(color_status, subset=['Action_Status']), use_container_width=True)
    
    st.subheader("Duplicate Detection")
    c_eid = st.text_input("Enter EID to check:")
    if st.button("Check Network for Duplicates"):
        dups = mock_duplicate_check(c_eid, "", "")
        if len(dups) > 1: st.error(f"🚨 Duplicate detected across Master IDs: {dups}")
        else: st.success("Identity is clean.")

with tab3:
    st.header("Action and Simulation Engine")
    df_users_base = pd.read_sql_query("SELECT Master_ID, Primary_Role, Secondary_Roles, Has_Subscription, Has_Certification FROM Global_Users", sqlite3.connect(DB_FILE))
    user_id = st.selectbox("Select Actor to Simulate:", df_users_base['Master_ID'].tolist())
    user_info = df_users_base[df_users_base['Master_ID'] == user_id].iloc[0]
    
    st.info(f"Dynamic Point Weights: {get_normalized_weights(user_info['Has_Subscription'], user_info['Has_Certification'])}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Standard Action")
        
        # YENİLİK 7: Arayüzde kullanıcının sahip olduğu rollere göre Active Role seçimi eklendi
        available_roles = [user_info['Primary_Role']]
        if user_info['Secondary_Roles']:
            available_roles.extend([r.strip() for r in user_info['Secondary_Roles'].split(',')])
            
        acting_role = st.radio("Select Active Role for this Action:", available_roles, horizontal=True)
        st.markdown("---")
        
        # Listelenen aksiyonlar artık Acting Role'a göre dinamik filtreli
        available_actions = pd.read_sql_query(f"SELECT Action_ID FROM Action_Registry WHERE Role='{acting_role}'", sqlite3.connect(DB_FILE))['Action_ID'].tolist()
        
        if len(available_actions) > 0:
            act = st.selectbox("Action Type:", available_actions)
            t_id = st.text_input("Target User ID (Optional for Pair Cooldown):", placeholder="e.g. ID-5")
            
            if st.button("Execute Action"):
                status, earned, msg = execute_action(user_id, acting_role, act, t_id if t_id else None)
                if status == 'Processed':
                    st.success(msg)
                else:
                    st.error(status)
        else:
            st.warning(f"No actions configured for the {acting_role} role yet.")
                
    with col2:
        st.subheader("Bulk Simulation")
        st.caption("Aylık minimum limitleri test edebilmek için hızlı veri pompalar.")
        if st.button("Simulate Minimum Qualifications for Workers"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            workers = pd.read_sql_query("SELECT Master_ID FROM Global_Users WHERE Primary_Role='Worker'", conn)['Master_ID'].tolist()
            now = datetime.datetime.now()
            for w in workers[:5]: 
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
        st.subheader("Mega Reward Tracker")
        mega_user = st.selectbox("Select Worker:", df_users_base[df_users_base['Primary_Role'] == 'Worker']['Master_ID'].tolist())
        if mega_user:
            cur = sqlite3.connect(DB_FILE).cursor()
            
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
        st.subheader("Monthly Fairness Selection")
        t_cap = st.slider("Total Winner Limit (Soft Cap):", 1, 10, 3)
        
        if st.button("Run Month End Engine"):
            conn = sqlite3.connect(DB_FILE)
            curr_month = st.session_state.current_simulation_month
            
            df_qualified = pd.read_sql_query("""
                SELECT u.Master_ID, u.Nationality, u.Labor_Cluster, m.Total_Score, m.Rollover_Bonus,
                       (m.Total_Score + m.Rollover_Bonus) as Final_Score
                FROM Monthly_Qualified_Users m
                JOIN Global_Users u ON m.Master_ID = u.Master_ID
                WHERE u.Primary_Role = 'Worker'
            """, conn)
            
            df_past = pd.read_sql_query("SELECT * FROM Past_Winners", conn)
            last_month_winners = df_past[df_past['Win_Month'] == curr_month - 1]['Master_ID'].tolist()
            older_winners = df_past[df_past['Win_Month'] < curr_month - 1]['Master_ID'].tolist()
            
            winners = []
            losers = []
            repeat_count = 0
            max_repeats = int(t_cap * 0.20) 
            
            df_qualified = df_qualified.sort_values(by='Final_Score', ascending=False)
            
            for _, row in df_qualified.iterrows():
                mid = row['Master_ID']
                
                if mid in last_month_winners:
                    row['Selection_Status'] = '❌ Excluded (Won Last Month)'
                    losers.append(row)
                    continue
                    
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
                    conn.execute("INSERT INTO Past_Winners (Master_ID, Win_Month) VALUES (?, ?)", (mid, curr_month))
                    conn.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = 0 WHERE Master_ID = ?", (mid,))
                else:
                    row['Selection_Status'] = '🔄 Rolled Over (Cap Reached)'
                    losers.append(row)
                    if st.session_state.rollover_mode:
                        conn.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = Rollover_Bonus + 5 WHERE Master_ID = ?", (mid,))
                        
            conn.commit()
            conn.close()
            
            st.session_state.current_simulation_month += 1
            st.success(f"Month {curr_month} completed! Advancing to Month {st.session_state.current_simulation_month}.")
            st.dataframe(pd.DataFrame(winners + losers)[['Master_ID', 'Nationality', 'Final_Score', 'Selection_Status']], use_container_width=True)

with tab5:
    st.header("System Logs")
    log_type = st.radio("Select Log Type:", ["Event Stream", "Past Winners History", "Reward Ledgers"])
    if log_type == "Event Stream":
        st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_ID DESC LIMIT 50", sqlite3.connect(DB_FILE)), use_container_width=True)
    elif log_type == "Past Winners History":
        st.dataframe(pd.read_sql_query("SELECT * FROM Past_Winners ORDER BY Win_ID DESC", sqlite3.connect(DB_FILE)), use_container_width=True)
    else:
        # YENİLİK 8: Ledger cüzdanlarının incelenebilmesi için tablo Loglar sekmesine eklendi
        st.dataframe(pd.read_sql_query("SELECT * FROM Reward_Ledgers", sqlite3.connect(DB_FILE)), use_container_width=True)
