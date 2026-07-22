"""
Diverse Dataset Audit Script

Analyzes the generated test_data/v2_diverse dataset to verify:
1. User distribution by type
2. Shared device/IP relationships
3. Rule trigger conditions
4. ML behavioral patterns
5. Expected detection attribution
"""
import pandas as pd
import sys
from pathlib import Path

# Add backend to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

# Load data
users_df = pd.read_csv("test_data/v2_diverse/users.csv")
devices_df = pd.read_csv("test_data/v2_diverse/devices.csv")
trades_df = pd.read_csv("test_data/v2_diverse/trades.csv")
withdrawals_df = pd.read_csv("test_data/v2_diverse/withdrawals.csv")

print("="*60)
print("DIVERSE DATASET AUDIT REPORT")
print("="*60)

# Parse timestamps
users_df['account_created_time'] = pd.to_datetime(users_df['account_created_time'])
users_df['account_age_days'] = (pd.Timestamp('2026-07-19') - users_df['account_created_time']).dt.days
devices_df['first_seen'] = pd.to_datetime(devices_df['first_seen'])
devices_df['last_seen'] = pd.to_datetime(devices_df['last_seen'])
trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
withdrawals_df['timestamp'] = pd.to_datetime(withdrawals_df['timestamp'])

# Calculate per-user statistics
print("\n1. DATASET OVERVIEW")
print("-"*60)
print(f"Total users: {len(users_df)}")
print(f"Total devices: {len(devices_df)}")
print(f"Total trades: {len(trades_df)}")
print(f"Total withdrawals: {len(withdrawals_df)}")

# Check for shared devices
print("\n2. SHARED DEVICE ANALYSIS")
print("-"*60)
device_counts = devices_df['device_id'].value_counts()
shared_devices = device_counts[device_counts > 1]
print(f"Unique devices: {len(device_counts)}")
print(f"Shared devices: {len(shared_devices)}")
print(f"Users with shared devices: {shared_devices.sum()}")
print(f"\nShared device distribution:")
for device_id, count in shared_devices.head(10).items():
    users = devices_df[devices_df['device_id'] == device_id]['user_id'].tolist()
    print(f"  {device_id}: {count} users - {users[:3]}...")

# Check for shared IPs
print("\n3. SHARED IP ANALYSIS")
print("-"*60)
ip_counts = devices_df['ip_address'].value_counts()
shared_ips = ip_counts[ip_counts > 1]
print(f"Unique IPs: {len(ip_counts)}")
print(f"Shared IPs: {len(shared_ips)}")
print(f"Users with shared IPs: {shared_ips.sum()}")

# Calculate per-user statistics
print("\n4. PER-USER STATISTICS")
print("-"*60)

# Trade statistics
user_trade_stats = trades_df.groupby('user_id').agg({
    'trade_id': 'count',
    'timestamp': ['min', 'max']
}).reset_index()
user_trade_stats.columns = ['user_id', 'trade_count', 'first_trade', 'last_trade']

# Withdrawal statistics
user_withdraw_stats = withdrawals_df.groupby('user_id').agg({
    'withdraw_id': 'count',
    'amount': 'sum',
    'is_new_address': 'sum'
}).reset_index()
user_withdraw_stats.columns = ['user_id', 'withdraw_count', 'withdraw_amount', 'new_address_count']

# Device information
user_device_info = devices_df[['user_id', 'device_id', 'ip_address']]

# Merge all stats
user_stats = users_df[['user_id', 'account_age_days']].merge(
    user_trade_stats, on='user_id', how='left'
).merge(
    user_withdraw_stats, on='user_id', how='left'
).merge(
    user_device_info, on='user_id', how='left'
)

# Fill NaN with 0
user_stats['trade_count'] = user_stats['trade_count'].fillna(0).astype(int)
user_stats['withdraw_count'] = user_stats['withdraw_count'].fillna(0).astype(int)
user_stats['withdraw_amount'] = user_stats['withdraw_amount'].fillna(0)
user_stats['new_address_count'] = user_stats['new_address_count'].fillna(0).astype(int)

# Check if user has shared device
device_user_counts = devices_df['device_id'].value_counts().to_dict()
user_stats['has_shared_device'] = user_stats['device_id'].map(
    lambda x: device_user_counts.get(x, 0) > 1
)

print(f"\nTrade count distribution:")
print(f"  Min: {user_stats['trade_count'].min()}")
print(f"  Max: {user_stats['trade_count'].max()}")
print(f"  Mean: {user_stats['trade_count'].mean():.1f}")
print(f"  Median: {user_stats['trade_count'].median():.1f}")

