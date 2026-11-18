import random

random.seed(42)

sectors = [
    ('REAL_ESTATE', 'Bất động sản', 1.85, 2.10, -2.40),
    ('CONSTRUCTION', 'Xây dựng & Hạ tầng', 1.50, 1.80, -1.60),
    ('MANUFACTURING', 'Sản xuất & Chế biến', 1.20, 1.30, -0.40),
    ('WHOLESALE_RETAIL', 'Bán buôn & Bán lẻ', 0.95, 1.10, -0.30),
    ('AGRICULTURE', 'Nông - Lâm - Thủy sản', 0.80, 0.90, -0.20),
    ('CONSUMER_LOAN', 'Cho vay tiêu dùng & Bán lẻ', 1.10, 1.50, -0.80)
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

print("Generating SQL...")
with open('database/seed_data_postgresql.sql', 'w', encoding='utf-8') as f:
    f.write('-- ==============================================================================\n')
    f.write('-- SEED DATA FOR CREDIT STRESS TESTING & IFRS 9 (POSTGRESQL)\n')
    f.write('-- ==============================================================================\n\n')

    # Users
    f.write('-- 1. SEED USERS\n')
    f.write("""INSERT INTO system_users (user_id, username, full_name, email, role, department) VALUES
(1, 'maker_an', 'Nguyễn Văn An (Maker)', 'an.nguyen@bank.vn', 'MAKER', 'Credit Risk Modeling & Analytics'),
(2, 'checker_binh', 'Trần Thị Bình (Checker)', 'binh.tran@bank.vn', 'CHECKER', 'Risk Control & Model Validation'),
(3, 'approver_cuong', 'Lê Hoàng Cường (Approver/CRO)', 'cuong.le@bank.vn', 'APPROVER', 'Executive Board / CRO'),
(4, 'auditor_dung', 'Phạm Minh Dũng (Auditor)', 'dung.pham@bank.vn', 'AUDITOR', 'Internal Audit Division')
ON CONFLICT (user_id) DO NOTHING;\n\n""")

    # Scenarios
    f.write('-- 2. SEED MACRO SCENARIOS\n')
    f.write("""INSERT INTO macro_scenarios (scenario_id, scenario_code, scenario_name, description, gdp_growth_shock, interest_rate_shock, real_estate_price_shock, fx_rate_shock) VALUES
(1, 'BASELINE', 'Kịch bản Cơ sở (Baseline 2026)', 'Tăng trưởng kinh tế ổn định theo mục tiêu Quốc hội, lãi suất giữ nguyên, giá BĐS đi ngang.', 0.0000, 0.0000, 0.0000, 0.0000),
(2, 'ADVERSE', 'Kịch bản Căng thẳng Vừa (Adverse)', 'Kinh tế toàn cầu giảm tốc, GDP giảm 1.5%, lãi suất tăng thêm 200 bps, thị trường BĐS giảm giá 15%.', -0.0150, 0.0200, -0.1500, 0.0300),
(3, 'SEVERE', 'Kịch bản Khủng hoảng Nghiêm trọng (Severely Adverse)', 'Lạm phát phi mã, GDP giảm sâu 3.0%, lãi suất tăng sốc 400 bps, thị trường BĐS đóng băng giảm 35%.', -0.0300, 0.0400, -0.3500, 0.0600)
ON CONFLICT (scenario_id) DO NOTHING;\n\n""")

    # Industry sensitivities
    f.write('-- 3. SEED INDUSTRY SENSITIVITIES\n')
    f.write("""INSERT INTO industry_sensitivities (sector_code, sector_name_vn, beta_gdp, beta_interest, beta_real_estate) VALUES
('REAL_ESTATE', 'Bất động sản', 1.8500, 2.1000, -2.4000),
('CONSTRUCTION', 'Xây dựng & Hạ tầng', 1.5000, 1.8000, -1.6000),
('MANUFACTURING', 'Sản xuất & Chế biến', 1.2000, 1.3000, -0.4000),
('WHOLESALE_RETAIL', 'Bán buôn & Bán lẻ', 0.9500, 1.1000, -0.3000),
('AGRICULTURE', 'Nông - Lâm - Thủy sản', 0.8000, 0.9000, -0.2000),
('CONSUMER_LOAN', 'Cho vay tiêu dùng & Bán lẻ', 1.1000, 1.5000, -0.8000)
ON CONFLICT (sector_code) DO NOTHING;\n\n""")

    # 100 Loan Contracts
    f.write('-- 4. SEED 100 LOAN CONTRACTS\n')
    f.write('INSERT INTO loan_contracts (contract_id, customer_id, customer_name, customer_segment, industry_sector, original_ead, interest_rate, remaining_tenor_months, collateral_type, collateral_value, baseline_haircut, internal_rating, baseline_pd, baseline_lgd, initial_stage, overdue_days) VALUES\n')
    
    rows = []
    corp_names = [
        'Tập đoàn Phát triển Đô thị Horizon', 'Công ty CP Đầu tư Địa ốc Nam Việt', 'Tổng Công ty Xây dựng Thăng Long',
        'Công ty Dệt may Phong Phú', 'Tập đoàn Thép Đại Nam', 'Công ty Chế biến Thủy hải sản Biển Đông',
        'Chuỗi Siêu thị Bách Hóa Xanh Plaza', 'Công ty Nông nghiệp Hitech Vinaseed', 'Công ty CP Xây lắp Dầu khí',
        'Tập đoàn Bất động sản Hoàng Gia', 'Công ty Nhựa & Bao bì Tân Tiến', 'Công ty Dược phẩm Trung ương Hà Nội'
    ]
    
    for i in range(1, 101):
        cid = f'LN-2026-{i:04d}'
        cust_id = f'CUST-{i:04d}'
        
        rand_val = random.random()
        if rand_val < 0.28:
            sec_code = 'REAL_ESTATE'
            c_type = 'Bất động sản thương mại & Đất dự án'
            haircut = 0.30
        elif rand_val < 0.46:
            sec_code = 'CONSTRUCTION'
            c_type = 'Bất động sản & Máy móc thi công'
            haircut = 0.35
        elif rand_val < 0.66:
            sec_code = 'MANUFACTURING'
            c_type = 'Nhà xưởng & Dây chuyền thiết bị'
            haircut = 0.40
        elif rand_val < 0.82:
            sec_code = 'WHOLESALE_RETAIL'
            c_type = 'Hàng tồn kho & Kho bãi'
            haircut = 0.45
        elif rand_val < 0.92:
            sec_code = 'AGRICULTURE'
            c_type = 'Đất nông nghiệp & Nông sản'
            haircut = 0.50
        else:
            sec_code = 'CONSUMER_LOAN'
            c_type = 'Bất động sản nhà ở & Xe ô tô'
            haircut = 0.25
            
        segment = 'CORPORATE' if i <= 50 else ('SME' if i <= 85 else 'RETAIL')
        cust_name = corp_names[(i - 1) % len(corp_names)] + f' - Chi nhánh {i%7 + 1}' if segment != 'RETAIL' else f'Khách hàng cá nhân #{i:04d}'
        
        ead = round(random.uniform(10_000_000_000, 95_000_000_000), -6) if segment == 'CORPORATE' else round(random.uniform(1_500_000_000, 15_000_000_000), -6)
        int_rate = round(random.uniform(0.082, 0.125), 4)
        tenor = random.choice([12, 24, 36, 48, 60, 84, 120])
        
        r_choice = random.choices(ratings_map, weights=[10, 15, 20, 25, 15, 10, 5])[0]
        rating, pd_base, stage = r_choice
        
        collateral = round(ead * random.uniform(1.05, 1.70), -6)
        rec = (collateral * (1 - haircut)) / ead
        lgd_base = round(max(0.1500, min(0.7500, 1.0 - rec)), 4)
        overdue = 0 if stage == 1 else (random.randint(31, 89) if stage == 2 else random.randint(91, 210))
        
        row_str = f"('{cid}', '{cust_id}', '{cust_name}', '{segment}', '{sec_code}', {ead:.2f}, {int_rate:.4f}, {tenor}, '{c_type}', {collateral:.2f}, {haircut:.4f}, '{rating}', {pd_base:.5f}, {lgd_base:.5f}, {stage}, {overdue})"
        rows.append(row_str)
        
    f.write(',\n'.join(rows))
    f.write(';\n\n')
    f.write('-- FINISHED SEED DATA\n')

print("Generated database/seed_data_postgresql.sql successfully!")
