import streamlit as st
import sqlite3
import pandas as pd
import datetime
import random
import os

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Buddy Rewards - Ultimate Engine", layout="wide")
DB_FILE = 'buddy_rewards_v4.db' 

if 'rollover_mode' not in st.session_state:
    st.session_state.rollover_mode = True

if 'current_simulation_month' not in st.session_state:
    st.session_state.current_simulation_month = 1 

if 'cycle_status' not in st.session_state:
    st.session_state.cycle_status = "DRAFT"

if 'rule_version' not in st.session_state:
    st.session_state.rule_version = "v2.0"

if 'random_seed' not in st.session_state:
    st.session_state.random_seed = 42

random.seed(st.session_state.random_seed)

# --- UNIVERSAL ACTION REGISTRY ---
UNIVERSAL_ACTION_REGISTRY = [
    ("Worker, Captain, Champion", "WORKER_VIDEO_WATCH", "Retention", 5, 1440, 0, True, 30),
    ("All", "WORKER_QUIZ_ATTEMPT", "Retention", 5, 1440, 0, True, 30),
    ("All", "PASS_QUIZ", "Quality", 2, 1440, 0, False, 30),
    ("All", "WORKER_REFERRAL", "Growth", 10, 0, +2, True, 15),
    ("Worker, Captain, Champion, Contractor", "SUPPLIER_ADDED", "Growth", 20, 60, +5, True, 5),
    ("Worker, Champion, Contractor", "TRANSPORTER_ADDED", "Growth", 20, 60, +5, True, 5),
    ("Worker, Captain, Champion", "BUDDY_HELP", "Community", 10, 120, +5, True, 5),
    ("All", "EID_KYC_VERIFIED", "Trust", 100, 0, 0, True, 1),
    ("All", "CERTIFICATION_COMPLETED", "Trust", 100, 0, 0, True, 1),
    ("All", "SUBSCRIPTION_PAID", "Trust", 50, 0, 0, True, 1),
    ("All", "REQ_SHARE_SENT", "Propagation", 2, 0, 0, False, 300),
    ("All", "REQ_SHARE_OPENED", "Propagation", 5, 0, 0, False, 999),
    ("All", "REQ_SHARE_ENGAGED", "Propagation", 10, 0, 0, False, 999),
    ("All", "SHARE_CHAIN_FULFILLED", "Outcome", 50, 0, 0, True, 999),
    ("Worker", "FULFILL_VALIDATED", "Trust", 40, 0, +10, True, 20),
    ("Contractor", "POST_REQ", "Trigger", 20, 30, 0, False, 10),
    ("Contractor", "CLONE_REQ", "Trigger", 10, 0, 0, False, 5),
    ("Contractor", "RESPOND_FIRST_BID", "Response", 5, 0, 0, False, 50),
    ("Contractor", "ACCEPT_BID", "Conversion", 20, 0, 0, False, 10),
    ("Contractor", "VALIDATE", "Completion", 20, 0, +15, False, 10),
    ("Contractor", "CLOSE_REQ", "Completion", 10, 0, 0, False, 10),
    ("Contractor", "RATE_COUNTERPARTY", "Trust", 5, 0, 0, False, 50),
    ("Contractor", "PAY_ON_TIME", "Trust", 15, 0, 0, False, 10),
    ("Supplier", "PROFILE", "Activation", 20, 129600, +1, False, 1),
    ("Supplier", "UPDATE_CATALOGUE", "Retention", 5, 0, 0, False, 4),
    ("Supplier", "QUOTE", "Response", 10, 60, +2, False, 20),
    ("Supplier", "RESPOND_BID_SLA", "Quality", 5, 0, 0, False, 20),
    ("Supplier", "BID_SELECTED", "Conversion", 15, 0, 0, False, 10),
    ("Supplier", "FULFILLMENT", "Completion", 40, 0, +10, False, 10),
    ("Supplier", "ON_TIME_DELIVERY", "Quality", 10, 0, 0, False, 10),
    ("Supplier", "UPLOAD_POD", "Trust", 5, 0, 0, False, 10),
    ("Supplier", "DISPUTE_FREE_SETTLEMENT", "Trust", 10, 0, 0, False, 10),
    ("Transporter", "SET_CAPACITY", "Trigger", 5, 720, 0, False, 60),
    ("Transporter", "RETURN_TRIP", "Trigger", 15, 120, +5, False, 20),
    ("Transporter", "ACCEPT_BACKHAUL", "Response", 15, 0, 0, False, 10),
    ("Transporter", "MULTI_PICKUP", "Trigger", 10, 0, +5, False, 30),
    ("Transporter", "COMPLETE_BUNDLED_TRIP", "Completion", 20, 0, 0, False, 8),
    ("Transporter", "DELIVERY", "Completion", 40, 0, +10, False, 15),
    ("Transporter", "UPLOAD_POD_TRANS", "Trust", 5, 0, 0, False, 15),
    ("Transporter", "MEET_SLA", "Quality", 10, 0, 0, False, 15),
    ("Transporter", "REDUCE_EMPTY_KM", "Efficiency", 25, 0, 0, False, 8),
    ("Transporter", "COMPETITIVE_PRICE", "Efficiency", 10, 0, 0, False, 10),
    ("Transporter", "DISPUTE_FREE_TRIP", "Trust", 10, 0, 0, False, 15),
    ("Champion", "DEMAND_CREATED", "Trigger", 20, 60, +5, False, 10),
    ("Champion", "REQ_PROPAGATED", "Propagation", 10, 0, 0, False, 20),
    ("Champion", "SUPPLIER_ACTIVATED", "Activation", 15, 0, 0, False, 10),
    ("Champion", "TRANSPORTER_ACTIVATED", "Activation", 15, 0, 0, False, 10),
    ("Champion", "CONTRACTOR_ACTIVATED", "Activation", 15, 0, 0, False, 10),
    ("Champion", "NUDGE_VALID_BID", "Response", 10, 0, 0, False, 20),
    ("Champion", "ACHIEVE_3_5_BIDS", "Liquidity", 25, 0, 0, False, 10),
    ("Champion", "RESOLVE_UNMET_DEMAND", "Completion", 35, 0, 0, False, 10),
    ("Champion", "CLOSURE", "Completion", 50, 0, +20, False, 10),
    ("Champion", "ACTIVATE_BACKHAUL", "Logistics", 20, 0, 0, False, 10),
    ("Champion", "REACTIVATE_PROVIDER", "Retention", 15, 0, 0, False, 10),
    ("Champion", "IMPROVE_BID_SLA", "Quality", 10, 0, 0, False, 10),
    ("Captain", "VERIFY_SIGNUP", "Growth", 2, 0, +2, False, 999),
    ("Captain", "ACTIVE_CLUSTER", "Trust", 25, 1440, +10, False, 1),
    ("Captain", "USER_ACTIVE", "Retention", 10, 0, +2, False, 999),
    ("Captain", "WORKER_RETAINED", "Retention", 15, 0, +5, False, 999),
    ("Captain", "HIGH_RETENTION_CLUSTER", "Trust", 40, 1440, +15, False, 1),
    ("Captain", "DAILY_TASK_ACTIVATION", "Retention", 5, 0, +1, False, 20),
    ("Captain", "SESSION_COMPLETED", "Community", 20, 1440, +5, False, 4),
    ("Captain", "INACTIVE_REACTIVATED", "Retention", 10, 0, +3, False, 20),
    ("Captain", "REFERRAL_RETAINED", "Growth", 15, 0, +4, False, 20),
    ("Captain", "CAMP_CHALLENGE", "Community", 25, 1440, +5, False, 4),
    ("All", "NR01_APP_INSTALL", "Trigger", 0, 0, 0, False, 1),
    ("All", "NR02_COSMETIC_PROFILE_EDIT", "Trigger", 0, 0, 0, False, 10),
    ("Transporter", "NR03_FAKE_BACKHAUL", "Trigger", 0, 0, -10, False, 5),
    ("Champion", "NR04_NUDGE_NO_RESPONSE", "Trigger", 0, 0, 0, False, 50),
    ("Captain", "NR05_TASK_IGNORED", "Trigger", 0, 0, 0, False, 50),
    ("Contractor", "NR06_SPAM_REQUIREMENT", "Trigger", 0, 0, -10, False, 5),
    ("Supplier", "NR07_SELF_BID", "Trigger", 0, 0, -20, False, 5),
    ("All", "NR08_ACTOR_FAULT_CANCEL", "Trigger", 0, 0, -15, False, 5),
    ("Transporter, Supplier", "NR09_REJECTED_POD", "Trigger", 0, 0, -5, False, 5),
    ("Worker", "NR10_PAIR_FARMING", "Trigger", 0, 0, -5, False, 5),
    ("All", "NR11_CELEBRATION_VIEW", "Trigger", 0, 0, 0, False, 50),
    ("All", "NR12_WINNER_STATUS", "Benefit", 0, 0, 0, False, 1)
]

MEGA_TARGETS = {
    'WORKER_VIDEO_WATCH': 180, 'WORKER_QUIZ_ATTEMPT': 180, 'WORKER_REFERRAL': 150,
    'SUPPLIER_ADDED': 50, 'FULFILL_VALIDATED': 10, 'BUDDY_HELP': 12               
}

REASON_CODES = {
    "Eligibility": ["HABIT_VIDEO_MIN_FAILED", "HABIT_QUIZ_MIN_FAILED", "REFERRAL_MIN_FAILED", "ROLE_GATE_FAILED", "INTEGRITY_FAILED"],
    "Validation": ["PROOF_MISSING", "POD_INVALID", "DUPLICATE_PROVIDER", "INVALID_TRIP", "OUTCOME_NOT_CONFIRMED"],
    "Caps_Cooldowns": ["DAILY_CAP_REACHED", "MONTHLY_CAP_REACHED", "EXACT_REPEAT_COOLDOWN", "PAIR_COOLDOWN"],
    "Integrity": ["SELF_REFERRAL", "COLLUSION_SUSPECTED", "DUPLICATE_IDENTITY", "VELOCITY_SPIKE", "FAKE_BACKHAUL"],
    "Monthly_Selection": ["APPROVED", "WINNER_CAP_FULL", "REPEAT_COHORT_EXCLUDED", "NATIONALITY_CAP", "GEOGRAPHY_CAP", "CAMP_CAP", "ROLLOVER_APPLIED", "QUALIFIED_NOT_FUNDED"],
    "Mega": ["MEGA_APPROVED", "MEGA_EID_FAILED", "MEGA_CERT_FAILED", "MEGA_SUBSCRIPTION_FAILED", "MEGA_INTEGRITY_FAILED", "MEGA_MONTHLY_WINNER_EXCLUDED", "MEGA_COUNTS_FAILED"],
    "Reversal": ["CANCELLED", "ACTOR_FAULT", "DISPUTE_UPHELD", "POST_SETTLEMENT_FRAUD", "REQ_CANCELLED_INVALID", "BUYER_FAULT_CANCEL", "SUPPLIER_NON_FULFIL", "TRIP_CANCEL_ACTOR_FAULT", "POD_DISPUTED", "MEGA_POST_AWARD_REVIEW", "APPROVED_CLEAN"]
}
FLAT_REASON_CODES = [code for category in REASON_CODES.values() for code in category]

