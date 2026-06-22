import streamlit as st
import sqlite3
import pandas as pd
import datetime
import random

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Buddy Rewards - Ultimate Engine", layout="wide")
DB_FILE = 'buddy_rewards_v4.db' 

if 'rollover_mode' not in st.session_state:
    st.session_state.rollover_mode = True

if 'current_simulation_month' not in st.session_state:
    st.session_state.current_simulation_month = 1 

# --- UNIVERSAL ACTION REGISTRY ---
# Sütunlar: Role, Action_ID, Category, Base_Points, Cooldown(min), Integrity_Impact, Mega_Eligible, Monthly_Cap
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
    
    ("Captain", "VERIFY_SIGNUP", "Growth", 2, 0, +2, False, 100),
    ("Captain", "ACTIVE_CLUSTER", "Trust", 25, 1440, +10, False, 5),
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

MEGA_TARGETS = {
    'WORKER_VIDEO_WATCH': 180, 'WORKER_QUIZ_ATTEMPT': 180, 'WORKER_REFERRAL': 150,
    'SUPPLIER_ADDED': 50, 'FULFILL_VALIDATED': 10, 'BUDDY_HELP': 12              
}

REASON_CODES = [
    "APPROVED_CLEAN", "POD_INVALID", "ACTOR_FAULT", "DISPUTE_UPHELD", 
    "POST_SETTLEMENT_FRAUD", "PROOF_MISSING", "DUPLICATE_PROVIDER", "COLLUSION_SUSPECTED"
]

