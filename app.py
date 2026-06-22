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

# FİNANS ONAY ZİNCİRİ İÇİN HAFIZA (STATE MACHINE)
if 'cycle_status' not in st.session_state:
    st.session_state.cycle_status = "DRAFT"

# --- UNIVERSAL ACTION REGISTRY ---
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

    cursor.execute('''CREATE TABLE IF NOT EXISTS Marketplace_Attributions (
        Attribution_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Source_ID TEXT,
        Target_ID TEXT,
        Attribution_Type TEXT,
        Expiry_Date DATETIME)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS reward_cycle_financial_config (
        Cycle_ID INTEGER PRIMARY KEY AUTOINCREMENT, Month_ID INTEGER, Status TEXT,
        Sub_Revenue REAL, Market_Revenue REAL, Ops_Costs REAL, Budget_Ceiling REAL,
        Profit_Margin_Pct REAL, Fixed_Profit_Floor REAL, Mega_Provision REAL,
        Max_Affordable_Pool REAL, Approved_Reward_Pool REAL)''')

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
            cursor.execute("INSERT INTO Monthly_Qualified_Users VALUES (?, ?, ?)", (mid, 0, 0)) 
            
    conn.commit()
    conn.close()

init_db()

# --- CORE ENGINE FUNCTIONS ---
def execute_action(master_id, acting_role, action_id, target_id=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    current_month_str = now.strftime('%Y-%m')
    
    cursor.execute("SELECT Base_Points, Cooldown, Monthly_Cap FROM Action_Registry WHERE Action_ID = ?", (action_id,))
    act_meta = cursor.fetchone()
    if not act_meta: return 'Failed', 0, ""
    base_points, cooldown, monthly_cap = act_meta
    
    query_cooldown = "SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Action_ID = ? AND Process_Status IN ('VALIDATING', 'SETTLED', 'DISPUTED', 'CAPPED') AND Event_Timestamp >= datetime(?, '-' || ? || ' minutes')"
    params_cd = [master_id, action_id, now, cooldown]
    if target_id:
        query_cooldown += " AND Target_ID = ?"
        params_cd.append(target_id)
        
    cursor.execute(query_cooldown, tuple(params_cd))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return 'BLOCKED (Cooldown)', 0, "Eylem Reddedildi (Zaman veya Çift Kayıt limitlerine takıldı)."

    cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Action_ID = ? AND strftime('%Y-%m', Event_Timestamp) = ? AND Process_Status IN ('VALIDATING', 'SETTLED', 'DISPUTED', 'CAPPED')", (master_id, action_id, current_month_str))
    if cursor.fetchone()[0] >= monthly_cap:
        status, points, msg_string = 'CAPPED', 0, f"Aylık kota ({monthly_cap}) doldu. Eylem sisteme (0 puan) ile işlendi."
    else:
        status, points, msg_string = 'VALIDATING', base_points, f"⏳ Eylem alındı. {base_points} puan 'VALIDATING' statüsünde bekliyor."
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, master_id, acting_role))

    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (master_id, acting_role, target_id, action_id, now, status, points, ""))
    
    if action_id == 'DEMAND_CREATED' and acting_role == 'Champion' and target_id:
        cursor.execute("INSERT INTO Marketplace_Attributions (Source_ID, Target_ID, Attribution_Type, Expiry_Date) VALUES (?, ?, ?, ?)", (master_id, target_id, 'CHAMPION_NUDGE', now + datetime.timedelta(days=7)))
        msg_string += " 🔗 (Zincir Başladı: Hedefe 7 günlük takip aktifleştirildi.)"

    if action_id in ['FULFILLMENT', 'DELIVERY'] and status != 'CAPPED':
        cursor.execute("SELECT Source_ID FROM Marketplace_Attributions WHERE Target_ID = ? AND Attribution_Type = 'CHAMPION_NUDGE' AND Expiry_Date > ?", (master_id, now))
        for attr in cursor.fetchall():
            cursor.execute("SELECT Base_Points FROM Action_Registry WHERE Action_ID = 'CLOSURE'")
            c_pts = cursor.fetchone()[0]
            cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points + ? WHERE Master_ID = ? AND Role_Ledger = 'Champion'", (c_pts, attr[0]))
            cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (attr[0], 'Champion', master_id, 'CLOSURE', now, 'VALIDATING', c_pts, "CHAIN_ATTRIBUTION"))
            msg_string += f" 🏆 (Zincir Tamamlandı: Champion {attr[0]} kullanıcısına CLOSURE atfedildi!)"

    conn.commit()
    conn.close()
    return status, points, msg_string

