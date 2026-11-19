import random
import os

random.seed(42)

# 1. Five Standard Sectors (Bảng 37 Báo cáo)
sectors = [
    ('REAL_ESTATE_CONSTRUCTION', 'BĐS và Xây dựng', 1.8000, 2.0000, -2.2000, 3.500),
    ('MANUFACTURING', 'Sản xuất và Chế biến', 1.3000, 1.4000, -0.4000, 2.200),
    ('AGRICULTURE', 'Nông - Lâm - Thủy sản', 0.8000, 0.9000, -0.2000, 1.800),
    ('COMMERCE', 'Thương mại', 1.2000, 1.3000, -0.5000, 2.500),
    ('RETAIL', 'Bán lẻ', 1.1000, 1.6000, -0.7000, 2.800)
]

ratings_map = [
    ('AAA', 0.0035, 1),
    ('AA', 0.0070, 1),
    ('A', 0.0120, 1),
    ('BBB', 0.0250, 1),
    ('BB', 0.0550, 2),
    ('B', 0.0950, 2),
    ('CCC', 0.1800, 3)
]

corp_names = [
    'Tập đoàn Phát triển Đô thị Horizon', 'Công ty CP Đầu tư Địa ốc Nam Việt', 'Tổng Công ty Xây dựng Thăng Long',
    'Công ty Dệt may Phong Phú', 'Tập đoàn Thép Đại Nam', 'Công ty Chế biến Thủy hải sản Biển Đông',
    'Chuỗi Siêu thị Bách Hóa Xanh Plaza', 'Công ty Nông nghiệp Hitech Vinaseed', 'Công ty CP Xây lắp Dầu khí',
    'Tập đoàn Bất động sản Hoàng Gia', 'Công ty Nhựa & Bao bì Tân Tiến', 'Công ty Dược phẩm Trung ương Hà Nội'
]

output_path = os.path.join(os.path.dirname(__file__), 'seed_data_postgresql.sql')
print(f"Generating SQL seed data into {output_path}...")