# --- DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Primary_Role TEXT, Secondary_Roles TEXT, Location TEXT, Nationality TEXT, 
        Labor_Cluster TEXT, Consent_Given BOOLEAN, Has_Subscription BOOLEAN, Has_Certification BOOLEAN,
        EID TEXT, Phone TEXT, Device_Fingerprint TEXT, EID_Verified BOOLEAN, 
        Join_Date DATETIME, Continuous_Paid_Months INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Action_Registry (
        Action_ID TEXT PRIMARY KEY, Role TEXT, Category TEXT, Base_Points INTEGER, Cooldown INTEGER, 
        Integrity_Impact INTEGER, Mega_Eligible BOOLEAN, Monthly_Cap INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Acting_Role TEXT, Target_ID TEXT, Action_ID TEXT, 
        Event_Timestamp DATETIME, Process_Status TEXT, Earned_Points INTEGER, Reason_Code TEXT DEFAULT '')''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Integrity_Profiles (
        Master_ID TEXT PRIMARY KEY, Integrity_Score INTEGER DEFAULT 100, Action_Status TEXT DEFAULT 'Normal')''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Reward_Ledgers (
        Ledger_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Role_Ledger TEXT,
        Pending_Points INTEGER DEFAULT 0, Settled_Points INTEGER DEFAULT 0, Reversed_Points INTEGER DEFAULT 0)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Qualified_Users (
        Master_ID TEXT PRIMARY KEY, Total_Score REAL, Rollover_Bonus REAL DEFAULT 0)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Past_Winners (
        Win_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Win_Month INTEGER)''')

    # YENİLİK 1: Zincir Atıf Tablosu (Event-Chain Attribution)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Marketplace_Attributions (
        Attribution_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Source_ID TEXT,
        Target_ID TEXT,
        Attribution_Type TEXT,
        Expiry_Date DATETIME)''')

    cursor.execute("SELECT COUNT(*) FROM Global_Users")
    if cursor.fetchone()[0] == 0:
        for act in UNIVERSAL_ACTION_REGISTRY:
            cursor.execute("INSERT INTO Action_Registry VALUES (?, ?, ?, ?, ?, ?, ?, ?)", act[1:2] + act[0:1] + act[2:])
            
        roles_list = list(set([x[0] for x in UNIVERSAL_ACTION_REGISTRY if x[0] not in ['Captain', 'Champion']]))
        nationalities = ['India', 'Egypt', 'Philippines', 'Turkey']
        clusters = ['Camp-A', 'Camp-B', 'Camp-C']
        
        for i in range(1, 31):
            mid = f'ID-{i}'
            primary_role = 'Worker' if i <= 15 else roles_list[i % len(roles_list)]
            secondary_roles = ""
            if primary_role == 'Worker':
                if i % 3 == 0: secondary_roles = "Captain"
                elif i % 5 == 0: secondary_roles = "Champion"
                
            nat = nationalities[i % len(nationalities)]
            cluster = clusters[i % len(clusters)]
            sub = i % 2 == 0
            cert = i % 3 == 0
            
            join_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(10, 200))
            paid_months = random.randint(0, 8) if sub else 0
            
            cursor.execute("""INSERT INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (mid, f'User-{i}', primary_role, secondary_roles, 'Dubai', nat, cluster, True, sub, cert,
                            f'EID789{i}', f'+9715012345{i:02d}', f'DEV-FP-{i}', True, join_date, paid_months))
            cursor.execute("INSERT INTO Integrity_Profiles (Master_ID) VALUES (?)", (mid,))
            
            cursor.execute("INSERT INTO Reward_Ledgers (Master_ID, Role_Ledger) VALUES (?, ?)", (mid, primary_role))
            if secondary_roles:
                cursor.execute("INSERT INTO Reward_Ledgers (Master_ID, Role_Ledger) VALUES (?, ?)", (mid, secondary_roles))
            
    conn.commit()
    conn.close()

init_db()

# --- CORE ENGINE FUNCTIONS ---

def execute_action(master_id, acting_role, action_id, target_id=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    current_month_str = now.strftime('%Y-%m')
    
    # YENİLİK 2: Base_Points ve Cooldown'un yanında Monthly_Cap değerini de çekiyoruz
    cursor.execute("SELECT Base_Points, Cooldown, Monthly_Cap FROM Action_Registry WHERE Action_ID = ?", (action_id,))
    act_meta = cursor.fetchone()
    if not act_meta: return 'Failed', 0, ""
    base_points, cooldown, monthly_cap = act_meta
    
    # KONTROL 1: Cooldown Kısıtı (Zaman/Spam Kontrolü)
    query_cooldown = """
        SELECT COUNT(*) FROM Event_Stream_Logs 
        WHERE Master_ID = ? AND Action_ID = ? AND Process_Status IN ('VALIDATING', 'SETTLED', 'DISPUTED', 'CAPPED')
        AND Event_Timestamp >= datetime(?, '-' || ? || ' minutes')
    """
    params_cd = [master_id, action_id, now, cooldown]
    if target_id:
        query_cooldown += " AND Target_ID = ?"
        params_cd.append(target_id)
        
    cursor.execute(query_cooldown, tuple(params_cd))
    recent_actions = cursor.fetchone()[0]
    
    if recent_actions > 0:
        conn.close()
        return 'BLOCKED (Cooldown)', 0, "Eylem Reddedildi (Zaman veya Çift Kayıt limitlerine takıldı)."

    # YENİLİK 3: Aylık Kota Kontrolü (Raw vs Rewarded)
    cursor.execute("""
        SELECT COUNT(*) FROM Event_Stream_Logs 
        WHERE Master_ID = ? AND Action_ID = ? AND strftime('%Y-%m', Event_Timestamp) = ?
        AND Process_Status IN ('VALIDATING', 'SETTLED', 'DISPUTED', 'CAPPED')
    """, (master_id, action_id, current_month_str))
    monthly_count = cursor.fetchone()[0]
    
    if monthly_count >= monthly_cap:
        status = 'CAPPED'
        points = 0
        msg_string = f"Aylık kota ({monthly_cap}) doldu. Eylem sisteme (0 puan) ile işlendi."
    else:
        status = 'VALIDATING'
        points = base_points
        
        cursor.execute("""
            UPDATE Reward_Ledgers 
            SET Pending_Points = Pending_Points + ? 
            WHERE Master_ID = ? AND Role_Ledger = ?
        """, (points, master_id, acting_role))
        
        msg_string = f"⏳ Eylem alındı. {points} puan {acting_role} cüzdanında 'VALIDATING' statüsünde bekliyor."

    # Eylemi loga yaz
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                   (master_id, acting_role, target_id, action_id, now, status, points, ""))
    
    # ---------------------------------------------------------
    # YENİLİK 4: OLAY ZİNCİRİ (EVENT-CHAIN CASCADE LOGIC)
    # ---------------------------------------------------------
    
    # ZİNCİR BAŞLATICI: Champion bir talep açarsa (DEMAND_CREATED) ve bir hedefi dürtüklediyse
    if action_id == 'DEMAND_CREATED' and acting_role == 'Champion' and target_id:
        expiry = now + datetime.timedelta(days=7) # 7 günlük atıf penceresi
        cursor.execute("INSERT INTO Marketplace_Attributions (Source_ID, Target_ID, Attribution_Type, Expiry_Date) VALUES (?, ?, ?, ?)", 
                       (master_id, target_id, 'CHAMPION_NUDGE', expiry))
        msg_string += f" 🔗 (Zincir Başladı: {target_id} hedefine 7 günlük takip aktifleştirildi.)"

    # ZİNCİR TAMAMLAYICI: Bir işlem başarıyla sonlanırsa (FULFILLMENT veya DELIVERY), arkasında süresi dolmamış bir Champion var mı bak.
    if action_id in ['FULFILLMENT', 'DELIVERY'] and status != 'CAPPED':
        cursor.execute("SELECT Source_ID FROM Marketplace_Attributions WHERE Target_ID = ? AND Attribution_Type = 'CHAMPION_NUDGE' AND Expiry_Date > ?", (master_id, now))
        attributions = cursor.fetchall()
        
        for attr in attributions:
            champion_id = attr[0]
            # Champion'a verilecek CLOSURE puanını Action_Registry'den çek
            cursor.execute("SELECT Base_Points FROM Action_Registry WHERE Action_ID = 'CLOSURE'")
            closure_pts = cursor.fetchone()
            if closure_pts:
                c_pts = closure_pts[0]
                # Champion'un cüzdanına otomatik bekleyen puan ekle
                cursor.execute("""
                    UPDATE Reward_Ledgers SET Pending_Points = Pending_Points + ? 
                    WHERE Master_ID = ? AND Role_Ledger = 'Champion'
                """, (c_pts, champion_id))
                
                # Champion için otomatik log girdisi oluştur
                cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                               (champion_id, 'Champion', master_id, 'CLOSURE', now, 'VALIDATING', c_pts, "CHAIN_ATTRIBUTION"))
                msg_string += f" 🏆 (Zincir Tamamlandı: {champion_id} kullanıcısına otomatik +{c_pts} CLOSURE puanı atfedildi!)"

    conn.commit()
    conn.close()
    return status, points, msg_string

def resolve_event(event_id, resolution_action, reason_code=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT Master_ID, Acting_Role, Action_ID, Earned_Points, Process_Status FROM Event_Stream_Logs WHERE Event_ID = ?", (event_id,))
    event = cursor.fetchone()
    
    if not event or event[4] not in ['VALIDATING', 'DISPUTED']:
        conn.close()
        return False, "Sadece VALIDATING veya DISPUTED statüsündeki olaylar çözümlenebilir."
        
    master_id, acting_role, action_id, points, current_status = event
    
    if resolution_action == 'SETTLE':
        new_status = 'SETTLED'
        reason_code = reason_code if reason_code else "APPROVED_CLEAN"
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ?, Settled_Points = Settled_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", 
                       (points, points, master_id, acting_role))
        
        cursor.execute("SELECT Integrity_Impact FROM Action_Registry WHERE Action_ID = ?", (action_id,))
        impact = cursor.fetchone()[0]
        if impact != 0:
            cursor.execute("SELECT Integrity_Score FROM Integrity_Profiles WHERE Master_ID = ?", (master_id,))
            curr_score = cursor.fetchone()[0]
            new_score = min(100, max(0, curr_score + impact)) 
            act_status = 'Normal' if new_score >= 80 else 'Warning' if new_score >= 60 else 'Review' if new_score >= 40 else 'Block'
            cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ? WHERE Master_ID = ?", (new_score, act_status, master_id))
            
    elif resolution_action == 'REVERSE':
        new_status = 'REVERSED'
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ?, Reversed_Points = Reversed_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", 
                       (points, points, master_id, acting_role))
                       
    elif resolution_action == 'DISPUTE':
        new_status = 'DISPUTED'
        reason_code = reason_code if reason_code else "DISPUTE_RAISED"
        
    cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = ?, Reason_Code = ? WHERE Event_ID = ?", (new_status, reason_code, event_id))
    conn.commit()
    conn.close()
    return True, f"Event {event_id} başarıyla {new_status} durumuna getirildi. Sebep: {reason_code}"

def get_normalized_weights(has_sub, has_cert):
    base_weights = {"Marketplace": 30, "Referral": 20, "Habit": 15, "Subscription": 20, "Certification": 15}
    active_weights = {k: base_weights[k] for k in ["Marketplace", "Referral", "Habit"]}
    if has_sub: active_weights["Subscription"] = base_weights["Subscription"]
    if has_cert: active_weights["Certification"] = base_weights["Certification"]
    total = sum(active_weights.values())
    return {k: round((v / total) * 100, 2) for k, v in active_weights.items()}

# --- STREAMLIT DASHBOARD UI ---
st.title("🌐 Buddy Rewards - Ultimate Ecosystem Engine")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚙️ Engine Setup", "👥 Users & Integrity", "🚀 Action Playground", "🏆 Mega & Fairness", "📜 Logs"])

with tab1:
    st.header("System Dynamics & Universal Registry")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Universal Action Registry")
        st.dataframe(pd.read_sql_query("SELECT * FROM Action_Registry", sqlite3.connect(DB_FILE)), use_container_width=True)
    with c2:
        st.subheader("Global Engine Settings")
        st.session_state.rollover_mode = st.toggle("ROLLOVER_MODE", st.session_state.rollover_mode)
        st.metric("Current Simulation Month", st.session_state.current_simulation_month)

with tab2:
    st.header("Ecosystem Actors & Security")
    df_users = pd.read_sql_query("""
        SELECT u.Master_ID, u.Primary_Role, u.Secondary_Roles, u.EID_Verified,
        i.Integrity_Score, i.Action_Status 
        FROM Global_Users u JOIN Integrity_Profiles i ON u.Master_ID = i.Master_ID
    """, sqlite3.connect(DB_FILE))
    
    def color_status(val):
        color = 'green' if val == 'Normal' else 'orange' if val == 'Warning' else 'red'
        return f'color: {color}; font-weight: bold'
        
    st.dataframe(df_users.style.map(color_status, subset=['Action_Status']), use_container_width=True)

with tab3:
    st.header("Action and Simulation Engine")
    df_users_base = pd.read_sql_query("SELECT Master_ID, Primary_Role, Secondary_Roles, Has_Subscription, Has_Certification FROM Global_Users", sqlite3.connect(DB_FILE))
    user_id = st.selectbox("Select Actor to Simulate:", df_users_base['Master_ID'].tolist())
    user_info = df_users_base[df_users_base['Master_ID'] == user_id].iloc[0]
    
    st.info(f"Dynamic Point Weights: {get_normalized_weights(user_info['Has_Subscription'], user_info['Has_Certification'])}")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Standard Action Trigger")
        available_roles = [user_info['Primary_Role']]
        if user_info['Secondary_Roles']:
            available_roles.extend([r.strip() for r in user_info['Secondary_Roles'].split(',')])
            
        acting_role = st.radio("Select Active Role for this Action:", available_roles, horizontal=True)
        available_actions = pd.read_sql_query(f"SELECT Action_ID FROM Action_Registry WHERE Role='{acting_role}'", sqlite3.connect(DB_FILE))['Action_ID'].tolist()
        
        if len(available_actions) > 0:
            act = st.selectbox("Action Type:", available_actions)
            t_id = st.text_input("Target User ID (Optional - Nudge/Chain senaryoları için):", placeholder="e.g. ID-12")
            
            if st.button("Execute Action"):
                status, earned, msg = execute_action(user_id, acting_role, act, t_id if t_id else None)
                if status == 'VALIDATING':
                    st.warning(msg) 
                elif status == 'CAPPED':
                    st.info(msg) # Capped durumu için info rengi
                else:
                    st.error(status)
                    
    with col2:
        st.subheader("2. Admin Resolution Desk")
        st.caption("Puanların kesinleşmesi veya itirazların karara bağlanması")
        
        conn = sqlite3.connect(DB_FILE)
        pending_validations = pd.read_sql_query("SELECT Event_ID, Master_ID, Action_ID, Earned_Points FROM Event_Stream_Logs WHERE Process_Status = 'VALIDATING'", conn)
        pending_disputes = pd.read_sql_query("SELECT Event_ID, Master_ID, Action_ID, Earned_Points, Reason_Code FROM Event_Stream_Logs WHERE Process_Status = 'DISPUTED'", conn)
        conn.close()
        
        st.markdown("#### ⏳ Normal Doğrulama İşlemleri (Validating)")
        if len(pending_validations) > 0:
            v_col1, v_col2, v_col3 = st.columns([2,1,1])
            v_ev_id = v_col1.selectbox("Select Validating Event", pending_validations['Event_ID'].tolist(), key="v_sel")
            if v_col2.button("✅ Settle", key="v_set"):
                success, m = resolve_event(v_ev_id, 'SETTLE')
                if success: st.success(m); st.rerun()
            if v_col3.button("⚠️ Dispute", key="v_dis"):
                success, m = resolve_event(v_ev_id, 'DISPUTE')
                if success: st.info(m); st.rerun()
        else:
            st.write("Bekleyen normal işlem yok.")
            
        st.markdown("---")
        
        st.markdown("#### ⚠️ Yöneticinin Karar Masası (Disputed)")
        if len(pending_disputes) > 0:
            st.dataframe(pending_disputes, use_container_width=True)
            d_col1, d_col2 = st.columns(2)
            d_ev_id = d_col1.selectbox("Select Disputed Event", pending_disputes['Event_ID'].tolist(), key="d_sel")
            r_code = d_col2.selectbox("Reason Code", REASON_CODES, key="r_code")
            
            dr_col1, dr_col2 = st.columns(2)
            if dr_col1.button("✅ İtirazı Reddet (Settle)", use_container_width=True):
                success, m = resolve_event(d_ev_id, 'SETTLE', r_code)
                if success: st.success(m); st.rerun()
            if dr_col2.button("❌ İşlemi İptal Et (Reverse)", use_container_width=True):
                success, m = resolve_event(d_ev_id, 'REVERSE', r_code)
                if success: st.error(m); st.rerun()
        else:
            st.write("Karar bekleyen bir itiraz bulunmuyor.")

with tab4:
    st.header("Reward Qualification and Fairness Engine")
    st.info("Bu modül daha sonra güncellenecektir.")

with tab5:
    st.header("System Logs")
    log_type = st.radio("Select Log Type:", ["Reward Ledgers (Cüzdanlar)", "Event Stream", "Marketplace Attributions (Zincirler)"])
    if log_type == "Event Stream":
        st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_ID DESC LIMIT 50", sqlite3.connect(DB_FILE)), use_container_width=True)
    elif log_type == "Reward Ledgers (Cüzdanlar)":
        st.dataframe(pd.read_sql_query("SELECT * FROM Reward_Ledgers", sqlite3.connect(DB_FILE)), use_container_width=True)
    else:
        st.dataframe(pd.read_sql_query("SELECT * FROM Marketplace_Attributions", sqlite3.connect(DB_FILE)), use_container_width=True)