def resolve_event(event_id, resolution_action, reason_code=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT Master_ID, Acting_Role, Action_ID, Earned_Points, Process_Status FROM Event_Stream_Logs WHERE Event_ID = ?", (event_id,))
    event = cursor.fetchone()
    if not event or event[4] not in ['VALIDATING', 'DISPUTED']: return False, "Sadece VALIDATING veya DISPUTED çözümlenebilir."
        
    master_id, acting_role, action_id, points, current_status = event
    
    if resolution_action == 'SETTLE':
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ?, Settled_Points = Settled_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, points, master_id, acting_role))
        new_status, reason_code = 'SETTLED', reason_code if reason_code else "APPROVED_CLEAN"
        cursor.execute("SELECT Integrity_Impact FROM Action_Registry WHERE Action_ID = ?", (action_id,))
        impact = cursor.fetchone()[0]
        if impact != 0:
            cursor.execute("SELECT Integrity_Score FROM Integrity_Profiles WHERE Master_ID = ?", (master_id,))
            new_score = min(100, max(0, cursor.fetchone()[0] + impact)) 
            act_status = 'Normal' if new_score >= 80 else 'Warning' if new_score >= 60 else 'Review' if new_score >= 40 else 'Block'
            cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ? WHERE Master_ID = ?", (new_score, act_status, master_id))
    elif resolution_action == 'REVERSE':
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ?, Reversed_Points = Reversed_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, points, master_id, acting_role))
        new_status = 'REVERSED'
    else:
        new_status, reason_code = 'DISPUTED', reason_code if reason_code else "DISPUTE_RAISED"
        
    cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = ?, Reason_Code = ? WHERE Event_ID = ?", (new_status, reason_code, event_id))
    conn.commit()
    conn.close()
    return True, f"Event {event_id} {new_status} durumuna getirildi."

def get_normalized_weights(has_sub, has_cert):
    base_weights = {"Marketplace": 30, "Referral": 20, "Habit": 15, "Subscription": 20, "Certification": 15}
    active_weights = {k: base_weights[k] for k in ["Marketplace", "Referral", "Habit"]}
    if has_sub: active_weights["Subscription"] = base_weights["Subscription"]
    if has_cert: active_weights["Certification"] = base_weights["Certification"]
    total = sum(active_weights.values())
    return {k: round((v / total) * 100, 2) for k, v in active_weights.items()}

# --- STREAMLIT DASHBOARD UI ---
st.title("🌐 Buddy Rewards - Ultimate Ecosystem Engine")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["⚙️ Setup", "👥 Users", "🚀 Actions", "🏆 Mega & Fairness", "💰 Finance & Economics", "📜 Logs"])

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
    df_users = pd.read_sql_query("SELECT Master_ID, Primary_Role, Secondary_Roles, EID_Verified, Has_Certification, Continuous_Paid_Months, Integrity_Score, Action_Status FROM Global_Users JOIN Integrity_Profiles USING(Master_ID)", sqlite3.connect(DB_FILE))
    def color_status(val):
        color = 'green' if val == 'Normal' else 'orange' if val == 'Warning' else 'red'
        return f'color: {color}; font-weight: bold'
    st.dataframe(df_users.style.map(color_status, subset=['Action_Status']), use_container_width=True)