with open(output_path, 'w', encoding='utf-8') as f:
    f.write('-- ==============================================================================\n')
    f.write('-- SEED DATA FOR CREDIT STRESS TESTING & IFRS 9 (POSTGRESQL)\n')
    f.write('-- Model: 11 Standardized Entities & 5 Business Sectors\n')
    f.write('-- ==============================================================================\n\n')

    # 1. Users
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('-- 1. SEED SYSTEM USERS (5 vai trò chuẩn RBAC)\n')
    f.write('-- ------------------------------------------------------------------------------\n')
    # PBKDF2 hash for password '123456'
    pwd_hash = 'pbkdf2_sha256$720000$defaultSalt2026$5Uo7tVp0JkLmn8v9wXyZ1234567890abcdefghijklm='
    f.write(f"""INSERT INTO system_users (user_id, username, full_name, email, role, department, password_hash) VALUES
(1, 'maker_an', 'Nguyễn Văn An', 'an.nguyen@bank.vn', 'MAKER', 'Phòng Đo lường Rủi ro', '{pwd_hash}'),
(2, 'checker_binh', 'Trần Thị Bình', 'binh.tran@bank.vn', 'CHECKER', 'Phòng Quản lý rủi ro', '{pwd_hash}'),
(3, 'approver_cuong', 'Lê Hoàng Cường', 'cuong.le@bank.vn', 'APPROVER', 'Ban Điều hành / Khối Quản lý rủi ro', '{pwd_hash}'),
(4, 'auditor_dung', 'Phạm Minh Dũng', 'dung.pham@bank.vn', 'AUDITOR', 'Khối Kiểm toán Nội bộ', '{pwd_hash}'),
(5, 'admin_system', 'Quản trị viên Hệ thống (IT Admin)', 'admin@bank.vn', 'ADMIN', 'Khối CNTT & Quản trị Hệ thống', '{pwd_hash}')
ON CONFLICT (user_id) DO NOTHING;\n\n""")

    # 2. Sector Sensitivities
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('-- 2. SEED SECTOR SENSITIVITY (5 Nhóm ngành chuẩn hóa theo Báo cáo)\n')
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('INSERT INTO sector_sensitivity (sector_code, sector_name_vn, beta_gdp, beta_interest, beta_real_estate, pd_multiplier) VALUES\n')
    sec_rows = [
        f"('{code}', '{name_vn}', {bg:.4f}, {bi:.4f}, {br:.4f}, {mult:.3f})"
        for code, name_vn, bg, bi, br, mult in sectors
    ]
    f.write(',\n'.join(sec_rows))
    f.write('\nON CONFLICT (sector_code) DO NOTHING;\n\n')

    # 3. Macro Scenarios
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('-- 3. SEED MACRO SCENARIOS (3 Kịch bản vĩ mô)\n')
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write("""INSERT INTO macro_scenarios (scenario_id, scenario_code, scenario_name, scenario_type, description, gdp_growth_shock, interest_rate_shock, real_estate_price_shock, fx_rate_shock, recovery_time_years, scenario_weight) VALUES
(1, 'BASELINE', 'Kịch bản Cơ sở 2026', 'Baseline', 'Tăng trưởng kinh tế ổn định theo mục tiêu Quốc hội (6.5%), lãi suất đi ngang, thị trường BĐS ổn định.', 0.0000, 0.0000, 0.0000, 0.0000, 1.5, 0.500),
(2, 'ADVERSE', 'Kịch bản Căng thẳng Vừa', 'Adverse', 'Kinh tế toàn cầu suy giảm, GDP giảm 1.5%, lãi suất tăng +200 bps, giá BĐS giảm 15%.', -0.0150, 0.0200, -0.1500, 0.0300, 2.0, 0.300),
(3, 'SEVERE', 'Kịch bản Khủng hoảng Nghiêm trọng', 'Severe', 'Lạm phát toàn cầu bùng phát, GDP sụt giảm 3.0%, lãi suất tăng sốc +400 bps, thị trường BĐS đóng băng giảm 35%.', -0.0300, 0.0400, -0.3500, 0.0600, 3.0, 0.200)
ON CONFLICT (scenario_id) DO NOTHING;\n\n""")

    # 4. Generate 100 Customers, Loan Accounts, Collaterals, Loan Collateral
    customer_rows = []
    loan_rows = []
    col_rows = []
    loan_col_rows = []

    for i in range(1, 101):
        cid = f'LN-2026-{i:04d}'
        cust_id = f'CUST-{i:04d}'
        col_id = f'COL-{i:04d}'

        rand_val = random.random()
        if rand_val < 0.35:
            sec_code = 'REAL_ESTATE_CONSTRUCTION'
            c_type = 'Bất động sản thương mại và Đất dự án'
            haircut = 0.30
        elif rand_val < 0.58:
            sec_code = 'MANUFACTURING'
            c_type = 'Nhà xưởng và Dây chuyền thiết bị'
            haircut = 0.40
        elif rand_val < 0.72:
            sec_code = 'AGRICULTURE'
            c_type = 'Đất nông nghiệp và Nông sản'
            haircut = 0.50
        elif rand_val < 0.86:
            sec_code = 'COMMERCE'
            c_type = 'Hàng tồn kho và Kho bãi'
            haircut = 0.45
        else:
            sec_code = 'RETAIL'
            c_type = 'Bất động sản nhà ở và Xe ô tô'
            haircut = 0.25

        segment = 'CORPORATE' if i <= 50 else ('SME' if i <= 85 else 'RETAIL')
        if sec_code == 'RETAIL':
            segment = 'RETAIL'
        elif segment == 'RETAIL':
            sec_code = 'RETAIL'

        cust_name = corp_names[(i - 1) % len(corp_names)] + f' - Chi nhánh {i%7 + 1}' if segment != 'RETAIL' else f'Khách hàng cá nhân #{i:04d}'
        ead = round(random.uniform(10_000_000_000, 95_000_000_000), -6) if segment == 'CORPORATE' else round(random.uniform(1_500_000_000, 15_000_000_000), -6)
        int_rate = round(random.uniform(0.082, 0.125), 4)
        tenor_months = random.choice([12, 24, 36, 48, 60, 84, 120])
        remaining_term = round(float(tenor_months) / 12.0, 2)

        r_choice = random.choices(ratings_map, weights=[10, 15, 20, 25, 15, 10, 5])[0]
        rating, pd_base, stage = r_choice

        collateral_val = round(ead * random.uniform(1.05, 1.70), -6)
        rec = (collateral_val * (1.0 - haircut)) / ead
        lgd_base = round(max(0.1500, min(0.7500, 1.0 - rec)), 4)
        overdue = 0 if stage == 1 else (random.randint(31, 89) if stage == 2 else random.randint(91, 210))
        debt_grp = 1 if overdue <= 30 else (2 if overdue <= 90 else 3)

        customer_rows.append(f"('{cust_id}', '{cust_name}', '{segment}', '{sec_code}', '{rating}')")
        loan_rows.append(f"('{cid}', '{cust_id}', CURRENT_DATE, {ead:.2f}, 0.00, {int_rate:.4f}, {remaining_term:.2f}, {overdue}, {debt_grp}, {stage}, {pd_base:.6f}, {lgd_base:.5f})")
        col_rows.append(f"('{col_id}', '{c_type}', {collateral_val:.2f}, CURRENT_DATE, {haircut:.4f})")
        loan_col_rows.append(f"('{cid}', '{col_id}', {collateral_val:.2f}, 1)")

    # 4. Customers
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('-- 4. SEED 100 CUSTOMERS (CUSTOMERS)\n')
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('INSERT INTO customers (customer_id, customer_name, segment, sector_code, internal_rating) VALUES\n')
    f.write(',\n'.join(customer_rows))
    f.write('\nON CONFLICT (customer_id) DO NOTHING;\n\n')

    # 5. Loan Accounts
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('-- 5. SEED 100 LOAN ACCOUNTS (LOAN_ACCOUNTS)\n')
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('INSERT INTO loan_accounts (loan_id, customer_id, snapshot_date, ead, undrawn_limit, interest_rate, remaining_term, days_past_due, debt_group, current_stage, pd_base, baseline_lgd) VALUES\n')
    f.write(',\n'.join(loan_rows))
    f.write('\nON CONFLICT (loan_id) DO NOTHING;\n\n')

    # 6. Collaterals
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('-- 6. SEED 100 COLLATERALS (COLLATERALS)\n')
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('INSERT INTO collaterals (collateral_id, collateral_type, appraised_value, appraisal_date, liquidation_cost_rate) VALUES\n')
    f.write(',\n'.join(col_rows))
    f.write('\nON CONFLICT (collateral_id) DO NOTHING;\n\n')

    # 7. Loan Collateral
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('-- 7. SEED 100 LOAN COLLATERAL ALLOCATIONS (LOAN_COLLATERAL)\n')
    f.write('-- ------------------------------------------------------------------------------\n')
    f.write('INSERT INTO loan_collateral (loan_id, collateral_id, allocated_value, pledge_order) VALUES\n')
    f.write(',\n'.join(loan_col_rows))
    f.write('\nON CONFLICT (loan_id, collateral_id) DO NOTHING;\n\n')

    f.write('-- ==============================================================================\n')
    f.write('-- FINISHED SEED DATA (100% Normalized to 11 Tables & 5 Business Sectors)\n')
    f.write('-- ==============================================================================\n')

print(f"Generated {output_path} successfully!")
