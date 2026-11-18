from django.db import models
from django.utils import timezone


class SystemUser(models.Model):
    """
    Bảng 39 Báo cáo: Đăng nhập tập trung (SSO), RBAC, phân quyền Maker - Checker - Approver - Auditor
    """
    ROLES = [
        ('MAKER', 'Chuyên viên Quản lý Rủi ro (Maker)'),
        ('CHECKER', 'Trưởng phòng Quản lý Rủi ro (Checker)'),
        ('APPROVER', 'Giám đốc Rủi ro / Ban Điều hành (Approver)'),
        ('AUDITOR', 'Kiểm toán nội bộ (Auditor)'),
        ('ADMIN', 'Quản trị viên Hệ thống (System Admin)'),
    ]

    username = models.CharField(max_length=50, unique=True, verbose_name="Tên đăng nhập")
    full_name = models.CharField(max_length=100, verbose_name="Họ và tên")
    email = models.EmailField(max_length=100, unique=True, verbose_name="Email")
    role = models.CharField(max_length=30, choices=ROLES, verbose_name="Vai trò")
    department = models.CharField(max_length=100, default='Khối Quản lý Rủi ro', verbose_name="Phòng ban")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tạo")

    class Meta:
        db_table = 'SYSTEM_USERS'
        verbose_name = 'Người dùng hệ thống'
        verbose_name_plural = '09. Phân quyền Người dùng'

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


class Customer(models.Model):
    """
    Bảng 24 / Bảng 31 Báo cáo: Thông tin khách hàng vay (CUSTOMERS)
    """
    customer_id = models.CharField(max_length=20, primary_key=True, verbose_name="Mã khách hàng")
    customer_name = models.CharField(max_length=150, verbose_name="Tên khách hàng")
    segment = models.CharField(max_length=30, verbose_name="Phân khúc")  # 'Doanh nghiệp', 'Bán lẻ'
    sector_code = models.CharField(max_length=50, verbose_name="Ngành kinh tế")  # BDS_XD, SX_CB, NLTS, TM, BL
    internal_rating = models.CharField(max_length=10, blank=True, null=True, verbose_name="Hạng tín dụng nội bộ")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tạo")

    class Meta:
        db_table = 'CUSTOMERS'
        verbose_name = 'Khách hàng'
        verbose_name_plural = '01. Danh mục Khách hàng'

    def __str__(self):
        return f"{self.customer_id} - {self.customer_name} ({self.sector_code})"


class LoanAccount(models.Model):
    """
    Bảng 25 / Bảng 32 Báo cáo: Hợp đồng vay tại ngày chốt số liệu (LOAN_ACCOUNTS)
    """
    loan_id = models.CharField(max_length=30, primary_key=True, verbose_name="Mã hợp đồng vay")
    customer = models.ForeignKey(Customer, to_field='customer_id', db_column='customer_id', on_delete=models.CASCADE, related_name='loans', verbose_name="Khách hàng")
    snapshot_date = models.DateField(default=timezone.now, verbose_name="Ngày chốt số liệu")
    ead = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Dư nợ gốc hiện tại (EAD)")
    undrawn_limit = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Hạn mức chưa rút")
    interest_rate = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Lãi suất vay (EIR)")
    remaining_term = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Kỳ hạn còn lại (năm)")
    days_past_due = models.IntegerField(default=0, verbose_name="Số ngày quá hạn")
    debt_group = models.SmallIntegerField(default=1, verbose_name="Nhóm nợ theo TT 11 (1 đến 5)")
    current_stage = models.SmallIntegerField(default=1, verbose_name="Stage hiện tại theo IFRS 9 (1, 2, 3)")
    pd_base = models.DecimalField(max_digits=8, decimal_places=6, verbose_name="Xác suất vỡ nợ cơ sở (PD0)")
    baseline_lgd = models.DecimalField(max_digits=6, decimal_places=5, default=0.45000, verbose_name="Tỷ lệ tổn thất cơ sở (LGD0)")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tạo")

    class Meta:
        db_table = 'LOAN_ACCOUNTS'
        verbose_name = 'Hợp đồng / Khoản vay'
        verbose_name_plural = '02. Danh mục Khoản vay'

    def __str__(self):
        return f"{self.loan_id} - Dư nợ: {self.ead:,.0f} VNĐ (Stage {self.current_stage})"


