-- ==============================================================================
-- DATABASE SCHEMA: CREDIT STRESS TESTING & PROVISION ALLOCATION (IFRS 9)
-- Target RDBMS: PostgreSQL 14+ / 16+
-- Encoding: UTF-8
-- Designed for: Bank Credit Risk Management Division
-- Standard Compliance: IFRS 9, Circular 11/2021/TT-NHNN, Circular 14/2025/TT-NHNN
-- Security Model: RBAC, PBKDF2 Password Hashing, Four-Eyes Principle, Immutable Audit Trail
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables in reverse dependency order if re-creating
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS car_impacts CASCADE;
DROP TABLE IF EXISTS ecl_results CASCADE;
DROP TABLE IF EXISTS stress_results CASCADE;
DROP TABLE IF EXISTS stress_test_runs CASCADE;
DROP TABLE IF EXISTS ecl_reports CASCADE;
DROP TABLE IF EXISTS loan_collateral CASCADE;
DROP TABLE IF EXISTS collaterals CASCADE;
DROP TABLE IF EXISTS loan_accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS industry_sensitivities CASCADE;
DROP TABLE IF EXISTS sector_sensitivity CASCADE;
DROP TABLE IF EXISTS macro_scenarios CASCADE;
DROP TABLE IF EXISTS system_users CASCADE;

