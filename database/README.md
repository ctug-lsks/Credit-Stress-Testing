# THIẾT KẾ CƠ SỞ DỮ LIỆU: HỆ THỐNG KIỂM ĐỊNH SỨC CHỊU ĐỰNG TÍN DỤNG & IFRS 9

Thư mục này chứa toàn bộ thiết kế, mã nguồn khởi tạo (DDL) và dữ liệu mẫu (Seed Data) cho hệ thống **Credit Stress Testing & Provision Allocation (IFRS 9)** sử dụng hệ quản trị CSDL **PostgreSQL 14+ / 16+** (kèm bản SQLite phục vụ môi trường chạy thử nghiệm nhanh).

---

## 1. Cấu trúc tệp tin trong thư mục `database/`

* `schema_postgresql.sql`: Tập lệnh DDL tạo toàn bộ cấu trúc **11 bảng chuẩn hóa**, khóa chính, khóa ngoại (Foreign Keys), ràng buộc kiểm tra (Check Constraints), chỉ mục (Indexes) và chú thích (Comments), khớp 100% với Báo cáo kiến tập (Bảng 22 & Bảng 23).
* `seed_data_postgresql.sql`: Dữ liệu mẫu chuẩn hóa gồm:
  * 5 Tài khoản người dùng phân quyền RBAC: Maker, Checker, Approver, Auditor, Admin.
  * 3 Kịch bản vĩ mô: Baseline, Adverse, Severely Adverse.
  * Hệ số độ nhạy vĩ mô ($\beta$) và khuếch đại PD cho **5 ngành kinh tế trọng yếu**: BĐS và Xây dựng, Sản xuất và Chế biến, Nông - Lâm - Thủy sản, Thương mại, Bán lẻ.
  * 100 Khách hàng (`customers`), 100 Khoản vay (`loan_accounts`), 100 Tài sản bảo đảm (`collaterals`) và 100 Phân bổ TSBĐ (`loan_collateral`).
* `docker-compose.yml`: Cấu hình Docker để khởi chạy PostgreSQL 16 và pgAdmin 4 chỉ với một câu lệnh.
* `generate_seed.py`: Script Python sinh ngẫu nhiên có kiểm soát 100 hồ sơ khách hàng & khoản vay mẫu chuẩn hóa cho CSDL.

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

## 3. Danh mục 11 Bảng Dữ liệu Chuẩn hóa (Khớp Bảng 22 Báo cáo)

1. `system_users`: Quản lý tài khoản, băm mật khẩu PBKDF2 và phân quyền người dùng RBAC (Maker, Checker, Approver, Auditor, Admin).
2. `sector_sensitivity`: Hệ số nhạy cảm vĩ mô và khuếch đại PD cho 5 nhóm ngành kinh tế trọng yếu.
3. `customers`: Thông tin khách hàng vay vốn và liên kết ngành nghề (`sector_code REFERENCES sector_sensitivity`).
4. `loan_accounts`: Danh mục khoản vay tại ngày chốt số liệu (EAD, lãi suất, kỳ hạn, nhóm nợ TT 11, Stage IFRS 9, PD0, LGD cơ sở).
5. `collaterals`: Danh mục tài sản bảo đảm định giá và tỷ lệ chi phí thanh lý (haircut).
6. `loan_collateral`: Bảng liên kết quan hệ N-N giữa khoản vay và tài sản bảo đảm kèm giá trị phân bổ.
7. `macro_scenarios`: Danh mục kịch bản kiểm định vĩ mô (Cơ sở, Căng thẳng vừa, Khủng hoảng).
8. `stress_test_runs`: Phiên kiểm định, tham số sốc vĩ mô và vòng đời phê duyệt Maker - Checker - Approver.
9. `stress_results`: Kết quả chi tiết tính toán tổn thất dự kiến IFRS 9 ($PD_{\text{sốc}}$, $LGD_{\text{sốc}}$, Stage mới, cờ SICR, ECL, $\Delta PS$).
10. `car_impacts`: Đánh giá tác động trích lập bổ sung lên Vốn cấp 1, RWA và tỷ lệ an toàn vốn CAR (Basel II).
11. `audit_logs`: Nhật ký kiểm toán bất biến (Append-only) ghi nhận mọi hành vi phê duyệt và chuyển trạng thái.