print(f"\nWithdrawal count distribution:")
print(f"  Min: {user_stats['withdraw_count'].min()}")
print(f"  Max: {user_stats['withdraw_count'].max()}")
print(f"  Mean: {user_stats['withdraw_count'].mean():.1f}")
print(f"  Median: {user_stats['withdraw_count'].median():.1f}")

print(f"\nAccount age distribution:")
print(f"  Min: {user_stats['account_age_days'].min()}")
print(f"  Max: {user_stats['account_age_days'].max()}")
print(f"  Mean: {user_stats['account_age_days'].mean():.1f}")

print(f"\nShared device users: {user_stats['has_shared_device'].sum()}")

# Categorize users based on characteristics
print("\n5. USER CATEGORIZATION (INFERRRED FROM DATA)")
print("-"*60)

# ML-only indicators: high trade count, no shared device, low withdraw count
ml_only_candidates = user_stats[
    (user_stats['trade_count'] >= 40) &
    (~user_stats['has_shared_device']) &
    (user_stats['withdraw_count'] <= 3)
]

# Rule-only indicators: high withdraw count, moderate trade count, no shared device, new account
rule_only_candidates = user_stats[
    (user_stats['withdraw_count'] >= 6) &
    (user_stats['trade_count'] <= 25) &
    (~user_stats['has_shared_device']) &
    (user_stats['account_age_days'] <= 10)
]

# Graph-only indicators: shared device, low trade count, low withdraw count
graph_only_candidates = user_stats[
    (user_stats['has_shared_device']) &
    (user_stats['trade_count'] <= 20) &
    (user_stats['withdraw_count'] <= 5)
]

# Multi-signal indicators: high trade count AND high withdraw count (and possibly shared device)
multi_signal_candidates = user_stats[
    (user_stats['trade_count'] >= 30) &
    (user_stats['withdraw_count'] >= 5)
]

# Normal users: low trade count, low withdraw count, no shared device
normal_candidates = user_stats[
    (user_stats['trade_count'] <= 15) &
    (user_stats['withdraw_count'] <= 4) &
    (~user_stats['has_shared_device'])
]

print(f"ML-only candidates (high trade, no shared, low withdraw): {len(ml_only_candidates)}")
print(f"Rule-only candidates (high withdraw, new account, no shared): {len(rule_only_candidates)}")
print(f"Graph-only candidates (shared device, low trade/withdraw): {len(graph_only_candidates)}")
print(f"Multi-signal candidates (high trade AND high withdraw): {len(multi_signal_candidates)}")
print(f"Normal candidates (low activity, no shared): {len(normal_candidates)}")

# Account for overlaps (users in multiple categories)
print(f"\nOverlap check:")
print(f"  Users in multiple categories: {len(ml_only_candidates) + len(rule_only_candidates) + len(graph_only_candidates) + len(multi_signal_candidates) + len(normal_candidates) - len(user_stats)}")

# Detailed analysis of each category
print("\n6. DETAILED CATEGORY ANALYSIS")
print("-"*60)

if len(ml_only_candidates) > 0:
    print(f"\nML-only Candidates (sample):")
    sample = ml_only_candidates.head(3)
    for _, row in sample.iterrows():
        print(f"  {row['user_id']}: trades={row['trade_count']}, withdraws={row['withdraw_count']}, shared_device={row['has_shared_device']}, account_age={row['account_age_days']}")

if len(rule_only_candidates) > 0:
    print(f"\nRule-only Candidates (sample):")
    sample = rule_only_candidates.head(3)
    for _, row in sample.iterrows():
        print(f"  {row['user_id']}: trades={row['trade_count']}, withdraws={row['withdraw_count']}, shared_device={row['has_shared_device']}, account_age={row['account_age_days']}")

if len(graph_only_candidates) > 0:
    print(f"\nGraph-only Candidates (sample):")
    sample = graph_only_candidates.head(3)
    for _, row in sample.iterrows():
        print(f"  {row['user_id']}: trades={row['trade_count']}, withdraws={row['withdraw_count']}, shared_device={row['has_shared_device']}, account_age={row['account_age_days']}")

if len(multi_signal_candidates) > 0:
    print(f"\nMulti-signal Candidates (sample):")
    sample = multi_signal_candidates.head(3)
    for _, row in sample.iterrows():
        print(f"  {row['user_id']}: trades={row['trade_count']}, withdraws={row['withdraw_count']}, shared_device={row['has_shared_device']}, account_age={row['account_age_days']}")

