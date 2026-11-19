import os
import django
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.hashers import make_password

from stress_app.models import (
    SystemUser, MacroScenario, IndustrySensitivity,
    Customer, LoanAccount, Collateral, LoanCollateral
)

print("Starting DB Seeding...")

# 1. System Users (SYSTEM_USERS)
default_pwd_hash = make_password('123456')

users_data = [
    (1, 'maker_an', 'Nguyễn Văn An', 'an.nguyen@bank.vn', 'MAKER', 'Phòng Đo lường Rủi ro'),
    (2, 'checker_binh', 'Trần Thị Bình', 'binh.tran@bank.vn', 'CHECKER', 'Phòng Quản lý rủi ro'),
    (3, 'approver_cuong', 'Lê Hoàng Cường', 'cuong.le@bank.vn', 'APPROVER', 'Ban Điều hành / Khối Quản lý rủi ro'),
    (4, 'auditor_dung', 'Phạm Minh Dũng', 'dung.pham@bank.vn', 'AUDITOR', 'Khối Kiểm toán Nội bộ'),
    (5, 'admin_system', 'Quản trị viên Hệ thống (IT Admin)', 'admin@bank.vn', 'ADMIN', 'Khối CNTT & Quản trị Hệ thống')
]
for uid, username, full_name, email, role, dept in users_data:
    SystemUser.objects.update_or_create(
        id=uid,
        defaults={
            'username': username,
            'full_name': full_name,
            'email': email,
            'role': role,
            'department': dept,
            'password_hash': default_pwd_hash
        }
    )
print("Seeded 5 System Users (SYSTEM_USERS) with hashed passwords.")

# 2. Macro Scenarios (MACRO_SCENARIOS)
scenarios_data = [
    (1, 'BASELINE', 'Kịch bản Cơ sở 2026', 'Baseline', 'Tăng trưởng kinh tế ổn định theo mục tiêu Quốc hội (6.5%), lãi suất đi ngang, thị trường BĐS ổn định.', 0.0000, 0.0000, 0.0000, 0.0000, 2.0, 0.500),
    (2, 'ADVERSE', 'Kịch bản Căng thẳng Vừa', 'Adverse', 'Kinh tế toàn cầu suy giảm, GDP giảm 1.5%, lãi suất tăng +200 bps, giá BĐS giảm 15%.', -0.0150, 0.0200, -0.1500, 0.0300, 2.5, 0.300),
    (3, 'SEVERE', 'Kịch bản Khủng hoảng Nghiêm trọng', 'Severe', 'Lạm phát toàn cầu bùng phát, GDP sụt giảm 3.0%, lãi suất tăng sốc +400 bps, thị trường BĐS đóng băng giảm 35%.', -0.0300, 0.0400, -0.3500, 0.0600, 3.0, 0.200)
]
for sid, code, name, stype, desc, gdp, ir, re, fx, rec_yrs, weight in scenarios_data:
    MacroScenario.objects.update_or_create(
        id=sid,
        defaults={
            'scenario_code': code,
            'scenario_name': name,
            'scenario_type': stype,
            'description': desc,
            'gdp_growth_shock': gdp,
            'interest_rate_shock': ir,
            'real_estate_price_shock': re,
            'fx_rate_shock': fx,
            'recovery_time_years': rec_yrs,
            'scenario_weight': weight,
            'status': 'Approved',
            'created_by': 'Khối Quản lý Rủi ro'
        }
    )
print("Seeded 3 Macro Scenarios (MACRO_SCENARIOS).")