class Collateral(models.Model):
    """
    Bảng 26 / Bảng 33 Báo cáo: Tài sản bảo đảm (COLLATERALS)
    """
    collateral_id = models.CharField(max_length=30, primary_key=True, verbose_name="Mã tài sản bảo đảm")
    collateral_type = models.CharField(max_length=100, verbose_name="Loại tài sản bảo đảm")
    appraised_value = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Giá trị định giá")
    appraisal_date = models.DateField(null=True, blank=True, verbose_name="Ngày định giá")
    liquidation_cost_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.1000, verbose_name="Tỷ lệ chi phí xử lý, thanh lý (Haircut)")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tạo")

    class Meta:
        db_table = 'COLLATERALS'
        verbose_name = 'Tài sản bảo đảm'
        verbose_name_plural = '03. Tài sản bảo đảm'

    def __str__(self):
        return f"{self.collateral_id} - {self.collateral_type} ({self.appraised_value:,.0f} VNĐ)"


class LoanCollateral(models.Model):
    """
    Bảng 27 / Bảng 34 Báo cáo: Bảng trung gian liên kết Khoản vay và TSBĐ (LOAN_COLLATERAL)
    """
    loan = models.ForeignKey(LoanAccount, to_field='loan_id', db_column='loan_id', on_delete=models.CASCADE, related_name='collateral_links', verbose_name="Khoản vay")
    collateral = models.ForeignKey(Collateral, to_field='collateral_id', db_column='collateral_id', on_delete=models.CASCADE, related_name='loan_links', verbose_name="Tài sản bảo đảm")
    allocated_value = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Phần giá trị phân bổ cho khoản vay")

    class Meta:
        db_table = 'LOAN_COLLATERAL'
        unique_together = ('loan', 'collateral')
        verbose_name = 'Liên kết Khoản vay - TSBĐ'
        verbose_name_plural = '04. Liên kết Khoản vay - TSBĐ'

    def __str__(self):
        return f"{self.loan_id} <-> {self.collateral_id}: {self.allocated_value:,.0f} VNĐ"


class MacroScenario(models.Model):
    """
    Bảng 28 / Bảng 35 Báo cáo: Kịch bản kinh tế vĩ mô (MACRO_SCENARIOS)
    """
    SCENARIO_TYPES = [
        ('Baseline', 'Kịch bản Cơ sở (Baseline)'),
        ('Adverse', 'Kịch bản Căng thẳng Vừa (Adverse)'),
        ('Severe', 'Kịch bản Căng thẳng Trọng yếu (Severe)'),
    ]

    scenario_code = models.CharField(max_length=30, unique=True, verbose_name="Mã kịch bản")
    scenario_name = models.CharField(max_length=100, verbose_name="Tên kịch bản")
    scenario_type = models.CharField(max_length=20, choices=SCENARIO_TYPES, default='Adverse', verbose_name="Phân loại kịch bản")
    description = models.TextField(blank=True, verbose_name="Mô tả bối cảnh kinh tế")
    gdp_growth_shock = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Cú sốc tăng trưởng GDP (%)")
    interest_rate_shock = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Cú sốc lãi suất cho vay (%)")
    unemployment_shock = models.DecimalField(max_digits=6, decimal_places=4, default=0.0000, verbose_name="Cú sốc tỷ lệ thất nghiệp (%)")
    real_estate_price_shock = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Biến động chỉ số BĐS (%)")
    fx_rate_shock = models.DecimalField(max_digits=6, decimal_places=4, default=0.0000, verbose_name="Cú sốc tỷ giá (%)")
    recovery_time_years = models.DecimalField(max_digits=4, decimal_places=2, default=2.00, verbose_name="Thời gian thu hồi TSBĐ (năm)")
    scenario_weight = models.DecimalField(max_digits=4, decimal_places=3, default=0.333, verbose_name="Trọng số kịch bản w")
    version = models.IntegerField(default=1, verbose_name="Số phiên bản")
    status = models.CharField(max_length=20, default='Active', verbose_name="Trạng thái kịch bản")
    created_by = models.CharField(max_length=50, default='Khối Quản lý Rủi ro', verbose_name="Người tạo")
    is_active = models.BooleanField(default=True, verbose_name="Kích hoạt")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tạo")

    class Meta:
        db_table = 'MACRO_SCENARIOS'
        verbose_name = 'Kịch bản Vĩ mô'
        verbose_name_plural = '05. Kịch bản Vĩ mô'

    def __str__(self):
        return f"{self.scenario_name} [{self.scenario_type}]"


