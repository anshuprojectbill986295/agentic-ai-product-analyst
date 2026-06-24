import sqlite3
import random
import numpy as np

conn = sqlite3.connect("fintech_product.db")
cursor = conn.cursor()

# ==========================================
# SCHEMA DEFINITION
# ==========================================
cursor.execute(""" 
CREATE TABLE IF NOT EXISTS users(
               user_id INTEGER PRIMARY KEY,
               kyc_status TEXT,
               kyc_processing_age_days REAL,
               margin_balance REAL,
               total_ledger_balance REAL,
               auth_bottleneck TEXT -- Upgraded to TEXT to hold specific failure reasons
               )""")

cursor.execute(""" 
CREATE TABLE IF NOT EXISTS app_performance(
               session_id INTEGER PRIMARY KEY,
               user_id INTEGER,
               device_os TEXT,
               session_start_ts INTEGER,
               chart_render_latency_ms REAL,
               websocket_drop_rate_pct REAL,
               indicator_sync_status_flag INTEGER,
               api_5xx_error_rate_pct REAL,
               crash_loop_count_per_session INTEGER,
               FOREIGN KEY(user_id) REFERENCES users(user_id))
               """)

cursor.execute("""
CREATE TABLE IF NOT EXISTS trades(
               order_id INTEGER PRIMARY KEY,
               user_id INTEGER,
               order_type TEXT, 
               requested_price REAL,
               executed_price REAL,
               price_slippage_bps REAL, 
               order_routing_latency_ms REAL,
               exchange_rejection_code TEXT,
               FOREIGN KEY(user_id) REFERENCES users(user_id)
               )
               """)

cursor.execute("""
CREATE TABLE IF NOT EXISTS financial_ledger(
               txn_id INTEGER PRIMARY KEY,
               user_id INTEGER,
               txn_type TEXT,
               amount REAL,
               balance_after_txn REAL,
               peak_margin_utilization_pct REAL,
               withdrawal_processing_latency_hours REAL,
               eod_ledger_sync_status_flag INTEGER,
               FOREIGN KEY(user_id) REFERENCES users(user_id)
               )
               """)

cursor.execute("""
               CREATE TABLE IF NOT EXISTS customer_support(
               ticket_id INTEGER PRIMARY KEY,
               user_id INTEGER,
               complaint_theme TEXT,
               ticket_resolution_time_hours REAL,
               support_interaction_count INTEGER,
               FOREIGN KEY(user_id) REFERENCES users(user_id)
               )
               """)

# ==========================================
# 0. CENTRALIZED PERSONA MAP (The Stitcher)
# ==========================================
all_users = list(range(1, 5001))
random.shuffle(all_users)

# 1. STRICT FUNNEL ISOLATION: 
# 650 users are strictly unapproved and stuck in top-of-funnel KYC
kyc_defective_users = all_users[:650]

# 4350 users are approved active traders
approved_users = all_users[650:]

# 2. REALISTIC OVERLAPPING COHORTS:
# By sampling independently from the entire approved pool, 
# a single power user can organically experience multiple different issues over time.
auth_defect_users = random.sample(approved_users, 250)
chart_glitch_users = random.sample(approved_users, 821)
stability_users = random.sample(approved_users, 517)
trade_slippage_users = random.sample(approved_users, 1135)
ledger_defect_users = random.sample(approved_users, 703)
general_inquiry_users = random.sample(approved_users, 924)

# ==========================================
# 1. STATEFUL MEMORY INITIALIZATION
# ==========================================
user_states = {}

# Your exact requested realistic KYC failure distribution
kyc_reasons = [
    "DOCUMENT_MISMATCH",         # 40% 
    "RE_KYC_REQUIRED",           # 20% 
    "SELFIE_VERIFICATION_FAILED",# 15% 
    "BANK_VERIFICATION_ISSUE",   # 10% 
    "TECHNICAL_API_DELAY",       # 10% 
    "COMPLIANCE_REVIEW"          # 5%  
]
kyc_weights = [0.40, 0.20, 0.15, 0.10, 0.10, 0.05]

for uid in all_users:
    if uid in kyc_defective_users:
        # KYC Users: Status is PENDING/REJECTED, bottleneck holds the exact reason
        kyc_status = random.choices(["PENDING", "REJECTED"], weights=[0.8, 0.2])[0]
        kyc_age = round(random.uniform(14.0, 45.0), 1)
        auth_bottleneck = random.choices(kyc_reasons, weights=kyc_weights, k=1)[0]
        
        user_states[uid] = {
            "kyc_status": kyc_status, "kyc_age": kyc_age, "auth_bottleneck": auth_bottleneck,
            "leverage_multiplier": 1.0, "ledger_balance": 0.0, "margin_balance": 0.0
        }
    else:
        # Approved Users: Cleared, except for the 250 users facing OTP/2FA bugs
        kyc_age = round(random.uniform(0.5, 3.0), 1)
        starting_balance = random.uniform(5000.0, 500000.0)
        leverage = random.choice([1.0, 2.0, 4.0, 5.0])
        
        # If they are in the auth defect cohort, they face OTP/Login issues
        auth_bottleneck = "2FA/OTP_NOT_RECEIVED" if uid in auth_defect_users else "CLEARED"
        
        user_states[uid] = {
            "kyc_status": "APPROVED", "kyc_age": kyc_age, "auth_bottleneck": auth_bottleneck,
            "leverage_multiplier": leverage, "ledger_balance": starting_balance,
            "margin_balance": starting_balance * leverage 
        }