with tab3:
    st.header("Action and Simulation Engine")
    users = pd.read_sql_query("SELECT Master_ID, Primary_Role, Secondary_Roles, Has_Subscription, Has_Certification FROM Global_Users", sqlite3.connect(DB_FILE))
    u_id = st.selectbox("Select Actor to Simulate:", users['Master_ID'].tolist())
    u_info = users[users['Master_ID'] == u_id].iloc[0]
    st.info(f"Dynamic Point Weights: {get_normalized_weights(u_info['Has_Subscription'], u_info['Has_Certification'])}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Standard Action Trigger")
        roles = [u_info['Primary_Role']] + ([r.strip() for r in u_info['Secondary_Roles'].split(',')] if u_info['Secondary_Roles'] else [])
        a_role = st.radio("Active Role:", roles, horizontal=True)
        acts = pd.read_sql_query(f"SELECT Action_ID FROM Action_Registry WHERE Role='{a_role}'", sqlite3.connect(DB_FILE))['Action_ID'].tolist()
        act = st.selectbox("Action Type:", acts)
        t_id = st.text_input("Target ID (Optional - Nudge/Chain senaryoları için):")
        
        if st.button("Execute Action"):
            status, earned, msg = execute_action(u_id, a_role, act, t_id if t_id else None)
            if status == 'VALIDATING': st.warning(msg) 
            elif status == 'CAPPED': st.info(msg) 
            else: st.error(status)
            
        st.markdown("---")
        st.caption("Aylık minimum limitleri aşmak için Worker test verisi pompalama")
        if st.button("Simulate 30/30/15 Minimums for Top 5 Workers"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            workers = pd.read_sql_query("SELECT Master_ID FROM Global_Users WHERE Primary_Role='Worker'", conn)['Master_ID'].tolist()
            now = datetime.datetime.now()
            for w in workers[:5]: 
                for _ in range(30): 
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points) VALUES (?, 'Worker', 'WORKER_VIDEO_WATCH', ?, 'SETTLED', 5)", (w, now))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 5 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
                for _ in range(30): 
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points) VALUES (?, 'Worker', 'WORKER_QUIZ_ATTEMPT', ?, 'SETTLED', 5)", (w, now))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 5 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
                for _ in range(15): 
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points) VALUES (?, 'Worker', 'WORKER_REFERRAL', ?, 'SETTLED', 10)", (w, now))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 10 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
            conn.commit()
            conn.close()
            st.success("Successfully pushed 30/30/15 SETTLED events for top 5 workers!")
            
    with col2:
        st.subheader("2. Admin Resolution Desk")
        conn = sqlite3.connect(DB_FILE)
        pending_val = pd.read_sql_query("SELECT Event_ID, Master_ID, Action_ID, Earned_Points FROM Event_Stream_Logs WHERE Process_Status = 'VALIDATING'", conn)
        pending_disp = pd.read_sql_query("SELECT Event_ID, Master_ID, Action_ID, Reason_Code FROM Event_Stream_Logs WHERE Process_Status = 'DISPUTED'", conn)
        conn.close()
        
        st.markdown("#### ⏳ Normal Doğrulama İşlemleri (Validating)")
        if len(pending_val) > 0:
            v_col1, v_col2, v_col3 = st.columns([2,1,1])
            v_ev_id = v_col1.selectbox("Select Validating Event", pending_val['Event_ID'].tolist(), key="v_sel")
            if v_col2.button("✅ Settle", key="v_set"): resolve_event(v_ev_id, 'SETTLE'); st.rerun()
            if v_col3.button("⚠️ Dispute", key="v_dis"): resolve_event(v_ev_id, 'DISPUTE'); st.rerun()
        else: st.write("Bekleyen normal işlem yok.")
            
        st.markdown("---")
        st.markdown("#### ⚠️ Yöneticinin Karar Masası (Disputed)")
        if len(pending_disp) > 0:
            d_col1, d_col2 = st.columns(2)
            d_ev_id = d_col1.selectbox("Select Disputed Event", pending_disp['Event_ID'].tolist(), key="d_sel")
            r_code = d_col2.selectbox("Reason Code", REASON_CODES, key="r_code")
            dr_col1, dr_col2 = st.columns(2)
            if dr_col1.button("✅ İtirazı Reddet (Settle)", use_container_width=True): resolve_event(d_ev_id, 'SETTLE', r_code); st.rerun()
            if dr_col2.button("❌ İşlemi İptal Et (Reverse)", use_container_width=True): resolve_event(d_ev_id, 'REVERSE', r_code); st.rerun()
        else: st.write("Karar bekleyen bir itiraz bulunmuyor.")

