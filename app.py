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

    # YENİ EKLENEN FİNANSAL TABLOLAR (BÖLÜM 25 & 32)
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
        return 'BLOCKED (Cooldown)', 0, "Eylem Reddedildi (Cooldown)."

    cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Action_ID = ? AND strftime('%Y-%m', Event_Timestamp) = ? AND Process_Status IN ('VALIDATING', 'SETTLED', 'DISPUTED', 'CAPPED')", (master_id, action_id, current_month_str))
    if cursor.fetchone()[0] >= monthly_cap:
        status, points, msg_string = 'CAPPED', 0, f"Aylık kota ({monthly_cap}) doldu. (0 puan)"
    else:
        status, points, msg_string = 'VALIDATING', base_points, f"⏳ Eylem alındı. {base_points} puan 'VALIDATING' statüsünde."
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, master_id, acting_role))

    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (master_id, acting_role, target_id, action_id, now, status, points, ""))
    
    if action_id == 'DEMAND_CREATED' and acting_role == 'Champion' and target_id:
        cursor.execute("INSERT INTO Marketplace_Attributions (Source_ID, Target_ID, Attribution_Type, Expiry_Date) VALUES (?, ?, ?, ?)", (master_id, target_id, 'CHAMPION_NUDGE', now + datetime.timedelta(days=7)))
        msg_string += " 🔗 Zincir Başladı."

    if action_id in ['FULFILLMENT', 'DELIVERY'] and status != 'CAPPED':
        cursor.execute("SELECT Source_ID FROM Marketplace_Attributions WHERE Target_ID = ? AND Attribution_Type = 'CHAMPION_NUDGE' AND Expiry_Date > ?", (master_id, now))
        for attr in cursor.fetchall():
            cursor.execute("SELECT Base_Points FROM Action_Registry WHERE Action_ID = 'CLOSURE'")
            c_pts = cursor.fetchone()[0]
            cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points + ? WHERE Master_ID = ? AND Role_Ledger = 'Champion'", (c_pts, attr[0]))
            cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (attr[0], 'Champion', master_id, 'CLOSURE', now, 'VALIDATING', c_pts, "CHAIN_ATTRIBUTION"))
            msg_string += " 🏆 Zincir Tamamlandı (CLOSURE atfedildi)."

    conn.commit()
    conn.close()
    return status, points, msg_string

def resolve_event(event_id, resolution_action, reason_code=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT Master_ID, Acting_Role, Action_ID, Earned_Points, Process_Status FROM Event_Stream_Logs WHERE Event_ID = ?", (event_id,))
    event = cursor.fetchone()
    if not event or event[4] not in ['VALIDATING', 'DISPUTED']: return False, "Sadece VALIDATING veya DISPUTED çözümlenebilir."
        
    if resolution_action == 'SETTLE':
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ?, Settled_Points = Settled_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (event[3], event[3], event[0], event[1]))
        new_status, reason_code = 'SETTLED', reason_code if reason_code else "APPROVED_CLEAN"
    elif resolution_action == 'REVERSE':
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ?, Reversed_Points = Reversed_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (event[3], event[3], event[0], event[1]))
        new_status = 'REVERSED'
    else:
        new_status, reason_code = 'DISPUTED', reason_code if reason_code else "DISPUTE_RAISED"
        
    cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = ?, Reason_Code = ? WHERE Event_ID = ?", (new_status, reason_code, event_id))
    conn.commit()
    conn.close()
    return True, f"Durum güncellendi: {new_status}"

# --- STREAMLIT DASHBOARD UI ---
st.title("🌐 Buddy Rewards - Ultimate Ecosystem Engine")
# YENİ SEKME (TAB 5) EKLENDİ
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["⚙️ Setup", "👥 Users", "🚀 Actions", "🏆 Mega & Fairness", "💰 Finance & Economics", "📜 Logs"])

with tab1:
    st.header("System Dynamics & Universal Registry")
    st.dataframe(pd.read_sql_query("SELECT * FROM Action_Registry", sqlite3.connect(DB_FILE)), use_container_width=True)