# ==========================================
# 2. FINANCIAL LEDGER 
# ==========================================
ledger_rows = []

# Defective Ledger Rows routed ONLY to `ledger_defect_users`
for uid in ledger_defect_users:
    txn_type = random.choices(["MARGIN_PENALTY", "DELAYED_PAYMENT", "AUTO_SQUARE_OFF", "WITHDRAWAL"], weights=[0.4, 0.2, 0.2, 0.2], k=1)[0]
    current_balance = user_states[uid]["ledger_balance"]
    
    if txn_type != "WITHDRAWAL":
        withdrawal_processing_latency_hours = 0.0
        if random.choices([True, False], weights=[0.45, 0.55], k=1)[0]: #if negative balance
            target_balance = random.uniform(-25000.0, -500.0)
            amount = current_balance - target_balance
        else:
            amount = (np.random.pareto(a=1.16) * 5000) + 1500
            target_balance = current_balance - amount
    else: 
        if current_balance <= 0:
             amount = 0.0; target_balance = current_balance; withdrawal_processing_latency_hours = 0.0
        else:
             amount = min(current_balance, random.uniform(5000.0, 50000.0))
             target_balance = current_balance - amount
             withdrawal_processing_latency_hours = max(2, np.random.normal(loc=96, scale=24))

    ledger_rows.append((uid, txn_type, round(amount, 2), round(target_balance, 2), round(random.uniform(95.0, 180.0), 2), round(withdrawal_processing_latency_hours, 2), random.choices([1, 0], weights=[0.8, 0.2], k=1)[0]))
    
    user_states[uid]["ledger_balance"] = target_balance
    user_states[uid]["margin_balance"] = target_balance * user_states[uid]["leverage_multiplier"] if target_balance > 0 else target_balance

# Healthy Ledger Rows
healthy_ledger_users = random.choices(approved_users, k=4297)
for uid in healthy_ledger_users:
    txn_type = random.choices(["DEPOSIT", "WITHDRAWAL", "AMC_FEE"], weights=[0.5, 0.4, 0.1], k=1)[0]
    current_balance = user_states[uid]["ledger_balance"]
    
    if txn_type == "DEPOSIT":
        amount = random.uniform(1000.0, 150000.0); target_balance = current_balance + amount; latency = 0.0
    elif txn_type == "WITHDRAWAL":
        if current_balance > 0:
            amount = min(current_balance * random.uniform(0.1, 0.5), random.uniform(1000.0, 50000.0))
            target_balance = current_balance - amount
            latency = max(0.5, np.random.normal(loc=2.5, scale=1.0))
        else: 
            amount = 0.0; target_balance = current_balance; latency = 0.0
    else:
        amount = random.uniform(100.0, 450.0); target_balance = current_balance - amount; latency = 0.0

    ledger_rows.append((uid, txn_type, round(amount, 2), round(target_balance, 2), round(random.uniform(10.0, 75.0), 2), round(latency, 2), 1))
    
    user_states[uid]["ledger_balance"] = target_balance
    user_states[uid]["margin_balance"] = target_balance * user_states[uid]["leverage_multiplier"] if target_balance > 0 else target_balance

random.shuffle(ledger_rows)
cursor.executemany("INSERT INTO financial_ledger (user_id,txn_type,amount,balance_after_txn,peak_margin_utilization_pct,withdrawal_processing_latency_hours,eod_ledger_sync_status_flag) VALUES(?,?,?,?,?,?,?)", ledger_rows)

# ==========================================
# 3. FINALIZE USERS TABLE
# ==========================================
user_rows = [(uid, state["kyc_status"], round(state["kyc_age"], 2), round(state["margin_balance"], 2), round(state["ledger_balance"], 2), state["auth_bottleneck"]) for uid, state in user_states.items()]
cursor.executemany("INSERT INTO users VALUES(?,?,?,?,?,?)", user_rows)

# ==========================================
# 4. APP PERFORMANCE
# ==========================================
perf_temp = []
START_TS, END_TS = 1770595200, 1781654399   

for uid in chart_glitch_users:
    perf_temp.append((uid, random.choice(["Android", "iOS"]), random.randint(START_TS, END_TS), round(abs(np.random.normal(loc=4500, scale=500)), 2), float(np.random.poisson(lam=12.5)), 0, round(random.uniform(0.0, 2.0), 2), random.randint(0, 1)))

for uid in stability_users:
    perf_temp.append((uid, random.choice(["Android", "iOS"]), random.randint(START_TS, END_TS), round(abs(np.random.normal(loc=1500, scale=300)), 2), float(np.random.poisson(lam=35.0)), 1, round(random.uniform(15.0, 45.0), 2), random.randint(2, 5)))