with tab4:
    st.header("Reward Qualification and Fairness Engine")
    t4_col1, t4_col2 = st.columns(2)
    
    with t4_col1:
        st.markdown("### 📅 Monthly Selection Engine")
        c_cap1, c_cap2, c_cap3 = st.columns(3)
        t_cap = c_cap1.number_input("Total Winner Cap:", min_value=1, max_value=20, value=5)
        nat_cap = c_cap2.number_input("Max per Nationality:", min_value=1, max_value=10, value=2)
        camp_cap = c_cap3.number_input("Max per Camp:", min_value=1, max_value=10, value=2)
        
        if st.button("🚀 Run Monthly Engine", type="primary"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            curr_month = st.session_state.current_simulation_month
            users_df = pd.read_sql_query("""
                SELECT u.Master_ID, u.Primary_Role, u.Nationality, u.Labor_Cluster, i.Integrity_Score, i.Action_Status,
                       COALESCE((SELECT SUM(Settled_Points) FROM Reward_Ledgers WHERE Master_ID = u.Master_ID), 0) as Base_Score,
                       m.Rollover_Bonus
                FROM Global_Users u JOIN Integrity_Profiles i ON u.Master_ID = i.Master_ID JOIN Monthly_Qualified_Users m ON u.Master_ID = m.Master_ID
            """, conn)
            
            qualified_pool, disqualified_pool = [], []
            for _, u in users_df.iterrows():
                mid, role = u['Master_ID'], u['Primary_Role']
                if u['Integrity_Score'] < 80 or u['Action_Status'] == 'Block':
                    disqualified_pool.append({'Master_ID': mid, 'Reason': 'INTEGRITY_FAILED'}); continue
                if role == 'Worker':
                    cur.execute("SELECT Action_ID, COUNT(*) FROM Event_Stream_Logs WHERE Master_ID=? AND Process_Status IN ('SETTLED', 'CAPPED') GROUP BY Action_ID", (mid,))
                    counts = dict(cur.fetchall())
                    if counts.get('WORKER_VIDEO_WATCH',0)<30 or counts.get('WORKER_QUIZ_ATTEMPT',0)<30 or counts.get('WORKER_REFERRAL',0)<15:
                        disqualified_pool.append({'Master_ID': mid, 'Reason': 'HABIT_MIN_FAILED'}); continue
                qualified_pool.append({'Master_ID': mid, 'Nationality': u['Nationality'], 'Camp': u['Labor_Cluster'], 'Final_Score': u['Base_Score'] + u['Rollover_Bonus']})
                
            qualified_pool.sort(key=lambda x: x['Final_Score'], reverse=True)
            df_past = pd.read_sql_query("SELECT * FROM Past_Winners", conn)
            last_month_winners = df_past[df_past['Win_Month'] == curr_month - 1]['Master_ID'].tolist()
            older_winners = df_past[df_past['Win_Month'] < curr_month - 1]['Master_ID'].tolist()
            
            winners, rollovers, nat_counts, camp_counts, repeat_count = [], [], {}, {}, 0
            for cand in qualified_pool:
                mid, nat, camp = cand['Master_ID'], cand['Nationality'], cand['Camp']
                if mid in last_month_winners: cand['Reason_Code'] = 'REPEAT_COHORT_EXCLUDED'; rollovers.append(cand); continue
                if mid in older_winners:
                    if repeat_count >= int(t_cap * 0.20): cand['Reason_Code'] = 'REPEAT_COHORT_EXCLUDED'; rollovers.append(cand); continue
                    else: repeat_count += 1
                if nat_counts.get(nat, 0) >= nat_cap: cand['Reason_Code'] = 'NATIONALITY_CAP'; rollovers.append(cand); continue
                if camp_counts.get(camp, 0) >= camp_cap: cand['Reason_Code'] = 'CAMP_CAP'; rollovers.append(cand); continue
                if len(winners) < t_cap:
                    cand['Reason_Code'] = 'APPROVED'; winners.append(cand); nat_counts[nat] = nat_counts.get(nat, 0) + 1; camp_counts[camp] = camp_counts.get(camp, 0) + 1
                    cur.execute("INSERT INTO Past_Winners (Master_ID, Win_Month) VALUES (?, ?)", (mid, curr_month))
                    cur.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = 0 WHERE Master_ID = ?", (mid,))
                else: cand['Reason_Code'] = 'WINNER_CAP_FULL'; rollovers.append(cand)
                    
            if st.session_state.rollover_mode:
                for r in rollovers: cur.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = Rollover_Bonus + 5 WHERE Master_ID = ?", (r['Master_ID'],))
            conn.commit()
            conn.close()
            st.session_state.current_simulation_month += 1
            st.success(f"Month completed! Winners: {len(winners)}")
            if winners: st.dataframe(pd.DataFrame(winners)[['Master_ID', 'Nationality', 'Camp', 'Reason_Code']], use_container_width=True)

    with t4_col2:
        st.markdown("### 🌟 Mega Rewards Engine")
        m_cert = st.checkbox("Require Certification (T02)", value=True)
        m_excl = st.checkbox("Exclude Monthly Winners", value=True)
        m_grace = st.checkbox("Apply 1-Month Grace", value=False)
        
        if st.button("Inject 6-Month Mega Data for ID-1", type="secondary"):
            conn, now = sqlite3.connect(DB_FILE), datetime.datetime.now()
            cur = conn.cursor()
            for a, t in MEGA_TARGETS.items():
                for _ in range(t): cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status) VALUES ('ID-1', 'Worker', ?, ?, 'SETTLED')", (a, now))
            cur.execute("UPDATE Global_Users SET EID_Verified=1, Has_Certification=1, Continuous_Paid_Months=6 WHERE Master_ID='ID-1'")
            cur.execute("UPDATE Integrity_Profiles SET Integrity_Score=100, Action_Status='Normal' WHERE Master_ID='ID-1'")
            conn.commit()
            conn.close()
            st.success("ID-1 için Mega veriler yüklendi!")

        if st.button("🚀 Run Mega Cycle Evaluation", type="primary"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            workers = pd.read_sql_query("SELECT Master_ID, EID_Verified, Has_Certification, Continuous_Paid_Months FROM Global_Users WHERE Primary_Role='Worker'", conn)
            mega_winners, mega_failed = [], []
            req_months = 2 if m_grace else 3 
            
            for _, w in workers.iterrows():
                mid, fail_reason = w['Master_ID'], None
                if not w['EID_Verified']: fail_reason = 'MEGA_EID_FAILED'
                elif m_cert and not w['Has_Certification']: fail_reason = 'MEGA_CERT_FAILED'
                elif w['Continuous_Paid_Months'] < req_months: fail_reason = 'MEGA_SUBSCRIPTION_FAILED'
                else:
                    cur.execute("SELECT Integrity_Score, Action_Status FROM Integrity_Profiles WHERE Master_ID=?", (mid,))
                    i_score, i_status = cur.fetchone()
                    if i_score < 80 or i_status == 'Block': fail_reason = 'MEGA_INTEGRITY_FAILED'
                
                if not fail_reason and m_excl:
                    cur.execute("SELECT COUNT(*) FROM Past_Winners WHERE Master_ID=?", (mid,))
                    if cur.fetchone()[0] > 0: fail_reason = 'MEGA_MONTHLY_WINNER_EXCLUDED'
                        
                if not fail_reason:
                    cur.execute("SELECT Action_ID, COUNT(*) FROM Event_Stream_Logs WHERE Master_ID=? AND Process_Status IN ('SETTLED', 'CAPPED') GROUP BY Action_ID", (mid,))
                    counts = dict(cur.fetchall())
                    for req_a, req_t in MEGA_TARGETS.items():
                        if counts.get(req_a, 0) < req_t: fail_reason = 'MEGA_COUNTS_FAILED'; break
                            
                if fail_reason: mega_failed.append({'Master_ID': mid, 'Reason_Code': fail_reason})
                else: mega_winners.append({'Master_ID': mid, 'Reason_Code': 'MEGA_APPROVED'})
            conn.close()
            st.success("Mega Cycle 1 Değerlendirmesi Tamamlandı!")
            if mega_winners: st.dataframe(pd.DataFrame(mega_winners), use_container_width=True)
            if mega_failed: st.dataframe(pd.DataFrame(mega_failed), use_container_width=True)

with tab5:
    st.header("Financial & Economics Control Centre")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        st.subheader("Income & Costs")
        sub_rev = st.number_input("Subscription Revenue (AED)", value=50000)
        market_rev = st.number_input("Marketplace Revenue (AED)", value=120000)
        var_costs = st.number_input("Variable Ops/Gateway Costs (AED)", value=30000)
        
    with f_col2:
        st.subheader("Admin Guardrails")
        budget_ceil = st.number_input("Budget Ceiling (Max Limit)", value=40000)
        profit_margin = st.slider("Required Profit Margin (%)", 10, 50, 20)
        fixed_floor = st.number_input("Fixed Profit Floor (AED)", value=15000)
        mega_prov = st.number_input("Mega Rewards Provision (AED)", value=5000)
        
    net_revenue = sub_rev + market_rev
    net_contribution = net_revenue - var_costs
    req_profit = max(fixed_floor, (profit_margin / 100) * net_revenue)
    max_affordable = max(0, net_contribution - mega_prov - req_profit)
    approved_pool = min(budget_ceil, max_affordable)
    
    with f_col3:
        st.subheader("Calculated Pools")
        st.metric("Net Contribution", f"AED {net_contribution:,.2f}")
        st.metric("Required Profit Reserve", f"AED {req_profit:,.2f}")
        st.metric("Max Affordable Reward Pool", f"AED {max_affordable:,.2f}")
        st.metric("FINAL APPROVED POOL", f"AED {approved_pool:,.2f}")
        
    st.markdown("---")
    st.subheader("Distribution Scenarios")
    t1_cost, t2_cost, t3_cost = 5, 20, 50 
    scenarios = {
        "Conservative (Kâr Odaklı)": {"T1": 0.10, "T2": 0.30, "T3": 0.60},
        "Balanced (Dengeli)": {"T1": 0.30, "T2": 0.40, "T3": 0.30},
        "Growth (Tabana Yayılma)": {"T1": 0.60, "T2": 0.30, "T3": 0.10} 
    }
    
    s_data = []
    for s_name, alloc in scenarios.items():
        t1_b, t2_b, t3_b = approved_pool * alloc["T1"], approved_pool * alloc["T2"], approved_pool * alloc["T3"]
        s_data.append({
            "Strategy": s_name, "Total Winners Funded": int((t1_b/t1_cost) + (t2_b/t2_cost) + (t3_b/t3_cost)), 
            "Tier 1 (5 AED)": int(t1_b/t1_cost), "Tier 2 (20 AED)": int(t2_b/t2_cost), "Tier 3 (50 AED)": int(t3_b/t3_cost)
        })
    st.dataframe(pd.DataFrame(s_data), use_container_width=True)
    
    st.markdown("---")
    st.subheader("Approval Workflow")
    col_state1, col_state2 = st.columns([1,3])
    with col_state1: 
        st.info(f"**Current Status:** \n### {st.session_state.cycle_status}")
    with col_state2:
        if st.session_state.cycle_status == "DRAFT": 
            if st.button("Lock Snapshot & Move to SIMULATED"): st.session_state.cycle_status = "SIMULATED"; st.rerun()
        elif st.session_state.cycle_status == "SIMULATED": 
            if st.button("Submit to Finance (SUBMITTED)"): st.session_state.cycle_status = "SUBMITTED"; st.rerun()
        elif st.session_state.cycle_status == "SUBMITTED": 
            if st.button("Grant FINANCE_APPROVED"): st.session_state.cycle_status = "FINANCE_APPROVED"; st.rerun()
        elif st.session_state.cycle_status == "FINANCE_APPROVED": 
            if st.button("Grant FINAL_APPROVED"): st.session_state.cycle_status = "FINAL_APPROVED"; st.rerun()
        elif st.session_state.cycle_status == "FINAL_APPROVED":
            if st.button("🚀 RELEASE REWARDS", type="primary"): 
                st.session_state.cycle_status = "RELEASED"
                conn = sqlite3.connect(DB_FILE)
                # Olay Loguna ödüllerin dağıtıldığını ekliyoruz ki ekranda görünsün
                conn.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code) VALUES ('SYSTEM', 'Admin', 'REWARDS_RELEASED', ?, 'SETTLED', 0, 'CYCLE_CLOSED')", (datetime.datetime.now(),))
                conn.commit()
                conn.close()
                st.balloons()
                st.success("Ödüller dağıtıldı ve muhasebe kayıtlarına 'Reconciled' olarak işlendi!")
                st.rerun()
        elif st.session_state.cycle_status == "RELEASED":
            st.success("Bu ayın bütçesi başarıyla dağıtıldı ve döngü kapandı.")
            if st.button("Reset Cycle (Yeni Ay)"): st.session_state.cycle_status = "DRAFT"; st.rerun()

with tab6:
    st.header("System Logs")
    log_type = st.radio("Select Log Type:", ["Reward Ledgers (Cüzdanlar)", "Event Stream", "Marketplace Attributions (Zincirler)", "Monthly Winners History"])
    
    if log_type == "Event Stream":
        st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_ID DESC LIMIT 50", sqlite3.connect(DB_FILE)), use_container_width=True)
    elif log_type == "Reward Ledgers (Cüzdanlar)":
        st.dataframe(pd.read_sql_query("SELECT * FROM Reward_Ledgers", sqlite3.connect(DB_FILE)), use_container_width=True)
    elif log_type == "Marketplace Attributions (Zincirler)":
        st.dataframe(pd.read_sql_query("SELECT * FROM Marketplace_Attributions", sqlite3.connect(DB_FILE)), use_container_width=True)
    else:
        st.dataframe(pd.read_sql_query("SELECT * FROM Past_Winners", sqlite3.connect(DB_FILE)), use_container_width=True)