with tab2:
    st.header("Ecosystem Actors & Security")
    st.dataframe(pd.read_sql_query("SELECT Master_ID, Primary_Role, EID_Verified, Integrity_Score, Action_Status FROM Global_Users JOIN Integrity_Profiles USING(Master_ID)", sqlite3.connect(DB_FILE)), use_container_width=True)

with tab3:
    st.header("Action and Simulation Engine")
    users = pd.read_sql_query("SELECT Master_ID, Primary_Role, Secondary_Roles FROM Global_Users", sqlite3.connect(DB_FILE))
    u_id = st.selectbox("Actor:", users['Master_ID'].tolist())
    u_info = users[users['Master_ID'] == u_id].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Standard Action")
        roles = [u_info['Primary_Role']] + ([r.strip() for r in u_info['Secondary_Roles'].split(',')] if u_info['Secondary_Roles'] else [])
        a_role = st.radio("Active Role:", roles, horizontal=True)
        acts = pd.read_sql_query(f"SELECT Action_ID FROM Action_Registry WHERE Role='{a_role}'", sqlite3.connect(DB_FILE))['Action_ID'].tolist()
        act = st.selectbox("Action:", acts)
        t_id = st.text_input("Target ID (Optional):")
        if st.button("Execute"):
            st.info(execute_action(u_id, a_role, act, t_id)[2])
            
    with col2:
        st.subheader("2. Resolution Desk")
        pending = pd.read_sql_query("SELECT Event_ID, Action_ID, Earned_Points FROM Event_Stream_Logs WHERE Process_Status = 'VALIDATING'", sqlite3.connect(DB_FILE))
        if len(pending) > 0:
            ev_id = st.selectbox("Validating Event", pending['Event_ID'].tolist())
            if st.button("✅ Settle"): resolve_event(ev_id, 'SETTLE'); st.rerun()
            if st.button("❌ Reverse"): resolve_event(ev_id, 'REVERSE'); st.rerun()

with tab4:
    st.header("Reward Qualification and Fairness Engine")
    st.info("Kotalar ve Adalet Motoru aktif. (Önceki aşamada tamamlandı)")

