# Credit Risk Stress Testing & ECL Provisioning System (IFRS 9 & Basel II)

Hệ thống Kiểm định Sức chịu tải Rủi ro Tín dụng và Phân bổ Trích lập Dự phòng theo Chuẩn mực IFRS 9 và Khung An toàn Vốn (Thông tư 14/2025/TT-NHNN).

---

## 📌 Tổng quan Hệ thống

Dự án cung cấp giải pháp toàn diện cho nghiệp vụ Quản trị Rủi ro Tín dụng tại Ngân hàng Thương mại:
1. **Mô phỏng Kịch bản Vĩ mô Đa chiều**: Cho phép điều chỉnh 4 cú sốc vĩ mô (Tăng trưởng GDP, Lãi suất điều hành, Tỷ lệ Thất nghiệp, Chỉ số Bất động sản) theo các kịch bản Cơ sở (Baseline), Căng thẳng Vừa (Adverse) và Khủng hoảng Sâu (Severe).
2. **Đo lường Tổn thất Tín dụng Dự kiến (ECL)**:
   - Mô hình nhạy cảm ngành kinh tế liên kết kinh tế vĩ mô thông qua hàm Logit PD.
   - Định giá lại tài sản bảo đảm và tỷ lệ mất vốn khi vỡ nợ (Stressed LGD).
   - Tự động nhận diện dấu hiệu rủi ro tín dụng gia tăng đáng kể (SICR) và dịch chuyển nhóm nợ giữa Stage 1, Stage 2 và Stage 3.
3. **Đánh giá Tác động An toàn Vốn (CAR)**: Tính toán thâm hụt Vốn Cấp 1, biến động tổng tài sản rủi ro (RWA) và tỷ lệ an toàn vốn CAR so với ngưỡng an toàn tối thiểu 8,00%.
4. **Quy trình Phê duyệt Kiểm soát Kép (Four-Eyes Principle)**:
   - **Maker (Chuyên viên Rủi ro)**: Xây dựng kịch bản, tính toán số liệu và nộp đề án.
   - **Checker (Trưởng phòng Rủi ro)**: Thẩm định 3 tiêu chuẩn nghiệp vụ, chuyển duyệt hoặc yêu cầu tính lại.
   - **Approver (Giám đốc Rủi ro / CRO)**: Phê duyệt đề án và ban hành 3 quyết định điều hành chiến lược.
   - **Auditor (Kiểm toán Nội bộ)**: Rà soát vết nhật ký hoạt động (Audit Trail).
5. **Giám sát Danh mục Cảnh báo Sớm (Early Warning Portfolio)**: Bộ lọc và phân tích chi tiết từng hợp đồng có nguy cơ vỡ nợ cao.

---

## 🛠 Kiến trúc Công nghệ

* **Backend**: Python 3.10+, Django 5.x, Django REST Framework
* **Frontend**: Angular 19, Tailwind CSS v4, FontAwesome
* **Database**: PostgreSQL (Dockerized) / SQLite3
* **Kiến trúc Tích hợp**: Single-Origin Architecture (Django tích hợp và phục vụ trực tiếp bản dựng Angular bundle).

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

### 1. Khởi động Backend (Django API)

```bash
# Điều hướng vào thư mục backend
cd backend

# Cài đặt thư viện phụ thuộc
pip install django djangorestframework django-cors-headers

# Thực hiện di trú cơ sở dữ liệu (nếu cần)
python manage.py migrate

# Khởi chạy máy chủ API
python manage.py runserver 127.0.0.1:8000
```

Hệ thống sẵn sàng tại: `http://127.0.0.1:8000/`  
Giao diện Quản trị CSDL (Django Admin): `http://127.0.0.1:8000/admin/`

### 2. Phát triển Frontend (Angular)

```bash
# Điều hướng vào thư mục frontend
cd frontend

# Cài đặt node_modules
npm install

# Biên dịch ứng dụng sang bundle phục vụ bởi backend
npm run build

# Hoặc khởi chạy máy chủ phát triển riêng (Hot Reload)
npm start
```

---

## 👥 Tài khoản Thử nghiệm Phân quyền

Hệ thống hỗ trợ cơ chế Đăng nhập nhanh (Quick Sign-in) cho 5 vai trò:
* **Maker**: `maker_an` (Mật khẩu: `123456`) - Nguyễn Văn An (Chuyên viên Phân tích rủi ro)
* **Checker**: `checker_binh` (Mật khẩu: `123456`) - Trần Thị Bình (Trưởng phòng Quản lý rủi ro)
* **Approver**: `approver_cuong` (Mật khẩu: `123456`) - Lê Hoàng Cường (Giám đốc Khối Quản trị Rủi ro)
* **Auditor**: `auditor_dung` (Mật khẩu: `123456`) - Phạm Minh Dũng (Kiểm toán viên nội bộ)
* **Admin**: `admin_system` (Mật khẩu: `123456`) - Quản trị viên Hệ thống