class IndustrySensitivity(models.Model):
    """
    Bảng 29 / Bảng 36 Báo cáo: Hệ số độ nhạy cảm theo ngành (SECTOR_SENSITIVITY)
    """
    sector_code = models.CharField(max_length=50, primary_key=True, verbose_name="Mã ngành kinh tế")
    sector_name_vn = models.CharField(max_length=100, verbose_name="Tên ngành kinh tế (VN)")
    beta_gdp = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Hệ số nhạy cảm GDP (Beta GDP)")
    beta_interest = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Hệ số nhạy cảm Lãi suất (Beta IR)")
    beta_real_estate = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Hệ số nhạy cảm BĐS (Beta RE)")
    pd_multiplier = models.DecimalField(max_digits=6, decimal_places=3, default=1.000, verbose_name="Hệ số khuếch đại PD")

    class Meta:
        db_table = 'SECTOR_SENSITIVITY'
        verbose_name = 'Độ nhạy cảm Ngành'
        verbose_name_plural = '06. Hệ số Nhạy cảm Ngành'

    def __str__(self):
        return f"{self.sector_name_vn} ({self.sector_code})"


# Backward/Alias compatibility for IndustrySensitivity
SectorSensitivity = IndustrySensitivity


class StressTestRun(models.Model):
    """
    Bảng 30 / Bảng 37 Báo cáo: Báo cáo tổng hợp kiểm định (ECL_REPORTS)
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Bản thảo'),
        ('SUBMITTED', 'Chờ thẩm định'),
        ('PENDING_APPROVAL', 'Chờ phê duyệt'),
        ('RECALCULATION_REQUESTED', 'Yêu cầu tính lại'),
        ('APPROVED', 'Đã phê duyệt'),
        ('REJECTED', 'Đã từ chối'),
    ]

    run_code = models.CharField(max_length=50, unique=True, verbose_name="Mã báo cáo / Phiên kiểm định")
    run_name = models.CharField(max_length=150, verbose_name="Tên phiên kiểm định")
    scenario = models.ForeignKey(MacroScenario, on_delete=models.CASCADE, related_name='runs', verbose_name="Kịch bản vĩ mô")
    custom_gdp_shock = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True, verbose_name="Cú sốc GDP tùy chỉnh")
    custom_ir_shock = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True, verbose_name="Cú sốc Lãi suất tùy chỉnh")
    custom_unemp_shock = models.DecimalField(max_digits=6, decimal_places=4, default=0.0000, null=True, blank=True, verbose_name="Cú sốc Thất nghiệp tùy chỉnh")
    custom_re_shock = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True, verbose_name="Cú sốc BĐS tùy chỉnh")
    snapshot_date = models.DateField(default=timezone.localdate, verbose_name="Ngày chốt dữ liệu")
    maker = models.ForeignKey(SystemUser, on_delete=models.CASCADE, related_name='runs_created', verbose_name="Chuyên viên lập (Maker)")
    checker = models.ForeignKey(SystemUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='runs_checked', verbose_name="Kiểm soát viên (Checker)")
    approver = models.ForeignKey(SystemUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='runs_approved', verbose_name="Cấp phê duyệt (Approver)")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT', verbose_name="Trạng thái phê duyệt")
    
    total_ead = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng EAD chịu rủi ro (VNĐ)")
    total_baseline_ecl = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng ECL cơ sở (VNĐ)")
    total_stressed_ecl = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Tổng ECL sau kiểm định (VNĐ)")
    total_delta_provision = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Dự phòng phát sinh tăng (ΔPS)")
    npl_stress = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True, verbose_name="Tỷ lệ nợ xấu sau sốc (NPL)")
    llr_stress = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, verbose_name="Tỷ lệ bao phủ nợ xấu sau sốc (LLR)")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="Ý kiến nhận xét / Phản hồi")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm phê duyệt")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Thời điểm cập nhật")

    class Meta:
        db_table = 'ECL_REPORTS'
        verbose_name = 'Báo cáo Kiểm định'
        verbose_name_plural = '07. Báo cáo Tổng hợp Kiểm định'

    def __str__(self):
        return f"{self.run_code}: {self.run_name} [{self.get_status_display()}]"


# Backward/Alias compatibility for StressTestRun
ECLReport = StressTestRun


class LoanContract(models.Model):
    """
    Bản ghi hợp đồng tổng hợp phục vụ hiển thị nhanh và tương thích ngược (LOAN_CONTRACTS)
    """
    SEGMENTS = [
        ('CORPORATE', 'Corporate'),
        ('SME', 'SME'),
        ('RETAIL', 'Retail'),
    ]

    SECTORS = [
        ('REAL_ESTATE', 'Bất động sản'),
        ('CONSTRUCTION', 'Xây dựng và Hạ tầng'),
        ('MANUFACTURING', 'Sản xuất và Chế biến'),
        ('WHOLESALE_RETAIL', 'Bán buôn và Bán lẻ'),
        ('AGRICULTURE', 'Nông - Lâm - Thủy sản'),
        ('CONSUMER_LOAN', 'Cho vay tiêu dùng và Bán lẻ'),
    ]

    contract_id = models.CharField(max_length=30, primary_key=True, verbose_name="Mã hợp đồng")
    customer_id = models.CharField(max_length=30, verbose_name="Mã khách hàng")
    customer_name = models.CharField(max_length=150, verbose_name="Tên khách hàng")
    customer_segment = models.CharField(max_length=30, choices=SEGMENTS, verbose_name="Phân khúc")
    industry_sector = models.CharField(max_length=50, choices=SECTORS, verbose_name="Ngành kinh tế")
    original_ead = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Dư nợ gốc (VNĐ)")
    interest_rate = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Lãi suất (EIR)")
    remaining_tenor_months = models.IntegerField(verbose_name="Kỳ hạn còn lại (tháng)")
    collateral_type = models.CharField(max_length=100, verbose_name="Loại TSBĐ")
    collateral_value = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Giá trị TSBĐ (VNĐ)")
    baseline_haircut = models.DecimalField(max_digits=5, decimal_places=4, default=0.3000, verbose_name="Tỷ lệ Haircut")
    internal_rating = models.CharField(max_length=10, verbose_name="Hạng tín dụng")
    baseline_pd = models.DecimalField(max_digits=6, decimal_places=5, verbose_name="PD cơ sở")
    baseline_lgd = models.DecimalField(max_digits=6, decimal_places=5, verbose_name="LGD cơ sở")
    initial_stage = models.IntegerField(default=1, verbose_name="Stage ban đầu")
    overdue_days = models.IntegerField(default=0, verbose_name="Số ngày quá hạn")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tạo")

    class Meta:
        db_table = 'LOAN_CONTRACTS'
        verbose_name = 'Hợp đồng Tín dụng (Hợp nhất)'
        verbose_name_plural = '12. Hợp đồng Tín dụng Tổng hợp'

    def __str__(self):
        return f"{self.contract_id} - {self.customer_name} ({self.industry_sector})"


class ECLResult(models.Model):
    """
    Bảng 31 / Bảng 38 Báo cáo: Kết quả kiểm định chi tiết từng khoản vay (STRESS_RESULTS)
    """
    run = models.ForeignKey(StressTestRun, on_delete=models.CASCADE, related_name='ecl_results', verbose_name="Báo cáo kiểm định")
    contract = models.ForeignKey(LoanContract, on_delete=models.CASCADE, related_name='ecl_evaluations', null=True, blank=True, verbose_name="Hợp đồng")
    loan_account = models.ForeignKey(LoanAccount, to_field='loan_id', db_column='loan_account_id', on_delete=models.SET_NULL, null=True, blank=True, related_name='stress_evaluations', verbose_name="Khoản vay LOAN_ACCOUNTS")
    baseline_pd = models.DecimalField(max_digits=8, decimal_places=6, verbose_name="PD 12 tháng cơ sở")
    stressed_pd = models.DecimalField(max_digits=8, decimal_places=6, verbose_name="PD 12 tháng sau sốc")
    baseline_lgd = models.DecimalField(max_digits=6, decimal_places=5, verbose_name="LGD cơ sở")
    stressed_lgd = models.DecimalField(max_digits=6, decimal_places=5, verbose_name="LGD sau sốc")
    baseline_stage = models.IntegerField(verbose_name="Stage cơ sở")
    stressed_stage = models.IntegerField(verbose_name="Stage sau sốc")
    discount_factor = models.DecimalField(max_digits=8, decimal_places=6, default=0.913240, verbose_name="Hệ số chiết khấu DF")
    is_sicr = models.BooleanField(default=False, verbose_name="Dấu hiệu SICR")
    early_warning_flag = models.BooleanField(default=False, verbose_name="Cờ cảnh báo sớm Early Warning")
    baseline_ecl = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="ECL cơ sở")
    stressed_ecl = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="ECL sau sốc")
    delta_provision = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="Dự phòng phát sinh tăng (ΔPS)")
    calculation_timestamp = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tính toán")

    class Meta:
        db_table = 'STRESS_RESULTS'
        verbose_name = 'Kết quả Kiểm định Chi tiết'
        verbose_name_plural = '08. Kết quả Kiểm định Chi tiết'

    def __str__(self):
        return f"{self.run.run_code} - HĐ {self.contract_id or (self.loan_account.loan_id if self.loan_account else 'N/A')}"


# Backward/Alias compatibility for ECLResult
StressResult = ECLResult


class CarImpact(models.Model):
    """
    Tác động Tỷ lệ An toàn Vốn (CAR_IMPACTS)
    """
    run = models.OneToOneField(StressTestRun, on_delete=models.CASCADE, related_name='car_impact', verbose_name="Phiên kiểm định")
    baseline_tier1_capital = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Vốn cấp 1 cơ sở")
    baseline_tier2_capital = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Vốn cấp 2 cơ sở")
    baseline_rwa = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Tổng RWA cơ sở")
    baseline_car = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Hệ số CAR cơ sở")
    total_delta_provision = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Tổng trích lập bổ sung")
    stressed_tier1_capital = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Vốn cấp 1 sau sốc")
    stressed_rwa = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Tổng RWA sau sốc")
    stressed_car = models.DecimalField(max_digits=6, decimal_places=4, verbose_name="Hệ số CAR sau sốc")
    car_change_bps = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Biến động CAR (bps)")
    minimum_regulatory_car = models.DecimalField(max_digits=6, decimal_places=4, default=0.0800, verbose_name="Ngưỡng CAR tối thiểu (8%)")
    is_capital_adequate = models.BooleanField(default=True, verbose_name="Đảm bảo tỷ lệ an toàn vốn")
    calculated_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tính toán")

    class Meta:
        db_table = 'CAR_IMPACTS'
        verbose_name = 'Tác động Tỷ lệ Vốn CAR'
        verbose_name_plural = '11. Tác động Tỷ lệ Vốn CAR'

    def __str__(self):
        return f"CAR Run {self.run.run_code}: {float(self.stressed_car)*100:.2f}%"


class AuditLog(models.Model):
    """
    Nhật ký hoạt động và kiểm toán (AUDIT_LOGS)
    """
    run = models.ForeignKey(StressTestRun, on_delete=models.CASCADE, related_name='audit_logs', verbose_name="Phiên kiểm định")
    actor = models.ForeignKey(SystemUser, on_delete=models.CASCADE, verbose_name="Người thực hiện")
    action = models.CharField(max_length=50, verbose_name="Hành động")
    action_note = models.TextField(blank=True, verbose_name="Ghi chú chi tiết")
    ip_address = models.CharField(max_length=45, blank=True, null=True, verbose_name="Địa chỉ IP")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm ghi nhận")

    class Meta:
        db_table = 'AUDIT_LOGS'
        verbose_name = 'Nhật ký Hoạt động'
        verbose_name_plural = '10. Nhật ký Hoạt động'

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {self.actor.full_name}: {self.action}"