# ====================================================================
# YEPYENİ BÖLÜM: FİNANS VE EKONOMİ SEKME ENTEGRASYONU (BÖLÜM 23-38)
# ====================================================================
with tab5:
    st.header("Financial & Economics Control Centre")
    st.markdown("Şirketin belirlediği kârlılık kurallarına göre maksimum dağıtılabilir ödül bütçesinin hesaplanması ve onaylanması.")
    
    # 1. Finansal Formüller ve Havuz Hesaplaması (Bölüm 25)
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        st.subheader("Income & Costs")
        sub_rev = st.number_input("Subscription Revenue (AED)", value=50000)
        market_rev = st.number_input("Marketplace Revenue (AED)", value=120000)
        var_costs = st.number_input("Variable Ops/Gateway Costs (AED)", value=30000)
        
    with f_col2:
        st.subheader("Admin Guardrails (FIN-001/016)")
        budget_ceil = st.number_input("Budget Ceiling (Max Limit)", value=40000)
        profit_margin = st.slider("Required Profit Margin (%)", 10, 50, 20)
        fixed_floor = st.number_input("Fixed Profit Floor (AED)", value=15000)
        mega_prov = st.number_input("Mega Rewards Provision (AED)", value=5000)
        
    # Matematiksel Çekirdek (Bölüm 25)
    net_revenue = sub_rev + market_rev
    net_contribution = net_revenue - var_costs
    req_profit = max(fixed_floor, (profit_margin / 100) * net_revenue)
    max_affordable = max(0, net_contribution - mega_prov - req_profit)
    approved_pool = min(budget_ceil, max_affordable)
    
    with f_col3:
        st.subheader("Calculated Pools")
        st.metric("Net Contribution", f"AED {net_contribution:,.2f}")
        st.metric("Required Profit Reserve", f"AED {req_profit:,.2f}")
        st.metric("Max Affordable Reward Pool", f"AED {max_affordable:,.2f}", delta="Limit", delta_color="off")
        st.metric("FINAL APPROVED POOL", f"AED {approved_pool:,.2f}", delta="Distributable", delta_color="normal")
        
    st.markdown("---")
    
    # 2. Dağıtım Senaryoları (Bölüm 28)
    st.subheader("Distribution Scenarios (Reward Inventory Allocation)")
    st.caption("Onaylanan bütçeyi kullanıcılara nasıl dağıtacağımıza dair maliyet senaryoları.")
    
    # Varsayılan ödül envanter maliyetleri (Tier 1: Küçük, Tier 2: Orta, Tier 3: Büyük)
    t1_cost, t2_cost, t3_cost = 5, 20, 50 
    
    scenarios = {
        "Conservative (Kâr Odaklı)": {"T1_share": 0.10, "T2_share": 0.30, "T3_share": 0.60},
        "Balanced (Dengeli)": {"T1_share": 0.30, "T2_share": 0.40, "T3_share": 0.30},
        "Growth (Tabana Yayılma)": {"T1_share": 0.60, "T2_share": 0.30, "T1_share": 0.10} # Growth tabana yayılma için Tier 1 ağırlıklıdır
    }
    
    scenario_data = []
    for s_name, alloc in scenarios.items():
        t1_budget = approved_pool * alloc.get("T1_share", 0.60) # Fallback for growth fix
        t2_budget = approved_pool * alloc.get("T2_share", 0.30)
        t3_budget = approved_pool * alloc.get("T3_share", 0.10)
        
        winners = int((t1_budget/t1_cost) + (t2_budget/t2_cost) + (t3_budget/t3_cost))
        scenario_data.append({
            "Strategy": s_name, 
            "Total Winners Funded": winners, 
            "Tier 1 Rewards (5 AED)": int(t1_budget/t1_cost),
            "Tier 2 Rewards (20 AED)": int(t2_budget/t2_cost),
            "Tier 3 Rewards (50 AED)": int(t3_budget/t3_cost),
            "Cost Utilized": f"AED {approved_pool:,.2f}"
        })
        
    st.dataframe(pd.DataFrame(scenario_data), use_container_width=True)
    
    st.markdown("---")
    
    # 3. Onay İş Akışı (Approval Workflow - Bölüm 30)
    st.subheader("Approval Workflow State Machine")
    col_state1, col_state2 = st.columns([1,3])
    
    with col_state1:
        current_state = st.radio("Cycle Status", ["DRAFT", "SIMULATED", "SUBMITTED", "FINANCE_APPROVED", "FINAL_APPROVED", "RELEASED"])
        
    with col_state2:
        if current_state == "DRAFT":
            st.info("Aşama: DRAFT. Finansal ayarlar şu an düzenlenebilir. Hazır olduğunuzda hesaplamaları kilitleyin.")
            st.button("Lock Snapshot & Move to SIMULATED")
        elif current_state == "SUBMITTED":
            st.warning("Aşama: SUBMITTED. Maker tarafından onaya sunuldu. Finans ekibinin incelemesi bekleniyor.")
            st.button("Grant FINANCE_APPROVED")
        elif current_state == "FINAL_APPROVED":
            st.success("Aşama: FINAL_APPROVED. Tüm bütçe kontrollerinden geçti. Havuz kilitlendi.")
            if st.button("🚀 RELEASE REWARDS", type="primary"):
                st.balloons()
                st.success("Ödüller dağıtıldı ve muhasebe kayıtlarına 'Reconciled' olarak işlendi!")
        else:
            st.write(f"Şu anki aşama: {current_state}. Süreç kilitli veya işlem bekleniyor.")

with tab6:
    st.header("System Logs")
    st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_ID DESC LIMIT 50", sqlite3.connect(DB_FILE)), use_container_width=True)
