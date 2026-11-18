# THIẾT KẾ CƠ SỞ DỮ LIỆU: HỆ THỐNG KIỂM ĐỊNH SỨC CHỊU ĐỰNG TÍN DỤNG & IFRS 9

Thư mục này chứa toàn bộ thiết kế, mã nguồn khởi tạo (DDL) và dữ liệu mẫu (Seed Data) cho hệ thống **Credit Stress Testing & Provision Allocation (IFRS 9)** sử dụng hệ quản trị CSDL **PostgreSQL 14+ / 16+**.

---

## 1. Cấu trúc tệp tin trong thư mục `database/`

* `schema_postgresql.sql`: Tập lệnh DDL tạo toàn bộ cấu trúc bảng, khóa chính, khóa ngoại, ràng buộc kiểm tra (Check Constraints), chỉ mục (Indexes) và chú thích (Comments).
* `seed_data_postgresql.sql`: Dữ liệu mẫu ban đầu gồm:
  * 4 Tài khoản người dùng phân quyền theo 3 vai trò: Maker (Chuyên viên đo lường), Checker (Trưởng phòng QLRR), Approver (Giám đốc Khối/CEO), Auditor (Kiểm toán).
  * 3 Kịch bản vĩ mô: Baseline, Adverse, Severely Adverse.
  * Hệ số độ nhạy vĩ mô ($\beta$) cho 6 ngành kinh tế trọng yếu.
  * 100 Hợp đồng tín dụng mẫu với dư nợ, xếp hạng tín nhiệm, giá trị tài sản bảo đảm, tỷ lệ trích lập IFRS 9 ban đầu.
* `docker-compose.yml`: Cấu hình Docker để khởi chạy PostgreSQL 16 và pgAdmin 4 chỉ với một câu lệnh.
* `generate_seed.py`: Script Python sinh ngẫu nhiên có kiểm soát 100 hợp đồng vay mẫu theo logic tài chính.

---

## 2. Thông tin kết nối mặc định (PostgreSQL)

| Tham số | Giá trị mặc định |
| :--- | :--- |
| **Host** | `localhost` |
| **Port** | `5432` |
| **Database Name** | `credit_risk_db` |
| **Username** | `risk_admin` |
| **Password** | `RiskAdmin2026!` |

---

## 3. Danh mục 7 Bảng Dữ liệu Chính (Data Dictionary)

1. `system_users`: Quản lý tài khoản và phân quyền người dùng theo vai trò (Role-Based Access Control).
2. `loan_contracts`: Lưu trữ danh mục 100 hợp đồng tín dụng từ Core Banking / DWH.
3. `macro_scenarios`: Định nghĩa các kịch bản sốc vĩ mô ($\Delta GDP$, $\Delta Interest Rate$, $\Delta Real Estate$).
4. `industry_sensitivities`: Hệ số độ nhạy hồi quy kinh tế lượng theo từng ngành nghề.
5. `stress_test_runs`: Quản lý các phiên mô phỏng và vòng đời phê duyệt (DRAFT $\to$ SUBMITTED $\to$ APPROVED).
6. `ecl_results`: Chi tiết tính toán tổn thất dự kiến IFRS 9 ($PD_{stress}$, $LGD_{stress}$, di chuyển Stage, $ECL$, $\Delta PS$) cho từng hợp đồng.
7. `car_impact`: Tác động tổng hợp lên Vốn Cấp 1, Tổng tài sản có rủi ro (RWA) và Hệ số an toàn vốn (CAR) so với ngưỡng 8.0%.
8. `audit_logs`: Nhật ký kiểm toán ghi vết mọi hành vi phê duyệt / yêu cầu tính lại.
