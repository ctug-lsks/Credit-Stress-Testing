-- ==============================================================================
-- DATABASE SCHEMA: CREDIT STRESS TESTING & PROVISION ALLOCATION (IFRS 9)
-- Target RDBMS: PostgreSQL 14+ / 16+
-- Encoding: UTF-8
-- Designed for: Bank Credit Risk Management Division
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if re-creating
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS car_impact CASCADE;
DROP TABLE IF EXISTS ecl_results CASCADE;
DROP TABLE IF EXISTS stress_test_runs CASCADE;
DROP TABLE IF EXISTS industry_sensitivities CASCADE;
DROP TABLE IF EXISTS macro_scenarios CASCADE;
DROP TABLE IF EXISTS loan_contracts CASCADE;
DROP TABLE IF EXISTS system_users CASCADE;

-- ------------------------------------------------------------------------------
-- 1. SYSTEM USERS & ROLES (RBAC)
-- ------------------------------------------------------------------------------
CREATE TABLE system_users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(30) NOT NULL CHECK (role IN ('MAKER', 'CHECKER', 'APPROVER', 'AUDITOR')),
    department VARCHAR(100) DEFAULT 'Credit Risk Management',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE system_users IS 'Bang luu tru nguoi dung he thong va phan quyen theo 3 vai tro Maker, Checker, Approver';