# 3. Industry Sensitivities (SECTOR_SENSITIVITY) - 5 Nhóm ngành chuẩn theo Báo cáo
IndustrySensitivity.objects.all().delete()
sensitivities_data = [
    ('REAL_ESTATE_CONSTRUCTION', 'BĐS và Xây dựng', 1.8000, 2.0000, -2.2000, 3.500),
    ('MANUFACTURING', 'Sản xuất và Chế biến', 1.3000, 1.4000, -0.4000, 2.200),
    ('AGRICULTURE', 'Nông - Lâm - Thủy sản', 0.8000, 0.9000, -0.2000, 1.800),
    ('COMMERCE', 'Thương mại', 1.2000, 1.3000, -0.5000, 2.500),
    ('RETAIL', 'Bán lẻ', 1.1000, 1.6000, -0.7000, 2.800)
]
for code, name_vn, b_gdp, b_ir, b_re, mult in sensitivities_data:
    IndustrySensitivity.objects.create(
        sector_code=code,
        sector_name_vn=name_vn,
        beta_gdp=b_gdp,
        beta_interest=b_ir,
        beta_real_estate=b_re,
        pd_multiplier=mult
    )
print("Seeded 5 Industry Sensitivities (SECTOR_SENSITIVITY).")

# 4. 100 Loan Contracts, Customers, Loan Accounts, Collaterals, and LoanCollateral
random.seed(42)
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
    'Tập đoàn Bất động sản Hoàng Gia', 'Công ty Nhựa và Bao bì Tân Tiến', 'Công ty Dược phẩm Trung ương Hà Nội'
]

customers_map = {}
loans_to_create = []
collaterals_to_create = []
loan_collateral_to_create = []

now = timezone.now()

for i in range(1, 101):
    cid = f'LN-2026-{i:04d}'
    cust_id = f'CUST-{i:04d}'
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
    tenor = random.choice([12, 24, 36, 48, 60, 84, 120])
    r_choice = random.choices(ratings_map, weights=[10, 15, 20, 25, 15, 10, 5])[0]
    rating, pd_base, stage = r_choice
    collateral_val = round(ead * random.uniform(1.05, 1.70), -6)
    rec = (collateral_val * (1 - haircut)) / ead
    lgd_base = round(max(0.1500, min(0.7500, 1.0 - rec)), 4)
    overdue = 0 if stage == 1 else (random.randint(31, 89) if stage == 2 else random.randint(91, 210))
    debt_grp = 1 if overdue <= 30 else (2 if overdue <= 90 else 3)

    # 1. Customer
    cust = Customer(
        customer_id=cust_id,
        customer_name=cust_name,
        segment=segment,
        sector_code=sec_code,
        internal_rating=rating,
        created_at=now
    )
    customers_map[cust_id] = cust

    # 2. LoanAccount
    loan = LoanAccount(
        loan_id=cid,
        customer=cust,
        snapshot_date=now.date(),
        ead=ead,
        undrawn_limit=0,
        interest_rate=int_rate,
        remaining_term=round(float(tenor)/12.0, 2),
        days_past_due=overdue,
        debt_group=debt_grp,
        current_stage=stage,
        pd_base=pd_base,
        baseline_lgd=lgd_base,
        created_at=now
    )
    loans_to_create.append(loan)

    # 3. Collateral
    col_id = f'COL-{i:04d}'
    col = Collateral(
        collateral_id=col_id,
        collateral_type=c_type,
        appraised_value=collateral_val,
        appraisal_date=now.date(),
        liquidation_cost_rate=haircut,
        created_at=now
    )
    collaterals_to_create.append(col)

    # 4. LoanCollateral
    loan_collateral_to_create.append(LoanCollateral(
        loan=loan,
        collateral=col,
        allocated_value=collateral_val
    ))

Customer.objects.all().delete()
Customer.objects.bulk_create(list(customers_map.values()))

LoanAccount.objects.all().delete()
LoanAccount.objects.bulk_create(loans_to_create)

Collateral.objects.all().delete()
Collateral.objects.bulk_create(collaterals_to_create)

LoanCollateral.objects.all().delete()
LoanCollateral.objects.bulk_create(loan_collateral_to_create)

print(f"Seeded 100 CUSTOMERS, 100 LOAN_ACCOUNTS, 100 COLLATERALS, and 100 LOAN_COLLATERAL successfully!")