for _ in range(3662):
    perf_temp.append((random.choice(approved_users), random.choice(["Android", "iOS"]), random.randint(START_TS, END_TS), round(np.random.lognormal(mean=6.5, sigma=0.5), 2), float(np.random.poisson(lam=2.0)), 1, 0.0, 0))

random.shuffle(perf_temp)
perf_rows = [(i+1,) + row for i, row in enumerate(perf_temp)]
cursor.executemany("INSERT INTO app_performance VALUES(?,?,?,?,?,?,?,?,?)", perf_rows)

# ==========================================
# 5. TRADES
# =========================================
trades_rows = []

for uid in trade_slippage_users:
    order_type = random.choice(["BUY_MARKET", "SELL_MARKET", "STOP_LOSS_MARKET"])
    req_price = random.uniform(50,3500)
    abs_slip = np.random.lognormal(mean=3.0, sigma=0.8)
    exec_price = req_price * (1 + abs_slip/10000) if "BUY" in order_type else req_price * (1 - abs_slip/10000)
    latency = np.random.exponential(scale=2500)
    rej_code = "FAILED TIMEOUT" if latency > 5000 else random.choices(["NONE","INSUFFICIENT_DEPTH","INVALID_TICK_SIZE"],weights=[0.8,0.1,0.1],k=1)[0]
    trades_rows.append((uid, order_type, round(req_price,2), round(exec_price,2), round(-1*abs_slip,2), round(latency,2), rej_code))    

for _ in range(3865):
    order_type = random.choice(["BUY_LIMIT", "SELL_LIMIT", "STOP_LOSS_LIMIT"])
    req_price = random.uniform(50,3500)
    #positive or 0 slippage can happen in LIMIT ORDER
    slippage = random.uniform(0.1,10) if random.choices(["TRUE","FALSE"],weights=[0.1,0.9],k=1)[0] == "TRUE" else 0.0    
    exec_price = req_price * (1 - slippage/10000) if "BUY" in order_type else req_price * (1 + slippage/10000)
    trades_rows.append((random.choice(approved_users), order_type, round(req_price,2), round(exec_price,2), round(slippage,2), round(max(20, np.random.normal(loc=150, scale=40)),2), "NONE"))

random.shuffle(trades_rows)
cursor.executemany("INSERT INTO trades (user_id,order_type,requested_price,executed_price,price_slippage_bps,order_routing_latency_ms,exchange_rejection_code) VALUES(?,?,?,?,?,?,?)", trades_rows)

# ==========================================
# 6. CUSTOMER SUPPORT (The RCA Stitcher)
# ==========================================
cs_rows=[]

# 1. KYC Defect Cohort (Top of Funnel - No overlap with trading bugs)
for uid in kyc_defective_users:
    cs_rows.append((uid, "KYC_ONBOARDING_EFFICIENCY", round(random.uniform(170.0,450.0),2), random.randint(4,9)))

# 2. Authentication Defect Cohort 
for uid in auth_defect_users:
    cs_rows.append((uid, "LOGIN_AND_2FA_ISSUE", round(np.random.exponential(scale=24.0)+0.5,2), random.choices([2,3,4], weights=[0.5,0.3,0.2], k=1)[0]))

# 3. Chart Defect Cohort 
for uid in chart_glitch_users:
    cs_rows.append((uid, "CHARTING_UI_GLITCH", round(np.random.exponential(scale=14.0)+0.5,2), random.choices([1,2,3], weights=[0.8,0.18,0.02], k=1)[0]))

# 4. Trade Slippage Cohort
for uid in trade_slippage_users:
    cs_rows.append((uid, "EXECUTION_SLIPPAGE", round(np.random.exponential(scale=14.0)+0.5,2), random.choices([1,2,3], weights=[0.8,0.18,0.02], k=1)[0]))

# 5. Stability Cohort
for uid in stability_users:
    cs_rows.append((uid, "SYSTEM_STABILITY", round(np.random.exponential(scale=14.0)+0.5,2), random.choices([1,2,3], weights=[0.8,0.18,0.02], k=1)[0]))

# 6. Ledger Defect Cohort
for uid in ledger_defect_users:
    cs_rows.append((uid, "LEDGER_DISPUTE", round(np.random.exponential(scale=14.0)+0.5,2), random.choices([1,2,3], weights=[0.8,0.18,0.02], k=1)[0]))

# 7. General Inquiry 
for uid in general_inquiry_users:
    cs_rows.append((uid, "GENERAL_INQUIRY", round(np.random.exponential(scale=8.0)+0.5,2), random.choices([1,2], weights=[0.9,0.1], k=1)[0]))

random.shuffle(cs_rows)

# Because users can now exist in multiple lists, the customer_support table will organically 
# have >5000 rows. A user who suffered slippage AND a crash will have two separate tickets. 
cursor.executemany("INSERT INTO customer_support (user_id,complaint_theme,ticket_resolution_time_hours,support_interaction_count) VALUES(?,?,?,?)", cs_rows)
print("🎯 SUCCESS! Database logically simplified with 'auth_bottleneck' TEXT column.")

conn.commit()
conn.close()