-- ------------------------------------------------------------------------------
-- 2. LOAN CONTRACTS (DANH MUC HOP DONG VAY)
-- ------------------------------------------------------------------------------
CREATE TABLE loan_contracts (
    contract_id VARCHAR(30) PRIMARY KEY,
    customer_id VARCHAR(30) NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_segment VARCHAR(30) NOT NULL CHECK (customer_segment IN ('CORPORATE', 'SME', 'RETAIL')),
    industry_sector VARCHAR(50) NOT NULL CHECK (industry_sector IN (
        'REAL_ESTATE', 'CONSTRUCTION', 'MANUFACTURING', 'WHOLESALE_RETAIL', 'AGRICULTURE', 'CONSUMER_LOAN'
    )),
    original_ead NUMERIC(15, 2) NOT NULL CHECK (original_ead > 0), -- Dư nợ gốc (VNĐ)
    interest_rate NUMERIC(5, 4) NOT NULL,                          -- Lãi suất hàng năm (ví dụ 0.095 = 9.5%)
    remaining_tenor_months INT NOT NULL CHECK (remaining_tenor_months > 0),
    collateral_type VARCHAR(50) NOT NULL,                         -- Bất động sản, Máy móc, Tiền gửi, v.v.
    collateral_value NUMERIC(15, 2) NOT NULL DEFAULT 0,            -- Giá trị TSBĐ định giá gần nhất
    baseline_haircut NUMERIC(5, 4) NOT NULL DEFAULT 0.3000,        -- Haircut cơ sở (30%)
    internal_rating VARCHAR(10) NOT NULL,                         -- AAA, AA, A, BBB, BB, B, CCC
    baseline_pd NUMERIC(6, 5) NOT NULL,                           -- PD cơ sở 12 tháng (0.005 -> 0.15)
    baseline_lgd NUMERIC(6, 5) NOT NULL,                          -- LGD cơ sở
    initial_stage INT NOT NULL CHECK (initial_stage IN (1, 2, 3)), -- Stage IFRS 9 ban đầu
    overdue_days INT DEFAULT 0,                                   -- Số ngày quá hạn hiện tại
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_loan_contracts_sector ON loan_contracts(industry_sector);
CREATE INDEX idx_loan_contracts_stage ON loan_contracts(initial_stage);
CREATE INDEX idx_loan_contracts_rating ON loan_contracts(internal_rating);
COMMENT ON TABLE loan_contracts IS 'Danh muc hop dong tin dung dau vao tu Core Banking / DWH';

-- ------------------------------------------------------------------------------
-- 3. MACROECONOMIC SCENARIOS (KICH BAN VI MO)
-- ------------------------------------------------------------------------------
CREATE TABLE macro_scenarios (
    scenario_id SERIAL PRIMARY KEY,
    scenario_code VARCHAR(30) NOT NULL UNIQUE,                    -- BASELINE, ADVERSE, SEVERE, CUSTOM
    scenario_name VARCHAR(100) NOT NULL,
    description TEXT,
    gdp_growth_shock NUMERIC(5, 4) NOT NULL,                      -- Độ lệch tăng trưởng GDP (vd -0.025 = -2.5%)
    interest_rate_shock NUMERIC(5, 4) NOT NULL,                   -- Sốc lãi suất (vd +0.03 = +300 bps)
    real_estate_price_shock NUMERIC(5, 4) NOT NULL,               -- Sốc giá BĐS (vd -0.30 = -30%)
    fx_rate_shock NUMERIC(5, 4) DEFAULT 0.0000,                   -- Sốc tỷ giá USD/VND
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE macro_scenarios IS 'Cac kịch ban kiem dinh suc chiu dung vi mo';

-- ------------------------------------------------------------------------------
-- 4. INDUSTRY SENSITIVITIES (HE SO DO NHAY THEO NGANH)
-- ------------------------------------------------------------------------------
CREATE TABLE industry_sensitivities (
    sector_code VARCHAR(50) PRIMARY KEY,
    sector_name_vn VARCHAR(100) NOT NULL,
    beta_gdp NUMERIC(6, 4) NOT NULL,       -- Độ nhạy với biến động GDP
    beta_interest NUMERIC(6, 4) NOT NULL,  -- Độ nhạy với biến động Lãi suất
    beta_real_estate NUMERIC(6, 4) NOT NULL-- Độ nhạy với biến động Bất động sản
);

COMMENT ON TABLE industry_sensitivities IS 'He so hoi quy da bien ve do nhay vi mo cho tung nganh kinh te';

-- ------------------------------------------------------------------------------
-- 5. STRESS TEST RUNS (PHIEN CHAY MO PHONG & QUY TRINH PHE DUYET)
-- ------------------------------------------------------------------------------
CREATE TABLE stress_test_runs (
    run_id SERIAL PRIMARY KEY,
    run_code VARCHAR(50) NOT NULL UNIQUE,
    run_name VARCHAR(150) NOT NULL,
    scenario_id INT NOT NULL REFERENCES macro_scenarios(scenario_id),
    custom_gdp_shock NUMERIC(5, 4),
    custom_ir_shock NUMERIC(5, 4),
    custom_re_shock NUMERIC(5, 4),
    maker_id INT NOT NULL REFERENCES system_users(user_id),
    checker_id INT REFERENCES system_users(user_id),
    approver_id INT REFERENCES system_users(user_id),
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (status IN (
        'DRAFT', 'SUBMITTED', 'RECALCULATION_REQUESTED', 'APPROVED', 'REJECTED'
    )),
    total_ead NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_baseline_ecl NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_stressed_ecl NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_delta_provision NUMERIC(18, 2) NOT NULL DEFAULT 0,
    rejection_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_runs_status ON stress_test_runs(status);
COMMENT ON TABLE stress_test_runs IS 'Quan ly cac lan chay mo phong va trang thai phe duyet Maker - Checker - Approver';

-- ------------------------------------------------------------------------------
-- 6. ECL RESULTS (KET QUA TINH TOAN IFRS 9 TUNG KHOAN VAY SAU SOC)
-- ------------------------------------------------------------------------------
CREATE TABLE ecl_results (
    result_id BIGSERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES stress_test_runs(run_id) ON DELETE CASCADE,
    contract_id VARCHAR(30) NOT NULL REFERENCES loan_contracts(contract_id),
    baseline_pd NUMERIC(6, 5) NOT NULL,
    stressed_pd NUMERIC(6, 5) NOT NULL,
    baseline_lgd NUMERIC(6, 5) NOT NULL,
    stressed_lgd NUMERIC(6, 5) NOT NULL,
    baseline_stage INT NOT NULL,
    stressed_stage INT NOT NULL CHECK (stressed_stage IN (1, 2, 3)),
    is_sicr BOOLEAN NOT NULL DEFAULT FALSE,                       -- Danh dau Significant Increase in Credit Risk
    baseline_ecl NUMERIC(15, 2) NOT NULL DEFAULT 0,
    stressed_ecl NUMERIC(15, 2) NOT NULL DEFAULT 0,
    delta_provision NUMERIC(15, 2) NOT NULL DEFAULT 0,            -- Delta PS = Stressed ECL - Baseline ECL
    calculation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ecl_run_contract ON ecl_results(run_id, contract_id);
CREATE INDEX idx_ecl_stressed_stage ON ecl_results(stressed_stage);
COMMENT ON TABLE ecl_results IS 'Ket qua tinh toan chi tiet ECL va chuyen nhom Stage IFRS 9 cho tung khoan vay';

-- ------------------------------------------------------------------------------
-- 7. CAPITAL ADEQUACY RATIO IMPACT (TAC DONG LEN CAR & VON CAP 1)
-- ------------------------------------------------------------------------------
CREATE TABLE car_impact (
    impact_id SERIAL PRIMARY KEY,
    run_id INT NOT NULL UNIQUE REFERENCES stress_test_runs(run_id) ON DELETE CASCADE,
    baseline_tier1_capital NUMERIC(18, 2) NOT NULL,   -- Vốn Cấp 1 ban đầu
    baseline_tier2_capital NUMERIC(18, 2) NOT NULL,   -- Vốn Cấp 2 ban đầu
    baseline_rwa NUMERIC(18, 2) NOT NULL,             -- Tài sản có rủi ro (RWA) ban đầu
    baseline_car NUMERIC(6, 4) NOT NULL,              -- CAR ban đầu (ví dụ 0.118 = 11.8%)
    total_delta_provision NUMERIC(18, 2) NOT NULL,    -- Tổng chi phí dự phòng bổ sung khấu trừ vào Vốn Cấp 1
    stressed_tier1_capital NUMERIC(18, 2) NOT NULL,   -- Vốn Cấp 1 sau sốc
    stressed_rwa NUMERIC(18, 2) NOT NULL,             -- RWA sau sốc (điều chỉnh tăng do chuyển Stage)
    stressed_car NUMERIC(6, 4) NOT NULL,              -- CAR sau sốc
    car_change_bps NUMERIC(8, 2) NOT NULL,            -- Mức thay đổi CAR tính bằng basis points
    minimum_regulatory_car NUMERIC(6, 4) DEFAULT 0.0800, -- Ngưỡng tối thiểu 8.0% theo Thông tư 41
    is_capital_adequate BOOLEAN NOT NULL,             -- Đạt hay không đạt chuẩn an toàn vốn
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE car_impact IS 'Tong hop tac dong len an toan von CAR cua toan ngan hang';

-- ------------------------------------------------------------------------------
-- 8. AUDIT LOGS (NHAT KY PHE DUYET & KIEM TOAN)
-- ------------------------------------------------------------------------------
CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES stress_test_runs(run_id) ON DELETE CASCADE,
    actor_id INT NOT NULL REFERENCES system_users(user_id),
    action VARCHAR(50) NOT NULL, -- CREATE, SUBMIT, RECALCULATE, APPROVE, REJECT, EXPORT
    action_note TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_run_id ON audit_logs(run_id);
COMMENT ON TABLE audit_logs IS 'Nhat ky kiem toan ghi nhan tat ca thao tac Maker - Checker - Approver';