# Expected detection attribution
print("\n7. EXPECTED DETECTION ATTRIBUTION")
print("-"*60)
print("Based on detection thresholds (ML>=10, Rule>=15, Graph>=10):")
print()

# Calculate expected detections
expected_ml_only = len(ml_only_candidates)
expected_rule_only = len(rule_only_candidates)
expected_graph_only = len(graph_only_candidates)
expected_multi_signal = len(multi_signal_candidates)

high_risk_users = expected_ml_only + expected_rule_only + expected_graph_only + expected_multi_signal

print(f"Expected ML-only (ml>=10, rule<15, graph<10): ~{expected_ml_only} users")
print(f"Expected Rule-only (ml<10, rule>=15, graph<10): ~{expected_rule_only} users")
print(f"Expected Graph-only (ml<10, rule<15, graph>=10): ~{expected_graph_only} users")
print(f"Expected Multi-signal (ml>=10, rule>=15, graph>=10): ~{expected_multi_signal} users")
print()
print("Expected Detection Coverage (assuming all become HIGH/CRITICAL):")
total_risk = expected_ml_only + expected_rule_only + expected_graph_only + expected_multi_signal

ml_coverage = (expected_ml_only + expected_multi_signal) / total_risk * 100 if total_risk > 0 else 0
rule_coverage = (expected_rule_only + expected_multi_signal) / total_risk * 100 if total_risk > 0 else 0
graph_coverage = (expected_graph_only + expected_multi_signal) / total_risk * 100 if total_risk > 0 else 0

print(f"  LightGBM: {ml_coverage:.1f}%")
print(f"  Rule Engine: {rule_coverage:.1f}%")
print(f"  Graph Network: {graph_coverage:.1f}%")

# Risk assessment
print("\n8. RISK ASSESSMENT")
print("-"*60)

risks = []

# Check 1: Are there enough shared devices for graph detection?
if len(shared_devices) == 0:
    risks.append("❌ CRITICAL: No shared devices found - graph detection will not work")
elif len(shared_devices) < 5:
    risks.append(f"⚠️  WARNING: Only {len(shared_devices)} shared devices - may produce limited graph detection")
else:
    risks.append(f"✅ {len(shared_devices)} shared devices available for graph detection")

# Check 2: Do rule-only users have sufficient withdrawal frequency?
if len(rule_only_candidates) < 50:
    risks.append(f"⚠️  WARNING: Only {len(rule_only_candidates)} rule-only candidates - may not show clear rule attribution")
else:
    risks.append(f"✅ {len(rule_only_candidates)} rule-only candidates available")

# Check 3: Do ML-only users have high trade frequency?
if len(ml_only_candidates) < 50:
    risks.append(f"⚠️  WARNING: Only {len(ml_only_candidates)} ML-only candidates - may not show clear ML attribution")
else:
    risks.append(f"✅ {len(ml_only_candidates)} ML-only candidates available")

# Check 4: Is there diversity in detection attribution?
unique_combinations = len(set([
    (expected_ml_only > 0),
    (expected_rule_only > 0),
    (expected_graph_only > 0),
    (expected_multi_signal > 0)
]))
if unique_combinations < 3:
    risks.append("⚠️  WARNING: Limited detection diversity expected")
else:
    risks.append("✅ Multiple detection patterns expected")

# Check 5: Are CSV files valid for upload?
required_files = ['users.csv', 'devices.csv', 'trades.csv', 'withdrawals.csv']
missing = [f for f in required_files if not Path(f"test_data/v2_diverse/{f}").exists()]
if missing:
    risks.append(f"❌ CRITICAL: Missing required files: {missing}")
else:
    risks.append("✅ All required CSV files present")

for risk in risks:
    print(risk)

# Sample rows from each file
print("\n9. DATA SAMPLES")
print("-"*60)
print(f"\nusers.csv (first 3 rows):")
print(users_df.head(3).to_string(index=False))

print(f"\ndevices.csv (first 3 rows):")
print(devices_df.head(3).to_string(index=False))

print(f"\ntrades.csv (first 3 rows):")
print(trades_df.head(3).to_string(index=False))

print(f"\nwithdrawals.csv (first 3 rows):")
print(withdrawals_df.head(3).to_string(index=False))

print("\n" + "="*60)
print("AUDIT COMPLETE")
print("="*60)