# --- DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS Global_Users (
        Master_ID TEXT PRIMARY KEY, Name TEXT, Primary_Role TEXT, Secondary_Roles TEXT, Location TEXT, Nationality TEXT, 
        Labor_Cluster TEXT, Consent_Given BOOLEAN, Has_Subscription BOOLEAN, Has_Certification BOOLEAN,
        EID TEXT, Phone TEXT, Device_Fingerprint TEXT, EID_Verified BOOLEAN, 
        Join_Date DATETIME, Continuous_Paid_Months INTEGER,
        Join_Month INTEGER, Geography TEXT, Company TEXT)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Action_Registry (
        Action_ID TEXT PRIMARY KEY, Role TEXT, Category TEXT, Base_Points INTEGER, Cooldown INTEGER, 
        Integrity_Impact INTEGER, Mega_Eligible BOOLEAN, Monthly_Cap INTEGER)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Event_Stream_Logs (
        Event_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Acting_Role TEXT, Target_ID TEXT, Action_ID TEXT, 
        Event_Timestamp DATETIME, Process_Status TEXT, Earned_Points INTEGER, Reason_Code TEXT DEFAULT '',
        Object_ID TEXT, Source_Module TEXT, Raw_Points INTEGER, Awarded_Points INTEGER, Cap_Cooldown_Result TEXT, Rule_Version TEXT)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Integrity_Profiles (
        Master_ID TEXT PRIMARY KEY, Integrity_Score INTEGER DEFAULT 100, Action_Status TEXT DEFAULT 'Normal', Critical_Flag BOOLEAN DEFAULT 0)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Reward_Ledgers (
        Ledger_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Role_Ledger TEXT,
        Pending_Points INTEGER DEFAULT 0, Settled_Points INTEGER DEFAULT 0, Reversed_Points INTEGER DEFAULT 0,
        Event_ID INTEGER, Rule_Version TEXT, Reason_Code TEXT)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Monthly_Qualified_Users (
        Master_ID TEXT PRIMARY KEY, Total_Score DECIMAL(10,2), Rollover_Bonus DECIMAL(10,2) DEFAULT 0)''')
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Past_Winners (
        Win_ID INTEGER PRIMARY KEY AUTOINCREMENT, Master_ID TEXT, Win_Month INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Marketplace_Attributions (
        Attribution_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Source_ID TEXT, Target_ID TEXT, Attribution_Type TEXT, Expiry_Date DATETIME)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS reward_cycle_financial_config (
        Cycle_ID INTEGER PRIMARY KEY AUTOINCREMENT, Month_ID INTEGER, Status TEXT,
        Sub_Revenue DECIMAL(10,2), Market_Revenue DECIMAL(10,2), Ops_Costs DECIMAL(10,2), Budget_Ceiling DECIMAL(10,2),
        Profit_Margin_Pct DECIMAL(10,2), Fixed_Profit_Floor DECIMAL(10,2), Mega_Provision DECIMAL(10,2),
        Max_Affordable_Pool DECIMAL(10,2), Approved_Reward_Pool DECIMAL(10,2),
        Rule_Version TEXT, Currency TEXT DEFAULT 'AED', Profit_Mode TEXT DEFAULT 'HYBRID',
        Refund_Reserve DECIMAL(10,2) DEFAULT 0, Other_Reserves DECIMAL(10,2) DEFAULT 0, Created_By TEXT, Config_Hash TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Attribution_Records (
        Attribution_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Referrer_ID TEXT, Captain_ID TEXT, Champion_ID TEXT, Campaign_ID TEXT, Share_Chain_ID TEXT,
        Attribution_Start DATETIME, Attribution_End DATETIME, Attribution_Reason TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Marketplace_Records (
        Record_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Requirement_ID TEXT, Bid_ID TEXT, Order_ID TEXT, Fulfillment_ID TEXT, Transporter_ID TEXT,
        Payment_Status TEXT, POD_Status TEXT, Dispute_Status TEXT, Cancellation_Fault TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Trip_Records (
        Trip_ID TEXT PRIMARY KEY,
        Origin TEXT, Destination TEXT, Return_Leg BOOLEAN, Capacity TEXT, Bundle_ID TEXT,
        Route_Baseline_KM DECIMAL(10,2), Actual_KM DECIMAL(10,2), Empty_KM_Saving DECIMAL(10,2),
        Pickup_Timestamp DATETIME, Delivery_Timestamp DATETIME)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Cycle_Snapshots (
        Snapshot_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Month INTEGER, Master_ID TEXT, Qualification_Flags TEXT, Component_Scores TEXT,
        Normalized_Weights TEXT, Rollover_Amount DECIMAL(10,2), Repeat_Cohort TEXT,
        Distribution_Group TEXT, Winner_Outcome TEXT, Rule_Version TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Audit_Trail (
        Audit_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Config_Change TEXT, Admin_Override TEXT, Reviewer TEXT, Timestamp DATETIME,
        Old_Value TEXT, New_Value TEXT, Reason TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Revenue_Snapshots (
        Snapshot_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Cycle_ID INTEGER, Source_Type TEXT, Gross_Amount DECIMAL(10,2), Collected_Amount DECIMAL(10,2),
        Failed_Amount DECIMAL(10,2), Refunded_Amount DECIMAL(10,2), Settlement_Status TEXT, Snapshot_Time DATETIME)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Cost_Snapshots (
        Snapshot_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Cycle_ID INTEGER, Cost_Type TEXT, Amount DECIMAL(10,2), Basis TEXT, Source_System TEXT, Snapshot_Time DATETIME)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Reward_Inventory (
        Reward_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Funding_Source TEXT, Sponsor_ID TEXT, Benefit_Type TEXT, Face_Value DECIMAL(10,2), Actual_Buddy_Cost DECIMAL(10,2),
        Available_Qty INTEGER, Reserved_Qty INTEGER, Expiry DATETIME, Redemption_Terms TEXT, Currency_Code TEXT DEFAULT 'AED')''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Reward_Scenarios (
        Scenario_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Cycle_ID INTEGER, Strategy TEXT, Input_JSON TEXT, Funded_Winner_Count INTEGER,
        Registered_Coverage DECIMAL(10,2), Qualified_Coverage DECIMAL(10,2), Reward_Face_Value DECIMAL(10,2),
        Actual_Cost DECIMAL(10,2), Projected_Profit DECIMAL(10,2), Projected_Margin DECIMAL(10,2), Warnings TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Reward_Tier_Allocations (
        Allocation_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Scenario_ID INTEGER, Tier_ID TEXT, Reward_ID INTEGER, Winner_Count INTEGER,
        Unit_Face_Value DECIMAL(10,2), Unit_Actual_Cost DECIMAL(10,2), Total_Actual_Cost DECIMAL(10,2))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Reward_Cycle_Approvals (
        Approval_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Cycle_ID INTEGER, Action TEXT, Actor_ID TEXT, Role TEXT, Timestamp DATETIME,
        Comments TEXT, Prior_State TEXT, New_State TEXT, Config_Hash TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Reward_Financial_Outcomes (
        Outcome_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Cycle_ID INTEGER, Approved_Pool DECIMAL(10,2), Issued_Cost DECIMAL(10,2), Redeemed_Cost DECIMAL(10,2),
        Expired_Cost DECIMAL(10,2), Reversed_Cost DECIMAL(10,2), Sponsor_Receivable DECIMAL(10,2), Final_Profit_Impact DECIMAL(10,2),
        Currency_Code TEXT DEFAULT 'AED')''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Qualified_User_Funding (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Cycle_ID INTEGER, User_ID TEXT, Eligibility_Status TEXT, Selection_Status TEXT,
        Funding_Status TEXT, Tier_ID TEXT, Reason_Code TEXT, Rollover_Status TEXT)''')

    cursor.execute("SELECT COUNT(*) FROM Global_Users")
    if cursor.fetchone()[0] == 0:
        for act in UNIVERSAL_ACTION_REGISTRY:
            cursor.execute("INSERT INTO Action_Registry VALUES (?, ?, ?, ?, ?, ?, ?, ?)", act[1:2] + act[0:1] + act[2:])
            
        roles_list = ['Worker', 'Contractor', 'Supplier', 'Transporter']
        nationalities = ['India', 'Egypt', 'Philippines', 'Turkey']
        clusters = ['Camp-A', 'Camp-B', 'Camp-C']
        locations = ['Dubai', 'Abu Dhabi', 'Sharjah']
        
        for i in range(1, 31):
            mid = f'ID-{i}'
            primary_role = 'Worker' if i <= 15 else roles_list[i % len(roles_list)]
            secondary_roles = ""
            if primary_role == 'Worker':
                if i % 3 == 0: secondary_roles = "Captain"
                elif i % 5 == 0: secondary_roles = "Champion"
                
            nat = nationalities[i % len(nationalities)]
            cluster = clusters[i % len(clusters)]
            loc = locations[i % len(locations)]
            sub = i % 2 == 0
            cert = i % 3 == 0
            
            join_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(10, 200))
            paid_months = random.randint(0, 8) if sub else 0
            
            cursor.execute("""INSERT INTO Global_Users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                           (mid, f'User-{i}', primary_role, secondary_roles, loc, nat, cluster, True, sub, cert,
                            f'EID789{i}', f'+9715012345{i:02d}', f'DEV-FP-{i}', True, join_date, paid_months,
                            join_date.month, loc, f"Company-{i}"))
            
            cursor.execute("INSERT INTO Integrity_Profiles (Master_ID, Critical_Flag) VALUES (?, 0)", (mid,))
            
            cursor.execute("INSERT INTO Reward_Ledgers (Master_ID, Role_Ledger) VALUES (?, ?)", (mid, primary_role))
            if secondary_roles:
                cursor.execute("INSERT INTO Reward_Ledgers (Master_ID, Role_Ledger) VALUES (?, ?)", (mid, secondary_roles))
            
            cursor.execute("INSERT INTO Monthly_Qualified_Users VALUES (?, ?, ?)", (mid, 0, 0)) 
            
    conn.commit()
    conn.close()

init_db()

# --- CSV EXPORT HELPER ---
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- CORE ENGINE FUNCTIONS ---
def expire_events():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    cursor.execute("""
        UPDATE Event_Stream_Logs 
        SET Process_Status = 'EXPIRED', Reason_Code = 'VALIDITY_WINDOW_EXPIRED'
        WHERE Process_Status = 'VALIDATING' 
        AND Event_Timestamp < datetime(?, '-7 days')
    """, (now,))
    
    expired_events = cursor.execute("SELECT Master_ID, Acting_Role, Earned_Points FROM Event_Stream_Logs WHERE Process_Status = 'EXPIRED' AND Event_Timestamp < datetime(?, '-7 days')", (now,)).fetchall()
    for master_id, acting_role, points in expired_events:
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, master_id, acting_role))
        
    conn.commit()
    conn.close()

def execute_action(master_id, acting_role, action_id, target_id=None):
    expire_events()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    current_month_str = now.strftime('%Y-%m')
    rule_ver = st.session_state.get('rule_version', 'v2.0')
    
    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code, Rule_Version) VALUES (?, ?, ?, ?, ?, 'RECEIVED', 0, 'App/API Request', ?)", (master_id, acting_role, target_id, action_id, now, rule_ver))
    last_event_id = cursor.lastrowid
    
    if action_id.startswith('NR'):
        cursor.execute("SELECT Integrity_Impact FROM Action_Registry WHERE Action_ID = ?", (action_id,))
        impact_row = cursor.fetchone()
        impact = impact_row[0] if impact_row else 0
        
        cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'SETTLED', Reason_Code = 'NON_REWARDABLE' WHERE Event_ID = ?", (last_event_id,))
        msg_string = f"⚠️ Non-rewardable/Penalty event ({action_id}) logged. 0 points."
        
        if impact < 0:
            cursor.execute("SELECT Integrity_Score, Critical_Flag FROM Integrity_Profiles WHERE Master_ID = ?", (master_id,))
            s_row = cursor.fetchone()
            new_score = min(100, max(0, s_row[0] + impact))
            act_status = 'Block' if s_row[1] else ('Normal' if new_score >= 80 else 'Warning' if new_score >= 70 else 'Review' if new_score >= 50 else 'Block')
            cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ? WHERE Master_ID = ?", (new_score, act_status, master_id))
            msg_string += f" Integrity penalty applied: {impact} pts."
            
        conn.commit(); conn.close()
        return 'SETTLED', 0, msg_string

    def apply_fraud_penalty(m_id, ev_id, penalty_pts, r_code, set_critical=False):
        cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'REVERSED', Reason_Code = ? WHERE Event_ID = ?", (r_code, ev_id))
        cursor.execute("SELECT Integrity_Score, Critical_Flag FROM Integrity_Profiles WHERE Master_ID = ?", (m_id,))
        s_row = cursor.fetchone()
        new_score = min(100, max(0, s_row[0] + penalty_pts))
        is_crit = 1 if set_critical else s_row[1]
        act_status = 'Block' if is_crit else ('Normal' if new_score >= 80 else 'Warning' if new_score >= 70 else 'Review' if new_score >= 50 else 'Block')
        cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ?, Critical_Flag = ? WHERE Master_ID = ?", (new_score, act_status, is_crit, m_id))

    cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Event_Timestamp >= datetime(?, '-5 minutes')", (master_id, now))
    if cursor.fetchone()[0] >= 10:
        apply_fraud_penalty(master_id, last_event_id, -10, 'VELOCITY_SPIKE')
        conn.commit(); conn.close()
        return 'BLOCKED (Fraud)', 0, "🚨 VELOCITY_SPIKE: Last-minute velocity spike detected."

    if target_id == master_id:
        apply_fraud_penalty(master_id, last_event_id, -20, 'SELF_REFERRAL', set_critical=True)
        conn.commit(); conn.close()
        return 'BLOCKED (Fraud)', 0, "🚨 SELF_REFERRAL: Self/circular interaction detected."

    if action_id in ['SUPPLIER_ADDED', 'TRANSPORTER_ADDED'] and target_id:
        cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Target_ID = ? AND Action_ID IN ('SUPPLIER_ADDED', 'TRANSPORTER_ADDED') AND Event_ID != ?", (target_id, last_event_id))
        if cursor.fetchone()[0] > 0:
            apply_fraud_penalty(master_id, last_event_id, -10, 'DUPLICATE_PROVIDER')
            conn.commit(); conn.close()
            return 'BLOCKED (Fraud)', 0, "🚨 DUPLICATE_PROVIDER: Duplicate provider addition detected."

    if action_id == 'RETURN_TRIP':
        cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Action_ID = 'RETURN_TRIP' AND Event_Timestamp >= datetime(?, '-1 days') AND Process_Status != 'REVERSED'", (master_id, now))
        if cursor.fetchone()[0] >= 3:
            apply_fraud_penalty(master_id, last_event_id, -10, 'FAKE_BACKHAUL')
            conn.commit(); conn.close()
            return 'BLOCKED (Fraud)', 0, "🚨 FAKE_BACKHAUL: Backhaul toggle farming detected."

    if action_id in ['BUDDY_HELP', 'WORKER_REFERRAL', 'NUDGE_VALID_BID'] and target_id:
        cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Target_ID = ? AND Action_ID = ? AND Event_Timestamp >= datetime(?, '-30 days') AND Process_Status NOT IN ('REVERSED')", (master_id, target_id, action_id, now))
        if cursor.fetchone()[0] >= 2:
            apply_fraud_penalty(master_id, last_event_id, -5, 'PAIR_COOLDOWN')
            conn.commit(); conn.close()
            return 'BLOCKED (Fraud)', 0, "🚨 PAIR_COOLDOWN: Pair farming limit exceeded."

    if target_id:
        cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Target_ID = ? AND Action_ID = ? AND Event_ID != ?", (master_id, target_id, action_id, last_event_id))
        if cursor.fetchone()[0] > 0:
            cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'REVERSED', Reason_Code = 'EXACT_REPEAT_COOLDOWN' WHERE Event_ID = ?", (last_event_id,))
            conn.commit(); conn.close()
            return 'BLOCKED (Duplication)', 0, "Action Rejected: Cross-role duplication block."

    # --- BÖLÜM 16: CAPPED STATUS FIX ---
    if action_id in ['WORKER_VIDEO_WATCH', 'WORKER_QUIZ_ATTEMPT', 'PASS_QUIZ']:
        cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Action_ID = ? AND date(Event_Timestamp) = date(?) AND Process_Status NOT IN ('REVERSED', 'DISPUTED')", (master_id, action_id, now))
        if cursor.fetchone()[0] >= 1: 
            cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'ELIGIBLE', Reason_Code = 'DAILY_CAP_REACHED', Cap_Cooldown_Result = 'CAPPED' WHERE Event_ID = ?", (last_event_id,))
            conn.commit(); conn.close()
            return 'CAPPED', 0, "Daily frequency cap (1/day) reached. Raw event logged, 0 points."

    cursor.execute("SELECT Base_Points, Cooldown, Monthly_Cap FROM Action_Registry WHERE Action_ID = ?", (action_id,))
    act_meta = cursor.fetchone()
    if not act_meta: 
        cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'REVERSED', Reason_Code = 'ROLE_GATE_FAILED' WHERE Event_ID = ?", (last_event_id,))
        conn.commit(); conn.close()
        return 'Failed', 0, "Action not found in registry."
        
    base_points, cooldown, monthly_cap = act_meta
    cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'ELIGIBLE' WHERE Event_ID = ?", (last_event_id,))

    query_cooldown = "SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Action_ID = ? AND Process_Status IN ('VALIDATING', 'VALIDATED', 'OUTCOME_CONFIRMED', 'SETTLED', 'DISPUTED') AND Event_Timestamp >= datetime(?, '-' || ? || ' minutes')"
    params_cd = [master_id, action_id, now, cooldown]
    if target_id:
        query_cooldown += " AND Target_ID = ?"
        params_cd.append(target_id)
        
    cursor.execute(query_cooldown, tuple(params_cd))
    if cursor.fetchone()[0] > 0:
        cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'REVERSED', Reason_Code = 'EXACT_REPEAT_COOLDOWN' WHERE Event_ID = ?", (last_event_id,))
        conn.commit(); conn.close()
        return 'BLOCKED (Cooldown)', 0, "Action Rejected (Blocked by cooldown or duplicate record limits)."

    # --- BÖLÜM 16: CAPPED STATUS FIX ---
    cursor.execute("SELECT COUNT(*) FROM Event_Stream_Logs WHERE Master_ID = ? AND Action_ID = ? AND strftime('%Y-%m', Event_Timestamp) = ? AND Process_Status IN ('VALIDATING', 'VALIDATED', 'OUTCOME_CONFIRMED', 'SETTLED', 'DISPUTED') AND Cap_Cooldown_Result IS NULL", (master_id, action_id, current_month_str))
    if cursor.fetchone()[0] >= monthly_cap:
        cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'ELIGIBLE', Reason_Code = 'MONTHLY_CAP_REACHED', Cap_Cooldown_Result = 'CAPPED' WHERE Event_ID = ?", (last_event_id,))
        status, points, msg_string = 'CAPPED', 0, f"Monthly quota ({monthly_cap}) reached. Action processed (0 points)."
    else:
        status, points, msg_string = 'VALIDATING', base_points, f"⏳ Action received & eligible. {base_points} points waiting in 'VALIDATING' status."
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, master_id, acting_role))
        cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = 'VALIDATING', Earned_Points = ?, Reason_Code = 'OUTCOME_NOT_CONFIRMED' WHERE Event_ID = ?", (points, last_event_id))

    if action_id in ['DEMAND_CREATED', 'NUDGE_VALID_BID'] and acting_role == 'Champion' and target_id and status == 'VALIDATING':
        cursor.execute("INSERT INTO Marketplace_Attributions (Source_ID, Target_ID, Attribution_Type, Expiry_Date) VALUES (?, ?, ?, ?)", (master_id, target_id, 'CHAMPION_NUDGE', now + datetime.timedelta(days=7)))
        msg_string += " 🔗 (Champion tracking activated for target.)"

    if action_id == 'VERIFY_SIGNUP' and acting_role == 'Captain' and target_id and status == 'VALIDATING':
        cursor.execute("INSERT INTO Marketplace_Attributions (Source_ID, Target_ID, Attribution_Type, Expiry_Date) VALUES (?, ?, ?, ?)", (master_id, target_id, 'CAPTAIN_ONBOARDING', now + datetime.timedelta(days=30)))
        msg_string += " 🔗 (Captain 30-day retention tracking started.)"

    if action_id == 'REQ_SHARE_SENT' and target_id and status == 'VALIDATING':
        cursor.execute("INSERT INTO Marketplace_Attributions (Source_ID, Target_ID, Attribution_Type, Expiry_Date) VALUES (?, ?, ?, ?)", (master_id, target_id, 'PROPAGATION_CHAIN', now + datetime.timedelta(days=7)))
        msg_string += " 🔗 (Propagation Chain Started.)"
        
    if action_id == 'WORKER_REFERRAL' and target_id and status == 'VALIDATING':
        cursor.execute("INSERT INTO Marketplace_Attributions (Source_ID, Target_ID, Attribution_Type, Expiry_Date) VALUES (?, ?, ?, ?)", (master_id, target_id, 'REFERRAL_ACTIVATION', now + datetime.timedelta(days=30)))

    if action_id in ['FULFILLMENT', 'DELIVERY', 'SHARE_CHAIN_FULFILLED', 'CLOSE_REQ'] and status == 'VALIDATING':
        cursor.execute("SELECT Source_ID FROM Marketplace_Attributions WHERE Target_ID = ? AND Attribution_Type = 'CHAMPION_NUDGE' AND Expiry_Date > ?", (master_id, now))
        for attr in cursor.fetchall():
            if attr[0] != master_id:
                cursor.execute("SELECT Base_Points FROM Action_Registry WHERE Action_ID = 'CLOSURE'")
                c_pts_row = cursor.fetchone()
                if c_pts_row:
                    c_pts = c_pts_row[0]
                    cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points + ? WHERE Master_ID = ? AND Role_Ledger = 'Champion'", (c_pts, attr[0]))
                    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code, Rule_Version) VALUES (?, ?, ?, ?, ?, 'VALIDATING', ?, 'OUTCOME_NOT_CONFIRMED', ?)", (attr[0], 'Champion', master_id, 'CLOSURE', now, c_pts, rule_ver))
                    msg_string += f" 🏆 (Chain Completed: CLOSURE attributed to Champion {attr[0]}!)"

        cursor.execute("SELECT Source_ID FROM Marketplace_Attributions WHERE Target_ID = ? AND Attribution_Type = 'PROPAGATION_CHAIN' AND Expiry_Date > ?", (master_id, now))
        propagators_awarded = set()
        for attr in cursor.fetchall():
            if attr[0] != master_id and attr[0] not in propagators_awarded:
                propagators_awarded.add(attr[0]) 
                cursor.execute("SELECT Base_Points FROM Action_Registry WHERE Action_ID = 'SHARE_CHAIN_FULFILLED'")
                p_pts_row = cursor.fetchone()
                if p_pts_row:
                    p_pts = p_pts_row[0]
                    cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points + ? WHERE Master_ID = ? AND Role_Ledger = 'Worker'", (p_pts, attr[0]))
                    cursor.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Target_ID, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code, Rule_Version) VALUES (?, ?, ?, ?, ?, 'VALIDATING', ?, 'OUTCOME_NOT_CONFIRMED', ?)", (attr[0], 'Worker', master_id, 'SHARE_CHAIN_FULFILLED', now, p_pts, rule_ver))
                    msg_string += f" 🔗 (Chain Completed: Propagator {attr[0]} awarded FULFILLED!)"

    conn.commit()
    conn.close()
    return status, points, msg_string

def progress_event_lifecycle(event_id, target_status, reason_code=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT Master_ID, Acting_Role, Action_ID, Earned_Points, Process_Status FROM Event_Stream_Logs WHERE Event_ID = ?", (event_id,))
    event = cursor.fetchone()
    
    if not event: return False, "Event not found."
    master_id, acting_role, action_id, points, current_status = event
    
    if current_status == target_status:
        return False, "Idempotency Protection: Target state is the same as current state."
    
    valid_transitions = {
        'VALIDATING': ['VALIDATED', 'DISPUTED', 'REVERSED', 'EXPIRED'],
        'VALIDATED': ['OUTCOME_CONFIRMED', 'DISPUTED', 'REVERSED'],
        'OUTCOME_CONFIRMED': ['SETTLED', 'DISPUTED', 'REVERSED'],
        'DISPUTED': ['SETTLED', 'REVERSED'],
        'SETTLED': ['REVERSED'],
        'RECEIVED': ['VALIDATING', 'ELIGIBLE', 'REVERSED'],
        'ELIGIBLE': ['VALIDATING', 'REVERSED']
    }

    if target_status not in valid_transitions.get(current_status, []):
        return False, f"Invalid transition from {current_status} to {target_status}."

    if target_status == 'SETTLED':
        cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ?, Settled_Points = Settled_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, points, master_id, acting_role))
        reason_code = reason_code if reason_code else "APPROVED_CLEAN"
        
        cursor.execute("SELECT Integrity_Impact FROM Action_Registry WHERE Action_ID = ?", (action_id,))
        impact = cursor.fetchone()[0]
        if impact != 0:
            cursor.execute("SELECT Integrity_Score, Critical_Flag FROM Integrity_Profiles WHERE Master_ID = ?", (master_id,))
            s_row = cursor.fetchone()
            new_score = min(100, max(0, s_row[0] + impact)) 
            act_status = 'Block' if s_row[1] else ('Normal' if new_score >= 80 else 'Warning' if new_score >= 70 else 'Review' if new_score >= 50 else 'Block')
            cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ? WHERE Master_ID = ?", (new_score, act_status, master_id))
            
    elif target_status == 'REVERSED':
        if current_status in ['VALIDATING', 'VALIDATED', 'OUTCOME_CONFIRMED', 'DISPUTED']:
            cursor.execute("UPDATE Reward_Ledgers SET Pending_Points = Pending_Points - ?, Reversed_Points = Reversed_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, points, master_id, acting_role))
        elif current_status == 'SETTLED':
            cursor.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points - ?, Reversed_Points = Reversed_Points + ? WHERE Master_ID = ? AND Role_Ledger = ?", (points, points, master_id, acting_role))
            
        reason_code = reason_code if reason_code else "ACTOR_FAULT"
        
        penalty = 0
        set_critical = False
        if reason_code == 'SUPPLIER_NON_FULFIL': penalty = -15
        elif reason_code == 'TRIP_CANCEL_ACTOR_FAULT': penalty = -10
        elif reason_code == 'POST_SETTLEMENT_FRAUD': penalty = -20; set_critical = True
        elif reason_code == 'MEGA_POST_AWARD_REVIEW': set_critical = True
        
        if penalty != 0 or set_critical:
            cursor.execute("SELECT Integrity_Score, Critical_Flag FROM Integrity_Profiles WHERE Master_ID = ?", (master_id,))
            s_row = cursor.fetchone()
            if s_row:
                new_score = min(100, max(0, s_row[0] + penalty))
                is_crit = 1 if set_critical else s_row[1]
                act_status = 'Block' if is_crit else ('Normal' if new_score >= 80 else 'Warning' if new_score >= 70 else 'Review' if new_score >= 50 else 'Block')
                cursor.execute("UPDATE Integrity_Profiles SET Integrity_Score = ?, Action_Status = ?, Critical_Flag = ? WHERE Master_ID = ?", (new_score, act_status, is_crit, master_id))

    cursor.execute("UPDATE Event_Stream_Logs SET Process_Status = ?, Reason_Code = ? WHERE Event_ID = ?", (target_status, reason_code, event_id))
    conn.commit()
    conn.close()
    return True, f"Event {event_id} successfully moved to {target_status}."

def get_normalized_weights(has_sub, has_cert):
    base_weights = {"Marketplace": 30, "Referral": 20, "Habit": 15, "Subscription": 20, "Certification": 15}
    active_weights = {k: base_weights[k] for k in ["Marketplace", "Referral", "Habit"]}
    if has_sub: active_weights["Subscription"] = base_weights["Subscription"]
    if has_cert: active_weights["Certification"] = base_weights["Certification"]
    total = sum(active_weights.values())
    return {k: round((v / total) * 100, 2) for k, v in active_weights.items()}

# --- STREAMLIT DASHBOARD UI ---
st.title("🌐 Buddy Rewards - Ultimate Ecosystem Engine")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["⚙️ Setup", "👥 Users", "🚀 Actions", "🏆 Mega & Fairness", "💰 Finance & Economics", "📜 Logs", "📊 Reports"])

with tab1:
    st.header("System Dynamics & Universal Registry")
    
    st.subheader("Simulation & Configuration Controls")
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
    
    with ctrl_col1:
        st.session_state.rule_version = st.text_input("Rule Version", st.session_state.rule_version)
    with ctrl_col2:
        new_seed = st.number_input("Random Seed", value=st.session_state.random_seed)
        if new_seed != st.session_state.random_seed:
            st.session_state.random_seed = new_seed
            random.seed(st.session_state.random_seed)
            st.success(f"Seed updated to {new_seed}")
    with ctrl_col3:
        st.session_state.rollover_mode = st.toggle("ROLLOVER_MODE", st.session_state.rollover_mode)
        st.metric("Current Simulation Month", st.session_state.current_simulation_month)

    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Universal Action Registry (Editable)")
        df_registry = pd.read_sql_query("SELECT * FROM Action_Registry", sqlite3.connect(DB_FILE))
        edited_registry = st.data_editor(df_registry, use_container_width=True)
        if st.button("Save Registry Configuration"):
            conn = sqlite3.connect(DB_FILE)
            edited_registry.to_sql("Action_Registry", conn, if_exists="replace", index=False)
            conn.execute("INSERT INTO Audit_Trail (Config_Change, Timestamp, Reason) VALUES ('Action_Registry_Updated', ?, 'Admin runtime edit')", (datetime.datetime.now(),))
            conn.commit()
            conn.close()
            st.success("Action registry rules updated runtime!")
            
    with c2:
        st.markdown("---")
        st.subheader("System Reset & Archive")
        st.caption("No destructive editing allowed (Bölüm 15.5). Archive preserves audit trail.")
        if st.button("🗄️ Archive & Soft Reset", type="primary", use_container_width=True):
            if os.path.exists(DB_FILE):
                archive_name = f"buddy_archive_{int(datetime.datetime.now().timestamp())}.db"
                os.rename(DB_FILE, archive_name)
                st.success(f"Database archived to {archive_name}")
            st.session_state.current_simulation_month = 1
            st.session_state.cycle_status = "DRAFT"
            init_db()
            st.rerun()

with tab2:
    st.header("Ecosystem Actors & Security")
    
    if st.button("🚀 Inject 10,000 Synthetic Users (Load Test)"):
        with st.spinner("Injecting 10,000 users... Please wait."):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            base_count = cursor.execute("SELECT COUNT(*) FROM Global_Users").fetchone()[0]
            new_users = []
            new_integrity = []
            new_ledgers = []
            new_qualified = []
            now = datetime.datetime.now()
            roles = ['Worker', 'Contractor', 'Supplier', 'Transporter']
            locations = ['Dubai', 'Abu Dhabi', 'Sharjah']
            for i in range(base_count+1, base_count+10001):
                mid = f'ID-{i}'
                prole = roles[i % 4]
                loc = locations[i % 3]
                new_users.append((mid, f'User-{i}', prole, "", loc, 'India', 'Camp-A', True, False, False, f'EID{i}', f'+97150{i:07d}', f'DEV-FP-{i}', True, now, 0, now.month, loc, f'Company-{i}'))
                new_integrity.append((mid, 100, 'Normal', 0))
                new_ledgers.append((mid, prole, 0, 0, 0, None, st.session_state.rule_version, None))
                new_qualified.append((mid, 0.0, 0.0))
                
            cursor.executemany("INSERT INTO Global_Users VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", new_users)
            cursor.executemany("INSERT INTO Integrity_Profiles (Master_ID, Integrity_Score, Action_Status, Critical_Flag) VALUES (?,?,?,?)", new_integrity)
            cursor.executemany("INSERT INTO Reward_Ledgers (Master_ID, Role_Ledger, Pending_Points, Settled_Points, Reversed_Points, Event_ID, Rule_Version, Reason_Code) VALUES (?,?,?,?,?,?,?,?)", new_ledgers)
            cursor.executemany("INSERT INTO Monthly_Qualified_Users (Master_ID, Total_Score, Rollover_Bonus) VALUES (?,?,?)", new_qualified)
            conn.commit()
            conn.close()
        st.success("10,000 synthetic users injected successfully!")
        
    df_users = pd.read_sql_query("SELECT Master_ID, Primary_Role, Secondary_Roles, EID_Verified, Has_Certification, Continuous_Paid_Months, Integrity_Score, Action_Status, Critical_Flag FROM Global_Users JOIN Integrity_Profiles USING(Master_ID)", sqlite3.connect(DB_FILE))
    def color_status(val):
        color = 'green' if val == 'Normal' else 'orange' if val == 'Warning' else 'red'
        return f'color: {color}; font-weight: bold'
    st.dataframe(df_users.style.map(color_status, subset=['Action_Status']), use_container_width=True)

    st.markdown("---")
    st.subheader("🕵️‍♂️ External Fraud & Abuse Signals (I01-I15)")
    st.caption("Simulate AI/External microservice detection for complex fraud patterns (e.g., Collusion, Device Clusters). Applies Critical Flag and reverses all points.")
    f_col1, f_col2, f_col3 = st.columns([1,2,1])
    users_list = df_users['Master_ID'].tolist()
    if len(users_list) > 0:
        f_uid = f_col1.selectbox("Select Actor:", users_list, key='f_uid')
        f_code = f_col2.selectbox("Fraud Pattern:", [
            "I01_DUPLICATE_IDENTITY", "I04_FAKE_DEMAND", "I06_COLLUSION", "I08_FAKE_ONBOARDING", 
            "I09_FAKE_LIQUIDITY", "I11_BUNDLE_MANIPULATION", "I12_KYC_MISMATCH", "I13_POD_REUSE", 
            "I14_RATING_MANIPULATION", "I15_ADMIN_ABUSE"
        ])
        if f_col3.button("🚨 Apply Fraud Flag & Reverse", use_container_width=True):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("UPDATE Integrity_Profiles SET Integrity_Score = 0, Action_Status = 'Block', Critical_Flag = 1 WHERE Master_ID = ?", (f_uid,))
            cur.execute("UPDATE Reward_Ledgers SET Reversed_Points = Reversed_Points + Settled_Points + Pending_Points, Settled_Points = 0, Pending_Points = 0 WHERE Master_ID = ?", (f_uid,))
            cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code, Rule_Version) VALUES (?, 'System', 'FRAUD_INTERVENTION', ?, 'REVERSED', 0, ?, ?)", (f_uid, datetime.datetime.now(), f_code, st.session_state.rule_version))
            conn.commit()
            conn.close()
            st.success(f"Critical Flag applied to {f_uid} for {f_code}. All points reversed.")
            st.rerun()

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
        acts = pd.read_sql_query(f"SELECT Action_ID FROM Action_Registry WHERE Role LIKE '%{a_role}%' OR Role = 'All'", sqlite3.connect(DB_FILE))['Action_ID'].tolist()
        act = st.selectbox("Action Type:", acts)
        t_id = st.text_input("Target ID (Optional - For Nudge/Chain scenarios):")
        
        if st.button("Execute Action"):
            status, earned, msg = execute_action(u_id, a_role, act, t_id if t_id else None)
            if status == 'VALIDATING': 
                st.warning(msg) 
            elif status == 'CAPPED': 
                st.info(msg) 
            else:
                if status == 'SETTLED' or status == 'RECEIVED': 
                    st.success(msg)
                else: 
                    st.error(msg)
            
        st.markdown("---")
        st.caption("Inject Worker test data to exceed monthly minimums (QA Multi-Day Simulator)")
        if st.button("Simulate 30/30/15 Minimums for Top 5 Workers"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            workers = pd.read_sql_query("SELECT Master_ID FROM Global_Users WHERE Primary_Role='Worker'", conn)['Master_ID'].tolist()
            now = datetime.datetime.now()
            rule_ver = st.session_state.rule_version
            for w in workers[:5]: 
                for day in range(30):
                    sim_date = now - datetime.timedelta(days=day)
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Worker', 'WORKER_VIDEO_WATCH', ?, 'SETTLED', 5, ?)", (w, sim_date, rule_ver))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 5 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Worker', 'WORKER_QUIZ_ATTEMPT', ?, 'SETTLED', 5, ?)", (w, sim_date, rule_ver))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 5 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
                for day in range(15): 
                    sim_date = now - datetime.timedelta(days=day)
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Worker', 'WORKER_REFERRAL', ?, 'SETTLED', 10, ?)", (w, sim_date, rule_ver))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 10 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
            conn.commit()
            conn.close()
            st.success("Successfully pushed 30/30/15 Multi-Day SETTLED events for top 5 workers!")
            
    with col2:
        st.subheader("2. Admin Resolution Desk & Lifecycle Management")
        
        if 'lifecycle_msg' in st.session_state and st.session_state.lifecycle_msg:
            st.success(st.session_state.lifecycle_msg)
            st.session_state.lifecycle_msg = "" 
            
        if 'lifecycle_error' in st.session_state and st.session_state.lifecycle_error:
            st.error(st.session_state.lifecycle_error)
            st.session_state.lifecycle_error = ""

        conn = sqlite3.connect(DB_FILE)
        pending_val = pd.read_sql_query("SELECT Event_ID, Action_ID, Process_Status, Earned_Points FROM Event_Stream_Logs WHERE Process_Status IN ('VALIDATING', 'VALIDATED', 'OUTCOME_CONFIRMED', 'SETTLED')", conn)
        pending_disp = pd.read_sql_query("SELECT Event_ID, Action_ID, Reason_Code FROM Event_Stream_Logs WHERE Process_Status = 'DISPUTED'", conn)
        conn.close()
        
        st.markdown("#### ⏳ Lifecycle Progression Pipeline")
        if len(pending_val) > 0:
            l_col1, l_col2, l_col3 = st.columns([2,1,1])
            l_ev_id = l_col1.selectbox("Select Pending Event", pending_val['Event_ID'].astype(str) + " (" + pending_val['Process_Status'] + ")", key="l_sel").split(" ")[0]
            
            target_opts = ['VALIDATED', 'OUTCOME_CONFIRMED', 'SETTLED', 'DISPUTED', 'REVERSED']
            selected_target = l_col2.selectbox("Move to:", target_opts, key="l_tgt")
            
            if l_col3.button("Execute Transition", use_container_width=True): 
                success, msg = progress_event_lifecycle(int(l_ev_id), selected_target)
                if success: 
                    st.session_state.lifecycle_msg = f"🚀 {msg}"
                else: 
                    st.session_state.lifecycle_error = f"❌ {msg}"
                st.rerun()
        else: st.write("No active events in pipeline.")
            
        st.markdown("---")
        st.markdown("#### ⚠️ Admin Decision Desk (Disputed)")
        if len(pending_disp) > 0:
            d_col1, d_col2 = st.columns(2)
            d_ev_id = d_col1.selectbox("Select Disputed Event", pending_disp['Event_ID'].tolist(), key="d_sel")
            r_code = d_col2.selectbox("Reason Code", FLAT_REASON_CODES, key="r_code")
            dr_col1, dr_col2 = st.columns(2)
            if dr_col1.button("✅ Reject Dispute (Settle)", use_container_width=True): 
                success, msg = progress_event_lifecycle(d_ev_id, 'SETTLED', r_code)
                if success: st.session_state.lifecycle_msg = f"✅ Dispute Rejected: {msg}"
                else: st.session_state.lifecycle_error = msg
                st.rerun()
            if dr_col2.button("❌ Cancel Event (Reverse)", use_container_width=True): 
                success, msg = progress_event_lifecycle(d_ev_id, 'REVERSED', r_code)
                if success: st.session_state.lifecycle_msg = f"❌ Event Cancelled: {msg}"
                else: st.session_state.lifecycle_error = msg
                st.rerun()
        else: st.write("No disputes awaiting decision.")

with tab4:
    st.header("Reward Qualification and Fairness Engine")
    t4_col1, t4_col2 = st.columns(2)
    
    with t4_col1:
        st.markdown("### 📅 Monthly Selection Engine")
        c_cap1, c_cap2, c_cap3, c_cap4 = st.columns(4)
        t_cap = c_cap1.number_input("Total Winner Cap:", min_value=1, max_value=20, value=5)
        nat_cap = c_cap2.number_input("Max per Nationality:", min_value=1, max_value=10, value=2)
        camp_cap = c_cap3.number_input("Max per Camp:", min_value=1, max_value=10, value=2)
        geo_cap = c_cap4.number_input("Max per Location:", min_value=1, max_value=10, value=2)
        
        if st.button("🚀 Run Monthly Engine", type="primary"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            curr_month = st.session_state.current_simulation_month
            rule_ver = st.session_state.rule_version
            
            workers_list = pd.read_sql_query("SELECT Master_ID FROM Global_Users WHERE Primary_Role='Worker'", conn)['Master_ID'].tolist()
            base_date = datetime.datetime.now()
            
            for w in workers_list[:5]:
                for day in range(30):
                    sim_date = base_date - datetime.timedelta(days=day)
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Worker', 'WORKER_VIDEO_WATCH', ?, 'SETTLED', 5, ?)", (w, sim_date, rule_ver))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 5 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Worker', 'WORKER_QUIZ_ATTEMPT', ?, 'SETTLED', 5, ?)", (w, sim_date, rule_ver))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 5 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
                
                for day in range(15):
                    sim_date = base_date - datetime.timedelta(days=day)
                    cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Worker', 'WORKER_REFERRAL', ?, 'SETTLED', 10, ?)", (w, sim_date, rule_ver))
                    cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 10 WHERE Master_ID=? AND Role_Ledger='Worker'", (w,))
            
            now_ts = datetime.datetime.now()
            captains_list = pd.read_sql_query("SELECT Master_ID FROM Global_Users WHERE Secondary_Roles LIKE '%Captain%' OR Primary_Role='Captain'", conn)['Master_ID'].tolist()
            for c in captains_list:
                cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Captain', 'VERIFY_SIGNUP', ?, 'SETTLED', 2, ?)", (c, now_ts, rule_ver))
                cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Captain', 'ACTIVE_CLUSTER', ?, 'SETTLED', 25, ?)", (c, now_ts, rule_ver))
                cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 27 WHERE Master_ID=? AND Role_Ledger='Captain'", (c,))
                
            champions_list = pd.read_sql_query("SELECT Master_ID FROM Global_Users WHERE Secondary_Roles LIKE '%Champion%' OR Primary_Role='Champion'", conn)['Master_ID'].tolist()
            for ch in champions_list:
                cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Champion', 'DEMAND_CREATED', ?, 'SETTLED', 20, ?)", (ch, now_ts, rule_ver))
                cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Rule_Version) VALUES (?, 'Champion', 'CLOSURE', ?, 'SETTLED', 50, ?)", (ch, now_ts, rule_ver))
                cur.execute("UPDATE Reward_Ledgers SET Settled_Points = Settled_Points + 70 WHERE Master_ID=? AND Role_Ledger='Champion'", (ch,))

            users_df = pd.read_sql_query("""
                SELECT u.Master_ID, u.Primary_Role, u.Nationality, u.Labor_Cluster, u.Location,
                       u.Has_Subscription, u.Has_Certification, u.Join_Date, 
                       i.Integrity_Score, i.Action_Status, i.Critical_Flag,
                       m.Rollover_Bonus
                FROM Global_Users u 
                JOIN Integrity_Profiles i ON u.Master_ID = i.Master_ID 
                JOIN Monthly_Qualified_Users m ON u.Master_ID = m.Master_ID
            """, conn)
            
            qualified_pool, disqualified_pool = [], []
            for _, u in users_df.iterrows():
                mid, role = u['Master_ID'], u['Primary_Role']
                
                if u['Integrity_Score'] < 50 or u['Action_Status'] == 'Block' or u['Critical_Flag']:
                    disqualified_pool.append({'Master_ID': mid, 'Reason': 'INTEGRITY_FAILED'})
                    cur.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = 0 WHERE Master_ID = ?", (mid,))
                    continue
                
                is_qualified = True
                
                # BÖLÜM 16: CAPPED durumları artık Cap_Cooldown_Result içinde saklanıyor.
                cur.execute("SELECT Action_ID, COUNT(*) FROM Event_Stream_Logs WHERE Master_ID=? AND (Process_Status='SETTLED' OR Cap_Cooldown_Result='CAPPED') GROUP BY Action_ID", (mid,))
                counts = dict(cur.fetchall())

                if role == 'Worker':
                    if counts.get('WORKER_VIDEO_WATCH',0)<30 or counts.get('WORKER_QUIZ_ATTEMPT',0)<30 or counts.get('WORKER_REFERRAL',0)<15:
                        is_qualified = False
                        disqualified_pool.append({'Master_ID': mid, 'Reason': 'HABIT_VIDEO_MIN_FAILED'})
                
                elif role == 'Contractor':
                    if counts.get('POST_REQ', 0) < 1:
                        is_qualified = False
                        disqualified_pool.append({'Master_ID': mid, 'Reason': 'ROLE_GATE_FAILED'})
                
                elif role == 'Supplier':
                    if counts.get('PROFILE', 0) < 1 and counts.get('QUOTE', 0) < 1:
                        is_qualified = False
                        disqualified_pool.append({'Master_ID': mid, 'Reason': 'ROLE_GATE_FAILED'})
                
                elif role == 'Transporter':
                    if counts.get('RETURN_TRIP', 0) < 1 and counts.get('DELIVERY', 0) < 1:
                        is_qualified = False
                        disqualified_pool.append({'Master_ID': mid, 'Reason': 'ROLE_GATE_FAILED'})
                        
                elif role == 'Captain':
                    if counts.get('VERIFY_SIGNUP', 0) < 1 or (counts.get('ACTIVE_CLUSTER', 0) == 0 and counts.get('HIGH_RETENTION_CLUSTER', 0) == 0):
                        is_qualified = False
                        disqualified_pool.append({'Master_ID': mid, 'Reason': 'ROLE_GATE_FAILED'})
                        
                elif role == 'Champion':
                    if counts.get('DEMAND_CREATED', 0) < 1 and counts.get('RESOLVE_UNMET_DEMAND', 0) < 1 and counts.get('CLOSURE', 0) < 1:
                        is_qualified = False
                        disqualified_pool.append({'Master_ID': mid, 'Reason': 'ROLE_GATE_FAILED'})

                if not is_qualified:
                    cur.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = 0 WHERE Master_ID = ?", (mid,))
                    continue

                has_sub_effective = u['Has_Subscription'] if curr_month > 3 else False
                weights = get_normalized_weights(has_sub_effective, u['Has_Certification'])
                
                cur.execute("""
                    SELECT a.Category, COALESCE(SUM(e.Earned_Points), 0)
                    FROM Event_Stream_Logs e
                    JOIN Action_Registry a ON e.Action_ID = a.Action_ID
                    WHERE e.Master_ID = ? AND e.Process_Status = 'SETTLED'
                    GROUP BY a.Category
                """, (mid,))
                cat_points = dict(cur.fetchall())
                
                habit_pts = cat_points.get('Retention', 0)
                ref_pts = cat_points.get('Growth', 0) + cat_points.get('Propagation', 0)
                mkt_pts = sum([cat_points.get(c, 0) for c in ['Trigger', 'Response', 'Completion', 'Quality', 'Efficiency', 'Logistics']])
                trust_pts = cat_points.get('Trust', 0)
                
                w_habit = weights.get('Habit', 0) / 100.0
                w_ref = weights.get('Referral', 0) / 100.0
                w_mkt = weights.get('Marketplace', 0) / 100.0
                w_sub = weights.get('Subscription', 0) / 100.0
                w_cert = weights.get('Certification', 0) / 100.0
                
                base_score = float(habit_pts * (1 + w_habit)) + \
                             float(ref_pts * (1 + w_ref)) + \
                             float(mkt_pts * (1 + w_mkt)) + \
                             float(trust_pts * (1 + w_sub + w_cert))

                qualified_pool.append({
                    'Master_ID': mid, 
                    'Nationality': u['Nationality'], 
                    'Camp': u['Labor_Cluster'], 
                    'Location': u['Location'],
                    'Final_Score': round(base_score + float(u['Rollover_Bonus']), 2)
                })
                
            qualified_pool.sort(key=lambda x: x['Final_Score'], reverse=True)
            df_past = pd.read_sql_query("SELECT * FROM Past_Winners", conn)
            
            winners, rollovers = [], []
            nat_counts, camp_counts, loc_counts = {}, {}, {}
            
            new_cap = t_cap
            m1_cap, m2_cap, gen_rep_cap = 0, 0, 0
            if curr_month == 3:
                new_cap = max(1, int(t_cap * 0.8))
                m1_cap = t_cap - new_cap
            elif curr_month == 4:
                new_cap = max(1, int(t_cap * 0.8))
                m1_cap = max(1, int(t_cap * 0.1))
                m2_cap = t_cap - new_cap - m1_cap
            elif curr_month >= 5:
                new_cap = max(1, int(t_cap * 0.8))
                gen_rep_cap = t_cap - new_cap
                
            c_new, c_m1, c_m2, c_rep = 0, 0, 0, 0

            for cand in qualified_pool:
                mid, nat, camp, loc = cand['Master_ID'], cand['Nationality'], cand['Camp'], cand['Location']
                cand_past_wins = df_past[df_past['Master_ID'] == mid]['Win_Month'].tolist()
                is_new = len(cand_past_wins) == 0
                
                if curr_month == 2 and 1 in cand_past_wins:
                    cand['Reason_Code'] = 'REPEAT_COHORT_EXCLUDED'; rollovers.append(cand); continue
                if curr_month >= 5 and (curr_month - 1) in cand_past_wins:
                    cand['Reason_Code'] = 'EXACT_REPEAT_COOLDOWN'; rollovers.append(cand); continue
                    
                cohort_approved = False
                track_var = ""
                
                if is_new:
                    if c_new < new_cap: cohort_approved = True; track_var = "new"
                    else: cand['Reason_Code'] = 'WINNER_CAP_FULL'
                else:
                    if curr_month <= 2: 
                        cand['Reason_Code'] = 'REPEAT_COHORT_EXCLUDED'
                    elif curr_month == 3:
                        if 1 in cand_past_wins and c_m1 < m1_cap: cohort_approved = True; track_var = "m1"
                        else: cand['Reason_Code'] = 'REPEAT_COHORT_EXCLUDED'
                    elif curr_month == 4:
                        if 2 in cand_past_wins and 1 not in cand_past_wins and c_m2 < m2_cap: cohort_approved = True; track_var = "m2"
                        elif 1 in cand_past_wins and c_m1 < m1_cap: cohort_approved = True; track_var = "m1"
                        else: cand['Reason_Code'] = 'REPEAT_COHORT_EXCLUDED'
                    else:
                        if c_rep < gen_rep_cap: cohort_approved = True; track_var = "rep"
                        else: cand['Reason_Code'] = 'REPEAT_COHORT_EXCLUDED'
                        
                if not cohort_approved:
                    rollovers.append(cand); continue
                    
                if nat_counts.get(nat, 0) >= nat_cap: 
                    cand['Reason_Code'] = 'NATIONALITY_CAP'; rollovers.append(cand); continue
                if camp_counts.get(camp, 0) >= camp_cap: 
                    cand['Reason_Code'] = 'CAMP_CAP'; rollovers.append(cand); continue
                if loc_counts.get(loc, 0) >= geo_cap:
                    cand['Reason_Code'] = 'GEOGRAPHY_CAP'; rollovers.append(cand); continue
                    
                if len(winners) < t_cap:
                    cand['Reason_Code'] = 'APPROVED'
                    winners.append(cand)
                    nat_counts[nat] = nat_counts.get(nat, 0) + 1
                    camp_counts[camp] = camp_counts.get(camp, 0) + 1
                    loc_counts[loc] = loc_counts.get(loc, 0) + 1
                    
                    if track_var == "new": c_new += 1
                    elif track_var == "m1": c_m1 += 1
                    elif track_var == "m2": c_m2 += 1
                    elif track_var == "rep": c_rep += 1
                    
                    cur.execute("INSERT INTO Past_Winners (Master_ID, Win_Month) VALUES (?, ?)", (mid, curr_month))
                    cur.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = 0 WHERE Master_ID = ?", (mid,))
                else: 
                    cand['Reason_Code'] = 'WINNER_CAP_FULL'; rollovers.append(cand)
                    
            if st.session_state.rollover_mode:
                for r in rollovers: 
                    cur.execute("UPDATE Monthly_Qualified_Users SET Rollover_Bonus = CASE WHEN Rollover_Bonus + 5 > 15 THEN 15 ELSE Rollover_Bonus + 5 END WHERE Master_ID = ?", (r['Master_ID'],))
            
            conn.commit()
            conn.close()
            st.session_state.current_simulation_month += 1
            st.success(f"Month completed! Winners: {len(winners)}")
            if winners: st.dataframe(pd.DataFrame(winners)[['Master_ID', 'Nationality', 'Camp', 'Location', 'Final_Score', 'Reason_Code']], use_container_width=True)

    with t4_col2:
        st.markdown("### 🌟 Mega Rewards Engine")
        m_cert = st.checkbox("Require Certification (T02)", value=True)
        m_excl = st.checkbox("Exclude Monthly Winners", value=True)
        m_grace = st.checkbox("Apply 1-Month Grace", value=False)
        
        mc_col1, mc_col2 = st.columns(2)
        mega_cycle = mc_col1.selectbox("Mega Cycle:", [1, 2, 3], format_func=lambda x: f"Cycle {x} (M4-{x*6 if x<3 else 18})")
        mega_cap = mc_col2.number_input("Mega Winner Cap:", min_value=1, value=3)
        
        if st.button("Inject 6-Month Mega Data for ID-1", type="secondary"):
            conn, now = sqlite3.connect(DB_FILE), datetime.datetime.now()
            cur = conn.cursor()
            rule_ver = st.session_state.rule_version
            for a, t in MEGA_TARGETS.items():
                for _ in range(t): cur.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Rule_Version) VALUES ('ID-1', 'Worker', ?, ?, 'SETTLED', ?)", (a, now, rule_ver))
            cur.execute("UPDATE Global_Users SET EID_Verified=1, Has_Certification=1, Continuous_Paid_Months=15 WHERE Master_ID='ID-1'")
            cur.execute("UPDATE Integrity_Profiles SET Integrity_Score=100, Action_Status='Normal', Critical_Flag=0 WHERE Master_ID='ID-1'")
            conn.commit()
            conn.close()
            st.success("Mega data injected for ID-1!")

        if st.button("🚀 Run Mega Qualification & Selection", type="primary"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            workers = pd.read_sql_query("SELECT Master_ID, EID_Verified, Has_Certification, Continuous_Paid_Months FROM Global_Users WHERE Primary_Role='Worker'", conn)
            mega_qualified, mega_failed = [], []
            
            if mega_cycle == 1: req_months = 2 if m_grace else 3
            elif mega_cycle == 2: req_months = 8 if m_grace else 9
            else: req_months = 14 if m_grace else 15
            
            for _, w in workers.iterrows():
                mid, fail_reason = w['Master_ID'], None
                if not w['EID_Verified']: fail_reason = 'MEGA_EID_FAILED'
                elif m_cert and not w['Has_Certification']: fail_reason = 'MEGA_CERT_FAILED'
                elif w['Continuous_Paid_Months'] < req_months: fail_reason = 'MEGA_SUBSCRIPTION_FAILED'
                else:
                    cur.execute("SELECT Integrity_Score, Action_Status, Critical_Flag FROM Integrity_Profiles WHERE Master_ID=?", (mid,))
                    i_score, i_status, c_flag = cur.fetchone()
                    if i_score < 50 or i_status == 'Block' or c_flag: fail_reason = 'MEGA_INTEGRITY_FAILED'
                
                if not fail_reason and m_excl:
                    cur.execute("SELECT COUNT(*) FROM Past_Winners WHERE Master_ID=?", (mid,))
                    if cur.fetchone()[0] > 0: fail_reason = 'MEGA_MONTHLY_WINNER_EXCLUDED'
                        
                if not fail_reason:
                    cur.execute("SELECT Action_ID, COUNT(*) FROM Event_Stream_Logs WHERE Master_ID=? AND (Process_Status='SETTLED' OR Cap_Cooldown_Result='CAPPED') GROUP BY Action_ID", (mid,))
                    counts = dict(cur.fetchall())
                    for req_a, req_t in MEGA_TARGETS.items():
                        if counts.get(req_a, 0) < req_t: fail_reason = 'MEGA_COUNTS_FAILED'; break
                            
                if fail_reason: 
                    mega_failed.append({'Master_ID': mid, 'Reason_Code': fail_reason})
                else: 
                    cur.execute("SELECT COALESCE(SUM(Earned_Points), 0) FROM Event_Stream_Logs WHERE Master_ID=? AND Process_Status='SETTLED'", (mid,))
                    base_mega_score = cur.fetchone()[0]
                    mega_qualified.append({'Master_ID': mid, 'Mega_Score': float(base_mega_score), 'Reason_Code': 'MEGA_APPROVED'})
            
            mega_qualified.sort(key=lambda x: x['Mega_Score'], reverse=True)
            
            final_mega_winners = []
            for i, cand in enumerate(mega_qualified):
                if i < mega_cap:
                    cand['Reason_Code'] = 'MEGA_SELECTED (Pending Admin Approval)'
                    final_mega_winners.append(cand)
                else:
                    cand['Reason_Code'] = 'MEGA_CAP_FULL'
                    mega_failed.append(cand)
                    
            conn.close()
            st.success(f"Mega Cycle {mega_cycle} Evaluation & Selection Completed!")
            if final_mega_winners: st.dataframe(pd.DataFrame(final_mega_winners), use_container_width=True)
            if mega_failed: st.dataframe(pd.DataFrame(mega_failed), use_container_width=True)

with tab5:
    st.header("Financial & Economics Control Centre")
    
    admin_role = st.selectbox("Simulate Login Role (12.9):", [
        "Rewards Operations Maker", 
        "Product/Admin Reviewer", 
        "Finance Approver", 
        "Final Authorised Admin", 
        "QA / Auditor", 
        "System Service Account"
    ])
    
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        st.subheader("Income & Costs (12.1)")
        collected_rev = st.number_input("Net Collected Revenue", value=120000)
        sponsor_funding = st.number_input("Cash Sponsorship Funding", value=15000)
        var_costs = st.number_input("Variable Operating Costs", value=20000)
        refunds = st.number_input("Refunds", value=2000)
        gateway_costs = st.number_input("Gateway Costs", value=3000)
        fulfillment_costs = st.number_input("Reward Fulfilment Costs", value=1000)
        
    with f_col2:
        st.subheader("Admin Guardrails (12.5)")
        budget_ceil = st.number_input("Budget Ceiling (Max Limit)", value=40000)
        policy_limit = st.number_input("Policy Reward Limit (AED)", value=35000) 
        
        profit_mode = st.selectbox("Profit Policy Mode (FIN-002)", ["Hybrid", "Fixed", "Percentage"])
        profit_margin = st.slider("Required Profit Margin (%)", 10, 50, 20)
        fixed_floor = st.number_input("Fixed Profit Floor (AED)", value=15000)
        mega_prov = st.number_input("Mega Rewards Provision (AED)", value=5000)
        
        refund_reserve = st.number_input("Refund/Chargeback Reserve (FIN-007)", value=2000)
        unused_budget = st.selectbox("Unused Budget Treatment (FIN-013)", ["Expire", "Carry forward", "Transfer to Mega"])
        redemption_rate = st.slider("Redemption-Rate Assumption (%) (FIN-014)", 10, 100, 85) / 100.0
        
    net_revenue_calc = collected_rev + sponsor_funding
    net_contribution = net_revenue_calc - var_costs - refunds - gateway_costs - fulfillment_costs
    
    if profit_mode == "Fixed":
        req_profit = fixed_floor
    elif profit_mode == "Percentage":
        req_profit = (profit_margin / 100.0) * net_revenue_calc
    else:
        req_profit = max(fixed_floor, (profit_margin / 100.0) * net_revenue_calc)
        
    max_affordable = max(0, net_contribution - mega_prov - req_profit - refund_reserve)
    approved_pool = min(budget_ceil, max_affordable, policy_limit)
    
    with f_col3:
        st.subheader("Calculated Pools")
        st.metric("Net Contribution", f"AED {net_contribution:,.2f}")
        st.metric("Required Profit Reserve", f"AED {req_profit:,.2f}")
        st.metric("Max Affordable Reward Pool", f"AED {max_affordable:,.2f}")
        st.metric("FINAL APPROVED POOL", f"AED {approved_pool:,.2f}")
        
    st.markdown("---")
    st.subheader("Distribution Strategies & Tiers (12.4, 12.6)")
    
    st.caption("**Funding Sources Supported:** 1. Buddy-funded | 2. Sponsor-funded | 3. Co-funded | 4. Partner in-kind | 5. Internal digital benefit | 6. Fee waiver")
    
    scenarios = {
        "Conservative (Profit-Oriented)": {"T1": 0.10, "T2": 0.30, "T3": 0.50, "T4": 0.10},
        "Balanced": {"T1": 0.25, "T2": 0.40, "T3": 0.25, "T4": 0.10},
        "Growth (Widespread Adoption)": {"T1": 0.50, "T2": 0.30, "T3": 0.15, "T4": 0.05},
        "Custom (Manual Override)": None
    }
    
    selected_strat = st.radio("Choose Distribution Strategy:", list(scenarios.keys()), horizontal=True)
    
    if selected_strat == "Custom (Manual Override)":
        c_sl1, c_sl2, c_sl3, c_sl4 = st.columns(4)
        pct_t1 = c_sl1.number_input("Tier 1 %", 0.0, 1.0, 0.25)
        pct_t2 = c_sl2.number_input("Tier 2 %", 0.0, 1.0, 0.40)
        pct_t3 = c_sl3.number_input("Tier 3 %", 0.0, 1.0, 0.25)
        pct_t4 = c_sl4.number_input("Tier 4 %", 0.0, 1.0, 0.10)
        alloc = {"T1": pct_t1, "T2": pct_t2, "T3": pct_t3, "T4": pct_t4}
    else:
        alloc = scenarios[selected_strat]
        
    total_alloc = sum(alloc.values())
    is_tier_valid = (total_alloc == 1.0)
    if not is_tier_valid:
        st.error(f"ECON-006: Tier percentages must sum to 1.0 (Currently {total_alloc:.2f})")
        
    tier_costs = {"T1": {"face": 5, "actual": 5}, "T2": {"face": 15, "actual": 15}, "T3": {"face": 35, "actual": 35}, "T4": {"face": 100, "actual": 100}}
    
    t1_b = approved_pool * alloc["T1"]
    t2_b = approved_pool * alloc["T2"]
    t3_b = approved_pool * alloc["T3"]
    t4_b = approved_pool * alloc["T4"]
    
    t1_count = int(t1_b / (tier_costs["T1"]["actual"] * redemption_rate)) if tier_costs["T1"]["actual"] > 0 else 0
    t2_count = int(t2_b / (tier_costs["T2"]["actual"] * redemption_rate)) if tier_costs["T2"]["actual"] > 0 else 0
    t3_count = int(t3_b / (tier_costs["T3"]["actual"] * redemption_rate)) if tier_costs["T3"]["actual"] > 0 else 0
    t4_count = int(t4_b / (tier_costs["T4"]["actual"] * redemption_rate)) if tier_costs["T4"]["actual"] > 0 else 0
    
    total_funded_winners = t1_count + t2_count + t3_count + t4_count
    
    sponsor_included = st.checkbox("Include Sponsor Inventory (FIN-015)", value=True)
    sponsor_qty = st.number_input("Sponsor Tier Qty (Face Value: 50, Actual Cost: 0)", value=5 if sponsor_included else 0)
    if sponsor_included:
        total_funded_winners += int(sponsor_qty)
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tier 1 - Recognition", f"{t1_count} users")
    c2.metric("Tier 2 - Standard", f"{t2_count} users")
    c3.metric("Tier 3 - High Perf.", f"{t3_count} users")
    c4.metric("Tier 4 - Monthly Star", f"{t4_count} users")
    c5.metric("Sponsor Tier", f"{int(sponsor_qty)} users")
    
    st.markdown("#### Coverage Metrics (12.2)")
    conn = sqlite3.connect(DB_FILE)
    registered_users = conn.execute("SELECT COUNT(*) FROM Global_Users").fetchone()[0]
    qualified_users = conn.execute("SELECT COUNT(*) FROM Monthly_Qualified_Users").fetchone()[0]
    conn.close()
    
    reg_cov = (total_funded_winners / registered_users * 100) if registered_users > 0 else 0
    qual_cov = (total_funded_winners / qualified_users * 100) if qualified_users > 0 else 0
    
    cov1, cov2 = st.columns(2)
    cov1.metric("Registered Coverage %", f"{reg_cov:.1f}%")
    cov2.metric("Qualified Coverage %", f"{qual_cov:.1f}%")
    
    st.markdown("---")
    st.subheader("Approval Workflow & Decision States (12.7, 12.8)")
    
    if 'cycle_maker' not in st.session_state: st.session_state.cycle_maker = "None"
    
    col_state1, col_state2 = st.columns([1,3])
    with col_state1: 
        st.info(f"**Current Status:** \n### {st.session_state.cycle_status}")
        
    with col_state2:
        valid = True
        errors = []
        
        if not is_tier_valid:
            valid = False
            errors.append("ECON-006: Tier percentages inconsistent.")
        if approved_pool > budget_ceil:
            valid = False
            errors.append("ECON-001: Approved pool exceeds budget ceiling.")
        if approved_pool > max_affordable:
            valid = False
            errors.append("ECON-002: Approved pool exceeds max affordable pool.")
        if req_profit < fixed_floor and profit_mode != "Fixed":
            errors.append("ECON-003: Projected profit < required floor (Warning).")
            
        if admin_role == "QA / Auditor":
            st.warning("QA / Auditor has read-only access. Cannot execute transitions.")
        else:
            for e in errors: st.error(e)
            
            if st.session_state.cycle_status == "DRAFT":
                if valid and st.button("Lock Snapshot & Move to SIMULATED"):
                    if admin_role == "Rewards Operations Maker":
                        st.session_state.cycle_status = "SIMULATED"
                        st.session_state.cycle_maker = "Rewards Operations Maker"
                        st.rerun()
                    else: st.error("Requires 'Rewards Operations Maker' role.")
            
            elif st.session_state.cycle_status == "SIMULATED":
                if valid and st.button("Submit to Finance (SUBMITTED)"):
                    if admin_role == "Rewards Operations Maker":
                        st.session_state.cycle_status = "SUBMITTED"
                        st.rerun()
                    else: st.error("Requires 'Rewards Operations Maker' role.")
                if st.button("RETURN TO DRAFT"): st.session_state.cycle_status = "DRAFT"; st.rerun()
            
            elif st.session_state.cycle_status == "SUBMITTED":
                if valid and st.button("Grant FINANCE_APPROVED"):
                    if admin_role == "Finance Approver":
                        st.session_state.cycle_status = "FINANCE_APPROVED"
                        st.rerun()
                    else: st.error("Requires 'Finance Approver' role.")
                if st.button("REJECT"): st.session_state.cycle_status = "REJECTED"; st.rerun()
            
            elif st.session_state.cycle_status == "FINANCE_APPROVED":
                if valid and st.button("Grant FINAL_APPROVED"):
                    if admin_role == "Final Authorised Admin":
                        if st.session_state.cycle_maker == admin_role: 
                            st.error("ECON-009: Maker and Approver cannot be the same user.")
                        else:
                            st.session_state.cycle_status = "FINAL_APPROVED"
                            st.rerun()
                    else: st.error("Requires 'Final Authorised Admin' role.")
                if st.button("EMERGENCY HOLD"): st.session_state.cycle_status = "EMERGENCY_HOLD"; st.rerun()
            
            elif st.session_state.cycle_status == "FINAL_APPROVED":
                if st.button("🚀 RELEASE REWARDS", type="primary"):
                    if admin_role in ["System Service Account", "Rewards Operations Maker", "Final Authorised Admin"]:
                        st.session_state.cycle_status = "RELEASED"
                        conn = sqlite3.connect(DB_FILE)
                        rule_ver = st.session_state.rule_version
                        conn.execute("INSERT INTO Event_Stream_Logs (Master_ID, Acting_Role, Action_ID, Event_Timestamp, Process_Status, Earned_Points, Reason_Code, Rule_Version) VALUES ('SYSTEM', 'Admin', 'REWARDS_RELEASED', ?, 'SETTLED', 0, 'CYCLE_CLOSED', ?)", (datetime.datetime.now(), rule_ver))
                        conn.commit()
                        conn.close()
                        st.balloons()
                        st.success("Rewards distributed and recorded in accounting as 'Reconciled'!")
                        st.rerun()
                    else: st.error("Requires executing authority.")
                if st.button("CANCEL CYCLE"): st.session_state.cycle_status = "CANCELLED"; st.rerun()
            
            elif st.session_state.cycle_status == "RELEASED":
                st.success("This month's budget successfully distributed.")
                if st.button("Mark PARTIALLY_RECONCILED"): st.session_state.cycle_status = "PARTIALLY_RECONCILED"; st.rerun()
            
            elif st.session_state.cycle_status == "PARTIALLY_RECONCILED":
                if st.button("Mark RECONCILED"): st.session_state.cycle_status = "RECONCILED"; st.rerun()
            
            elif st.session_state.cycle_status == "RECONCILED":
                if st.button("Mark CLOSED"): st.session_state.cycle_status = "CLOSED"; st.rerun()
            
            elif st.session_state.cycle_status in ["REJECTED", "CANCELLED", "CLOSED", "EMERGENCY_HOLD"]:
                if st.button("Reset Cycle (New Month) / Unlock"): 
                    st.session_state.cycle_status = "DRAFT"
                    st.session_state.cycle_maker = "None"
                    st.rerun()

with tab6:
    st.header("System Logs")
    log_type = st.radio("Select Log Type:", ["Reward Ledgers (Wallets)", "Event Stream", "Marketplace Attributions (Chains)", "Monthly Winners History"])
    
    conn = sqlite3.connect(DB_FILE)
    if log_type == "Event Stream":
        st.dataframe(pd.read_sql_query("SELECT * FROM Event_Stream_Logs ORDER BY Event_ID DESC LIMIT 50", conn), use_container_width=True)
    elif log_type == "Reward Ledgers (Wallets)":
        st.dataframe(pd.read_sql_query("SELECT * FROM Reward_Ledgers", conn), use_container_width=True)
    elif log_type == "Marketplace Attributions (Chains)":
        st.dataframe(pd.read_sql_query("SELECT * FROM Marketplace_Attributions", conn), use_container_width=True)
    else:
        st.dataframe(pd.read_sql_query("SELECT * FROM Past_Winners", conn), use_container_width=True)
    conn.close()

# --- BÖLÜM 14.2 & 14.3: YENİ RAPORLAMA SEKMESİ ---
with tab7:
    st.header("📊 Simulator Reports & Analytics")
    st.caption("Access all 19 missing operational and financial reports as specified in PDF Section 16 & 18.")
    
    report_cat = st.radio("Report Category:", ["Operational Reports (14.2)", "Financial Reports (14.3)"], horizontal=True)
    conn = sqlite3.connect(DB_FILE)
    df_report = pd.DataFrame()
    
    if report_cat == "Operational Reports (14.2)":
        op_rep = st.selectbox("Select Report:", [
            "1. Action Registry Validation", "2. User Monthly Ledger", "3. Actor KPI Report", 
            "4. Monthly Qualification", "5. Monthly Winner Selection", "6. Mega Eligibility", 
            "7. Integrity/Fraud", "8. Reversal/Clawback", "9. Audit Trail"
        ])
        
        if op_rep.startswith("1."):
            df_report = pd.read_sql_query("SELECT * FROM Action_Registry", conn)
        elif op_rep.startswith("2."):
            df_report = pd.read_sql_query("SELECT Master_ID, Role_Ledger, Pending_Points, Settled_Points, Reversed_Points, Rule_Version FROM Reward_Ledgers", conn)
        elif op_rep.startswith("3."):
            df_report = pd.read_sql_query("SELECT Acting_Role, COUNT(*) as Total_Actions, SUM(Earned_Points) as Total_Points_Earned FROM Event_Stream_Logs GROUP BY Acting_Role", conn)
        elif op_rep.startswith("4."):
            df_report = pd.read_sql_query("SELECT Master_ID, Total_Score, Rollover_Bonus FROM Monthly_Qualified_Users", conn)
        elif op_rep.startswith("5."):
            df_report = pd.read_sql_query("SELECT * FROM Past_Winners", conn)
        elif op_rep.startswith("6."):
            df_report = pd.read_sql_query("SELECT Master_ID, EID_Verified, Has_Certification, Continuous_Paid_Months FROM Global_Users", conn)
        elif op_rep.startswith("7."):
            df_report = pd.read_sql_query("SELECT Master_ID, Integrity_Score, Action_Status, Critical_Flag FROM Integrity_Profiles WHERE Integrity_Score < 100 OR Action_Status != 'Normal' OR Critical_Flag = 1", conn)
        elif op_rep.startswith("8."):
            df_report = pd.read_sql_query("SELECT * FROM Event_Stream_Logs WHERE Process_Status = 'REVERSED'", conn)
        elif op_rep.startswith("9."):
            df_report = pd.read_sql_query("SELECT * FROM Audit_Trail", conn)

    else:
        fin_rep = st.selectbox("Select Report:", [
            "1. Reward Economics Summary", "2. Population Coverage", "3. Funding Source Report", 
            "4. Tier Allocation Report", "5. Scenario Comparison", "6. Budget & Profit Breach Report", 
            "7. Redemption & Expiry Report", "8. Mega Provision Report", "9. Cycle Audit Report"
        ])
        
        if fin_rep.startswith("1."):
            df_report = pd.read_sql_query("SELECT Cycle_ID, Month_ID, Status, Sub_Revenue, Market_Revenue, Ops_Costs, Budget_Ceiling, Profit_Margin_Pct, Fixed_Profit_Floor, Max_Affordable_Pool, Approved_Reward_Pool FROM reward_cycle_financial_config", conn)
        elif fin_rep.startswith("2."):
            df_report = pd.read_sql_query("SELECT * FROM Qualified_User_Funding", conn)
        elif fin_rep.startswith("3."):
            df_report = pd.read_sql_query("SELECT * FROM Reward_Inventory", conn)
        elif fin_rep.startswith("4."):
            df_report = pd.read_sql_query("SELECT * FROM Reward_Tier_Allocations", conn)
        elif fin_rep.startswith("5."):
            df_report = pd.read_sql_query("SELECT * FROM Reward_Scenarios", conn)
        elif fin_rep.startswith("6."):
            st.info("No breaches logged in current session.")
        elif fin_rep.startswith("7."):
            df_report = pd.read_sql_query("SELECT * FROM Reward_Financial_Outcomes", conn)
        elif fin_rep.startswith("8."):
            st.info("Mega Provision opening reserve and usage will appear here during cycle close.")
        elif fin_rep.startswith("9."):
            df_report = pd.read_sql_query("SELECT * FROM Reward_Cycle_Approvals", conn)
            
    if not df_report.empty:
        st.dataframe(df_report, use_container_width=True)
        # P3 EXPORT (XLSX/PDF/CSV) - Eklenen Kod
        st.download_button(label="📥 Export to CSV", data=convert_df_to_csv(df_report), file_name="report.csv", mime='text/csv')
            
    conn.close()