-- ------------------------------------------------------------------------------
-- 1. SYSTEM USERS & ROLES (RBAC & AUTHENTICATION - Bảng 34 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE system_users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(30) NOT NULL CHECK (role IN ('MAKER', 'CHECKER', 'APPROVER', 'AUDITOR', 'ADMIN')),
    department VARCHAR(100) DEFAULT 'Khối Quản lý Rủi ro',
    password_hash VARCHAR(255) NOT NULL DEFAULT '',
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_users_role ON system_users(role);
CREATE INDEX idx_system_users_username ON system_users(username);
COMMENT ON TABLE system_users IS 'Bảng lưu trữ người dùng hệ thống, phân quyền RBAC và băm mật khẩu chuẩn PBKDF2 with SHA-256';

-- ------------------------------------------------------------------------------
-- 2. SECTOR SENSITIVITY (HỆ SỐ ĐỘ NHẠY THEO NGÀNH - Bảng 29 / 36 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE sector_sensitivity (
    sector_code VARCHAR(50) PRIMARY KEY,
    sector_name_vn VARCHAR(100) NOT NULL,
    beta_gdp NUMERIC(6, 4) NOT NULL,
    beta_interest NUMERIC(6, 4) NOT NULL,
    beta_real_estate NUMERIC(6, 4) NOT NULL,
    pd_multiplier NUMERIC(6, 3) NOT NULL DEFAULT 1.000,
    CONSTRAINT chk_standard_sectors CHECK (sector_code IN (
        'REAL_ESTATE_CONSTRUCTION', 'MANUFACTURING', 'AGRICULTURE', 'COMMERCE', 'RETAIL'
    ))
);

-- Alias view for industry_sensitivities backward compatibility
CREATE OR REPLACE VIEW industry_sensitivities AS SELECT * FROM sector_sensitivity;
COMMENT ON TABLE sector_sensitivity IS 'Hệ số nhạy cảm vĩ mô cho 5 ngành kinh tế chuẩn hóa (BĐS và Xây dựng, Sản xuất và Chế biến, Nông - Lâm - Thủy sản, Thương mại, Bán lẻ)';

-- ------------------------------------------------------------------------------
-- 3. CUSTOMERS (THÔNG TIN KHÁCH HÀNG VAY - Bảng 24 / 31 Báo cáo)
-- Quan hệ 1-N: SECTOR_SENSITIVITY (1) -> CUSTOMERS (N)
-- ------------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    segment VARCHAR(30) NOT NULL CHECK (segment IN ('CORPORATE', 'SME', 'RETAIL', 'Doanh nghiệp', 'Bán lẻ')),
    sector_code VARCHAR(50) NOT NULL REFERENCES sector_sensitivity(sector_code) ON UPDATE CASCADE ON DELETE RESTRICT,
    internal_rating VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customers_sector ON customers(sector_code);
CREATE INDEX idx_customers_rating ON customers(internal_rating);
COMMENT ON TABLE customers IS 'Danh mục thông tin định danh khách hàng vay vốn';

-- ------------------------------------------------------------------------------
-- 4. LOAN ACCOUNTS (HỢP ĐỒNG KHOẢN VAY TẠI NGÀY CHỐT - Bảng 25 / 32 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE loan_accounts (
    loan_id VARCHAR(30) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    ead NUMERIC(18, 2) NOT NULL CHECK (ead > 0),
    undrawn_limit NUMERIC(18, 2) NOT NULL DEFAULT 0,
    interest_rate NUMERIC(6, 4) NOT NULL,
    remaining_term NUMERIC(6, 2) NOT NULL,
    days_past_due INT NOT NULL DEFAULT 0,
    debt_group SMALLINT NOT NULL DEFAULT 1 CHECK (debt_group BETWEEN 1 AND 5),
    current_stage SMALLINT NOT NULL DEFAULT 1 CHECK (current_stage IN (1, 2, 3)),
    pd_base NUMERIC(8, 6) NOT NULL,
    baseline_lgd NUMERIC(6, 5) NOT NULL DEFAULT 0.45000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_loan_accounts_customer ON loan_accounts(customer_id);
CREATE INDEX idx_loan_accounts_stage ON loan_accounts(current_stage);
CREATE INDEX idx_loan_accounts_debt_group ON loan_accounts(debt_group);
COMMENT ON TABLE loan_accounts IS 'Danh mục khoản vay chuẩn hóa tại ngày chốt số liệu';

-- ------------------------------------------------------------------------------
-- 5. COLLATERALS (TÀI SẢN BẢO ĐẢM - Bảng 26 / 33 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE collaterals (
    collateral_id VARCHAR(30) PRIMARY KEY,
    collateral_type VARCHAR(100) NOT NULL,
    appraised_value NUMERIC(18, 2) NOT NULL CHECK (appraised_value >= 0),
    appraisal_date DATE,
    liquidation_cost_rate NUMERIC(5, 4) NOT NULL DEFAULT 0.1000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE collaterals IS 'Danh mục tài sản bảo đảm định giá và tỷ lệ chi phí thanh lý';

-- ------------------------------------------------------------------------------
-- 6. LOAN COLLATERAL (QUAN HỆ KHOẢN VAY - TÀI SẢN BẢO ĐẢM N-N - Bảng 27 / 34 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE loan_collateral (
    id BIGSERIAL PRIMARY KEY,
    loan_id VARCHAR(30) NOT NULL REFERENCES loan_accounts(loan_id) ON DELETE CASCADE,
    collateral_id VARCHAR(30) NOT NULL REFERENCES collaterals(collateral_id) ON DELETE CASCADE,
    allocated_value NUMERIC(18, 2) NOT NULL CHECK (allocated_value >= 0),
    pledge_order INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_loan_collateral UNIQUE (loan_id, collateral_id)
);

CREATE INDEX idx_loan_collateral_loan ON loan_collateral(loan_id);
CREATE INDEX idx_loan_collateral_collateral ON loan_collateral(collateral_id);
COMMENT ON TABLE loan_collateral IS 'Bảng liên kết quan hệ N-N giữa khoản vay và tài sản bảo đảm kèm giá trị phân bổ';

-- ------------------------------------------------------------------------------
-- 7. MACROECONOMIC SCENARIOS (KỊCH BẢN VĨ MÔ - Bảng 28 / 35 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE macro_scenarios (
    scenario_id SERIAL PRIMARY KEY,
    scenario_code VARCHAR(30) NOT NULL UNIQUE,
    scenario_name VARCHAR(100) NOT NULL,
    scenario_type VARCHAR(30) DEFAULT 'Baseline',
    description TEXT,
    gdp_growth_shock NUMERIC(6, 4) NOT NULL,
    interest_rate_shock NUMERIC(6, 4) NOT NULL,
    real_estate_price_shock NUMERIC(6, 4) NOT NULL,
    fx_rate_shock NUMERIC(6, 4) DEFAULT 0.0000,
    recovery_time_years NUMERIC(4, 1) DEFAULT 2.0,
    scenario_weight NUMERIC(5, 3) DEFAULT 0.500,
    status VARCHAR(20) DEFAULT 'Approved',
    created_by VARCHAR(100) DEFAULT 'Khối Quản lý Rủi ro',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE macro_scenarios IS 'Danh mục kịch bản kiểm định sức chịu đựng vĩ mô (Baseline, Adverse, Severe)';

-- ------------------------------------------------------------------------------
-- 8. STRESS TEST RUNS / ECL REPORTS (PHIÊN KIỂM ĐỊNH & WORKFLOW - Bảng 30 / 37 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE stress_test_runs (
    run_id SERIAL PRIMARY KEY,
    run_code VARCHAR(50) NOT NULL UNIQUE,
    run_name VARCHAR(150) NOT NULL,
    scenario_id INT NOT NULL REFERENCES macro_scenarios(scenario_id),
    custom_gdp_shock NUMERIC(6, 4),
    custom_ir_shock NUMERIC(6, 4),
    custom_re_shock NUMERIC(6, 4),
    custom_unemp_shock NUMERIC(6, 4) DEFAULT 0.0000,
    snapshot_date DATE DEFAULT CURRENT_DATE,
    maker_id INT NOT NULL REFERENCES system_users(user_id),
    checker_id INT REFERENCES system_users(user_id),
    approver_id INT REFERENCES system_users(user_id),
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (status IN (
        'DRAFT', 'SUBMITTED', 'PENDING_APPROVAL', 'RECALCULATION_REQUESTED', 'APPROVED', 'REJECTED'
    )),
    total_ead NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_baseline_ecl NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_stressed_ecl NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_delta_provision NUMERIC(18, 2) NOT NULL DEFAULT 0,
    npl_stress NUMERIC(6, 4),
    llr_stress NUMERIC(8, 4),
    rejection_reason TEXT,
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_runs_status ON stress_test_runs(status);
CREATE INDEX idx_runs_maker ON stress_test_runs(maker_id);
-- Alias view for ecl_reports backward compatibility
CREATE OR REPLACE VIEW ecl_reports AS SELECT * FROM stress_test_runs;
COMMENT ON TABLE stress_test_runs IS 'Báo cáo tổng hợp kiểm định và quy trình phê duyệt Maker - Checker - Approver';

-- ------------------------------------------------------------------------------
-- 9. STRESS RESULTS / ECL RESULTS (KẾT QUẢ KIỂM ĐỊNH CHI TIẾT - Bảng 31 / 38 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE stress_results (
    result_id BIGSERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES stress_test_runs(run_id) ON DELETE CASCADE,
    loan_account_id VARCHAR(30) NOT NULL REFERENCES loan_accounts(loan_id) ON DELETE CASCADE,
    baseline_pd NUMERIC(8, 6) NOT NULL,
    stressed_pd NUMERIC(8, 6) NOT NULL,
    baseline_lgd NUMERIC(6, 5) NOT NULL,
    stressed_lgd NUMERIC(6, 5) NOT NULL,
    baseline_stage INT NOT NULL,
    stressed_stage INT NOT NULL CHECK (stressed_stage IN (1, 2, 3)),
    discount_factor NUMERIC(8, 6) NOT NULL DEFAULT 0.913240,
    is_sicr BOOLEAN NOT NULL DEFAULT FALSE,
    early_warning_flag BOOLEAN NOT NULL DEFAULT FALSE,
    baseline_ecl NUMERIC(18, 2) NOT NULL DEFAULT 0,
    stressed_ecl NUMERIC(18, 2) NOT NULL DEFAULT 0,
    delta_provision NUMERIC(18, 2) NOT NULL DEFAULT 0,
    calculation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stress_results_run ON stress_results(run_id);
CREATE INDEX idx_stress_results_loan ON stress_results(loan_account_id);
-- Alias view for ecl_results backward compatibility
CREATE OR REPLACE VIEW ecl_results AS SELECT * FROM stress_results;
COMMENT ON TABLE stress_results IS 'Kết quả kiểm định chi tiết ECL và dịch chuyển Stage IFRS 9 từng hợp đồng';

-- ------------------------------------------------------------------------------
-- 10. CAR IMPACTS (TÁC ĐỘNG TỶ LỆ AN TOÀN VỐN CAR - Bảng 32 / 39 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE car_impacts (
    impact_id SERIAL PRIMARY KEY,
    run_id INT NOT NULL UNIQUE REFERENCES stress_test_runs(run_id) ON DELETE CASCADE,
    baseline_tier1_capital NUMERIC(18, 2) NOT NULL,
    baseline_tier2_capital NUMERIC(18, 2) NOT NULL,
    baseline_rwa NUMERIC(18, 2) NOT NULL,
    baseline_car NUMERIC(6, 4) NOT NULL,
    total_delta_provision NUMERIC(18, 2) NOT NULL,
    stressed_tier1_capital NUMERIC(18, 2) NOT NULL,
    stressed_rwa NUMERIC(18, 2) NOT NULL,
    stressed_car NUMERIC(6, 4) NOT NULL,
    car_change_bps NUMERIC(8, 2) NOT NULL,
    minimum_regulatory_car NUMERIC(6, 4) DEFAULT 0.0800,
    is_capital_adequate BOOLEAN NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Alias view for car_impact backward compatibility
CREATE OR REPLACE VIEW car_impact AS SELECT * FROM car_impacts;
COMMENT ON TABLE car_impacts IS 'Tổng hợp tác động trích lập bổ sung lên Vốn cấp 1, RWA và tỷ lệ an toàn vốn CAR (Thông tư 14/2025/TT-NHNN)';

-- ------------------------------------------------------------------------------
-- 11. AUDIT LOGS (NHẬT KÝ BẤT BIẾN APPEND-ONLY - Bảng 33 / 40 Báo cáo)
-- ------------------------------------------------------------------------------
CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    run_id INT REFERENCES stress_test_runs(run_id) ON DELETE SET NULL,
    run_code VARCHAR(50) DEFAULT '',
    actor_id INT NOT NULL REFERENCES system_users(user_id),
    action VARCHAR(50) NOT NULL,
    action_note TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_run ON audit_logs(run_id);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id);
CREATE INDEX idx_audit_logs_time ON audit_logs(created_at);
COMMENT ON TABLE audit_logs IS 'Nhật ký kiểm toán bất biến ghi nhận mọi thay đổi trạng thái theo nguyên tắc Append-only';
