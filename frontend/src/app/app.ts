import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

export interface SystemUser {
  id: number;
  username: string;
  full_name: string;
  email: string;
  role: 'MAKER' | 'CHECKER' | 'APPROVER' | 'AUDITOR' | 'ADMIN';
  department: string;
}

export interface MacroScenario {
  id: number;
  scenario_code: string;
  scenario_name: string;
  description: string;
  gdp_growth_shock: number;
  interest_rate_shock: number;
  real_estate_price_shock: number;
}

export interface LoanContract {
  contract_id: string;
  customer_id: string;
  customer_name: string;
  customer_segment: string;
  industry_sector: string;
  original_ead: number;
  interest_rate: number;
  remaining_tenor_months: number;
  collateral_type: string;
  collateral_value: number;
  baseline_haircut: number;
  internal_rating: string;
  baseline_pd: number;
  baseline_lgd: number;
  initial_stage: number;
  overdue_days: number;
}

export interface ContractResult {
  contract_id: string;
  customer_name: string;
  customer_segment: string;
  industry_sector: string;
  sector_name_vn: string;
  original_ead: number;
  collateral_type?: string;
  collateral_value?: number;
  internal_rating?: string;
  baseline_pd: number;
  stressed_pd: number;
  baseline_lgd: number;
  stressed_lgd: number;
  baseline_stage: number;
  stressed_stage: number;
  is_sicr: boolean;
  baseline_ecl: number;
  stressed_ecl: number;
  delta_provision: number;
}

export interface SectorBreakdown {
  sector_code: string;
  sector_name: string;
  ead: number;
  baseline_ecl: number;
  stressed_ecl: number;
  delta_provision: number;
  contract_count: number;
}

export interface SimulationResponse {
  contract_results: ContractResult[];
  summary: {
    total_ead: number;
    total_baseline_ecl: number;
    total_stressed_ecl: number;
    total_delta_provision: number;
    baseline_car: number;
    stressed_car: number;
    car_change_bps: number;
    minimum_regulatory_car: number;
    is_capital_adequate: boolean;
    baseline_tier1: number;
    stressed_tier1: number;
    baseline_rwa: number;
    stressed_rwa: number;
    npl_ratio_pre: number;
    npl_ratio_post: number;
  };
  stage_migration: {
    pre_stress: { [key: number]: number };
    post_stress: { [key: number]: number };
    migrated_to_stage2: number;
    migrated_to_stage3: number;
  };
  sector_breakdown: SectorBreakdown[];
}

export interface AuditLogItem {
  id: number;
  run: number;
  run_code?: string;
  run_name?: string;
  actor: number;
  actor_name: string;
  actor_role: string;
  action: string;
  action_note: string;
  created_at: string;
}

export interface StressTestRun {
  id: number;
  run_code: string;
  run_name: string;
  status: string;
  scenario_name: string;
  maker_name: string;
  checker_name?: string;
  approver_name?: string;
  total_ead: number;
  total_baseline_ecl: number;
  total_stressed_ecl: number;
  total_delta_provision: number;
  custom_gdp_shock: number;
  custom_ir_shock: number;
  custom_unemp_shock?: number;
  custom_re_shock: number;
  npl_stress?: number;
  rejection_reason?: string;
  created_at: string;
  car_impact?: {
    baseline_car: number;
    stressed_car: number;
    is_capital_adequate: boolean;
  };
  audit_logs?: AuditLogItem[];
}

export const TRANSLATIONS: { [lang: string]: { [key: string]: string } } = {
  vi: {
    system_title: 'KIỂM ĐỊNH TÍN DỤNG IFRS 9',
    system_subtitle: 'Phân hệ Đo lường Rủi ro Tín dụng và Phân bổ Trích lập Dự phòng',
    db_status: 'Cơ sở Dữ liệu: PostgreSQL',
    tab_maker: 'Mô Phỏng Kịch Bản',
    tab_checker: 'Thẩm Định Rủi Ro',
    tab_approver: 'Phê Duyệt Điều Hành',
    tab_portfolio: 'Cảnh Báo Sớm và Danh Mục',
    tab_audit: 'Nhật Ký Hoạt Động',
    login_title: 'Đăng nhập Hệ thống',
    login_subtitle: 'Cổng Quản trị Rủi ro Tín dụng IFRS 9',
    login_prompt: 'Đăng nhập vào tài khoản của bạn:',
    lbl_username: 'Tên đăng nhập',
    lbl_password: 'Mật khẩu',
    placeholder_username: 'Nhập tên đăng nhập (ví dụ: maker_an)...',
    placeholder_password: 'Nhập mật khẩu...',
    quick_login_title: 'Đăng nhập nhanh theo chức danh:',
    quick_login_hint: 'Chọn vai trò:',
    btn_login: 'Đăng nhập',
    btn_logout: 'Đăng xuất',
    role_maker: 'Chuyên viên Phân tích rủi ro',
    role_checker: 'Trưởng phòng Quản lý rủi ro',
    role_approver: 'Giám đốc Khối Quản lý rủi ro',
    role_auditor: 'Kiểm toán viên nội bộ',
    role_admin: 'Quản trị viên Hệ thống',
    user_role: 'Chức danh',
    user_dept: 'Đơn vị',
    scenario_settings: 'Tham số Cú sốc Vĩ mô',
    preset_baseline: 'Kịch bản Cơ sở',
    preset_adverse: 'Căng thẳng Vừa',
    preset_severe: 'Khủng hoảng Sâu',
    shock_gdp: 'Tăng trưởng GDP',
    shock_ir: 'Lãi suất điều hành',
    shock_unemp: 'Tỷ lệ Thất nghiệp',
    shock_re: 'Chỉ số Bất động sản',
    kpi_ead: 'Tổng Dư nợ Danh mục',
    kpi_ead_sym: '',
    kpi_ecl_stress: 'Tổn thất Dự kiến',
    kpi_ecl_sym: '',
    kpi_ecl_base: 'Mức cơ sở',
    kpi_delta_ps: 'Trích lập Bổ sung',
    kpi_delta_ps_sym: '',
    kpi_car: 'Hệ số An toàn Vốn',
    kpi_car_stress: 'Hệ số An toàn Vốn',
    kpi_car_sym: '',
    kpi_car_base: 'Tỷ lệ ban đầu',
    kpi_npl: 'Tỷ lệ Nợ xấu',
    kpi_npl_sym: '',
    btn_recalculate: 'Tính toán Lại',
    btn_submit_checker: 'Lưu và Chuyển Thẩm định',
    sec_breakdown_title: 'Phân bổ Tổn thất theo Ngành Kinh tế',
    stage_migration_title: 'Ma Trận Dịch Chuyển Nhóm Nợ',
    stage_1: 'Nhóm 1 - Nợ tiêu chuẩn',
    stage_2: 'Nhóm 2 - Rủi ro gia tăng',
    stage_3: 'Nhóm 3 - Nợ xấu',
    stage_1_desc: 'Trích lập dự phòng 12 tháng',
    stage_2_desc: 'Trích lập dự phòng trọn đời',
    stage_3_desc: 'Nợ suy giảm và mất vốn',
    checker_queue_title: 'Danh sách Phiên Kiểm định Chờ Thẩm định',
    col_run_code: 'Mã Phiên',
    col_run_name: 'Tên Phiên',
    col_maker: 'Người lập',
    col_scenario: 'Kịch bản',
    col_delta_ps: 'Trích lập Bổ sung',
    col_status: 'Trạng thái',
    col_actions: 'Thao tác',
    btn_forward_approver: 'Xác nhận và Chuyển Phê duyệt',
    btn_request_recalc: 'Yêu cầu Tính lại',
    approver_title: 'Báo Cáo Phê Duyệt Điều Hành',
    approver_subtitle: '',
    decision_1_title: '1. Cắt giảm hạn mức tín dụng Bất động sản và Xây dựng',
    decision_1_desc: 'Ngành BĐS chiếm phần lớn tổn thất. Cắt giảm hạn mức cấp mới để chuyển dịch vốn sang sản xuất kinh doanh.',
    decision_2_title: '2. Phân bổ chi phí trích lập dự phòng bổ sung qua 4 quý',
    decision_2_desc: 'Lên kế hoạch trích lập đều đặn theo từng quý, đảm bảo chỉ tiêu an toàn vốn và ổn định lợi nhuận.',
    decision_3_title: '3. Kích hoạt quy trình xử lý nợ sớm',
    decision_3_desc: 'Chuyển danh sách các hợp đồng có dấu hiệu suy giảm khả năng trả nợ sang Khối Xử lý nợ để định giá lại tài sản bảo đảm.',
    btn_sign_approve: 'Ký số Phê duyệt Kịch bản',
    search_placeholder: 'Tìm kiếm tên khách hàng, mã hợp đồng...',
    filter_all_sectors: 'Tất cả ngành nghề',
    filter_all_stages: 'Tất cả nhóm nợ',
    btn_export_csv: 'Xuất Bảng Tính Excel',
    col_contract_id: 'Mã Hợp đồng',
    col_customer: 'Khách hàng',
    col_sector: 'Ngành nghề',
    col_ead: 'Dư nợ',
    col_interest: 'Lãi suất',
    col_rating: 'Hạng tín nhiệm',
    col_collateral: 'Tài sản bảo đảm',
    col_stage: 'Nhóm nợ',
    notice_no_permission: 'Tài khoản của bạn không có quyền truy cập phân hệ này.',
    btn_methodology_detail: 'Chi tiết Cách tính',
    modal_methodology_title: 'Quy Trình và Công Thức Tính Toán Định Lượng'
  },
  en: {
    system_title: 'IFRS 9 CREDIT STRESS TESTING',
    system_subtitle: 'Credit Risk Stress Testing and Expected Credit Loss Provision Allocation',
    db_status: 'Database: PostgreSQL',
    tab_maker: 'Scenario Simulation',
    tab_checker: 'Risk Validation',
    tab_approver: 'Executive Approval',
    tab_portfolio: 'Early Warning Portfolio',
    tab_audit: 'Audit Trail',
    login_title: 'System Sign In',
    login_subtitle: 'IFRS 9 Credit Risk Governance Portal',
    login_prompt: 'Sign in to your account:',
    lbl_username: 'Username',
    lbl_password: 'Password',
    placeholder_username: 'Enter username (e.g. maker_an)...',
    placeholder_password: 'Enter password...',
    quick_login_title: 'Quick Sign In by Job Role:',
    quick_login_hint: 'Select role:',
    btn_login: 'Sign In',
    btn_logout: 'Logout',
    role_maker: 'Credit Risk Analyst',
    role_checker: 'Risk Management Head',
    role_approver: 'Chief Risk Officer',
    role_auditor: 'Internal Auditor',
    role_admin: 'System Administrator',
    user_role: 'Job Role',
    user_dept: 'Department',
    scenario_settings: 'Macroeconomic Shock Parameters',
    preset_baseline: 'Baseline Scenario',
    preset_adverse: 'Adverse Scenario',
    preset_severe: 'Severe Scenario',
    shock_gdp: 'GDP Growth Shock',
    shock_ir: 'Policy Interest Rate Shock',
    shock_unemp: 'Unemployment Rate Shock',
    shock_re: 'Real Estate Price Shock',
    kpi_ead: 'Total Exposure',
    kpi_ead_sym: '',
    kpi_ecl_stress: 'Stressed Expected Loss',
    kpi_ecl_sym: '',
    kpi_ecl_base: 'Baseline ECL',
    kpi_delta_ps: 'Additional Provision',
    kpi_delta_ps_sym: '',
    kpi_car: 'Capital Adequacy Ratio',
    kpi_car_stress: 'Capital Adequacy Ratio',
    kpi_car_sym: '',
    kpi_car_base: 'Baseline CAR',
    kpi_npl: 'Non-Performing Loan Ratio',
    kpi_npl_sym: '',
    btn_recalculate: 'Recalculate',
    btn_submit_checker: 'Save and Submit for Review',
    sec_breakdown_title: 'Expected Loss Breakdown by Economic Sector',
    stage_migration_title: 'Stage Migration Matrix',
    stage_1: 'Stage 1 - Performing',
    stage_2: 'Stage 2 - Underperforming',
    stage_3: 'Stage 3 - Impaired',
    stage_1_desc: '12-Month Expected Loss',
    stage_2_desc: 'Lifetime Expected Loss',
    stage_3_desc: 'Default and Credit Impaired',
    checker_queue_title: 'Stress Test Scenarios Pending Review',
    col_run_code: 'Run ID',
    col_run_name: 'Scenario Title',
    col_maker: 'Created By',
    col_scenario: 'Scenario',
    col_delta_ps: 'Additional Provision',
    col_status: 'Status',
    col_actions: 'Actions',
    btn_forward_approver: 'Verify and Submit for Approval',
    btn_request_recalc: 'Request Recalculation',
    approver_title: 'Executive Approval Report',
    approver_subtitle: 'Multi-Dimensional Capital Adequacy Assessment and Bank-Wide Credit Directives',
    decision_1_title: '1. Curtail Credit Limits on Real Estate and Construction',
    decision_1_desc: 'Real Estate accounts for highest stress loss. Reduce new origination limits by 15% and redirect liquidity to manufacturing.',
    decision_2_title: '2. Allocate Additional Provision Evenly Across 4 Quarters',
    decision_2_desc: 'Finance and Accounting Division books provisions quarterly to safeguard capital targets and smooth profit impacts.',
    decision_3_title: '3. Activate Early Warning and Debt Workout Workflows',
    decision_3_desc: 'Special Assets and Workout Units conduct on-site collateral inspections, seek additional guarantees or restructure terms.',
    btn_sign_approve: 'Sign and Finalize Decision',
    search_placeholder: 'Search customer name or loan ID...',
    filter_all_sectors: 'All Economic Sectors',
    filter_all_stages: 'All Credit Stages',
    btn_export_csv: 'Export Excel Spreadsheet',
    col_contract_id: 'Loan Contract ID',
    col_customer: 'Borrower Name',
    col_sector: 'Sector',
    col_ead: 'Exposure at Default',
    col_interest: 'Interest Rate',
    col_rating: 'Internal Rating',
    col_collateral: 'Collateral Assets',
    col_stage: 'Credit Risk Stage',
    notice_no_permission: 'Your account does not have permission to access this module.',
    btn_methodology_detail: 'Calculation Methodology',
    modal_methodology_title: 'Quantitative Framework and Stress Testing Formulations'
  }
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  private http = inject(HttpClient);
  apiUrlOverride = signal<string>(typeof window !== 'undefined' ? localStorage.getItem('CUSTOM_API_BASE') || '' : '');
  showApiConfigModal = signal<boolean>(false);

  get API_BASE(): string {
    const custom = this.apiUrlOverride();
    if (custom && custom.trim()) {
      return custom.trim().replace(/\/$/, '');
    }
    if (typeof window !== 'undefined') {
      const host = window.location.hostname;
      if (host === 'localhost' || host === '127.0.0.1') {
        return 'http://127.0.0.1:8000/api';
      }
    }
    return 'https://credit-stress-testing.onrender.com/api';
  }

  saveCustomApi(url: string) {
    if (url && url.trim()) {
      localStorage.setItem('CUSTOM_API_BASE', url.trim());
      this.apiUrlOverride.set(url.trim());
    } else {
      localStorage.removeItem('CUSTOM_API_BASE');
      this.apiUrlOverride.set('');
    }
    this.showApiConfigModal.set(false);
    this.fetchInitialData();
  }

  currentLang = signal<'vi' | 'en'>('vi');
  currentUser = signal<SystemUser | null>(null);

  activeTab = signal<'maker' | 'checker' | 'approver' | 'portfolio' | 'audit'>('maker');

  readonly TEST_ACCOUNTS: SystemUser[] = [
    { id: 1, username: 'maker_an', full_name: 'Nguyễn Văn An', email: 'an.nguyen@bank.vn', role: 'MAKER', department: 'Phòng Đo lường Rủi ro' },
    { id: 2, username: 'checker_binh', full_name: 'Trần Thị Bình', email: 'binh.tran@bank.vn', role: 'CHECKER', department: 'Phòng Quản lý rủi ro' },
    { id: 3, username: 'approver_cuong', full_name: 'Lê Hoàng Cường', email: 'cuong.le@bank.vn', role: 'APPROVER', department: 'Ban Điều hành / Khối Quản lý rủi ro' },
    { id: 4, username: 'auditor_dung', full_name: 'Phạm Minh Dũng', email: 'dung.pham@bank.vn', role: 'AUDITOR', department: 'Khối Kiểm toán Nội bộ' },
    { id: 5, username: 'admin_system', full_name: 'Quản trị viên Hệ thống', email: 'admin.it@bank.vn', role: 'ADMIN', department: 'Khối Công nghệ Thông tin và CSDL' },
  ];

  loginUsername = signal<string>('maker_an');
  loginPassword = signal<string>('123456');
  loginError = signal<string>('');

  selectedPreset = signal<string>('ADVERSE');
  gdpShock = signal<number>(-1.5);
  irShock = signal<number>(200);
  unempShock = signal<number>(2.0);
  reShock = signal<number>(-15);

  isLoading = signal<boolean>(false);
  isSaving = signal<boolean>(false);
  notification = signal<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

  scenarios = signal<MacroScenario[]>([]);
  simulationResult = signal<SimulationResponse | null>(null);
  allRuns = signal<StressTestRun[]>([]);
  contracts = signal<LoanContract[]>([]);

  searchQuery = signal<string>('');
  selectedSectorFilter = signal<string>('ALL');
  selectedStageFilter = signal<string>('ALL');

  saveRunModalOpen = signal<boolean>(false);
  newRunName = signal<string>('Mô phỏng Kịch bản Căng thẳng Q4/2026');
  editingRun = signal<StressTestRun | null>(null);
  recalculationModalOpen = signal<boolean>(false);
  recalculationNote = signal<string>('Đề nghị Maker kiểm tra lại số liệu ngành BĐS và chạy thêm sốc lãi suất +300 bps.');
  selectedRunToReview = signal<StressTestRun | null>(null);
  selectedApproverRun = signal<StressTestRun | null>(null);
  allAuditLogs = signal<AuditLogItem[]>([]);
  auditActionFilter = signal<string>('ALL');
  methodologyModalOpen = signal<boolean>(false);
  selectedCalcTab = signal<'all' | 'ead' | 'ecl' | 'deltaps' | 'car' | 'npl'>('all');

  makerActiveView = signal<'simulation' | 'reports'>('simulation');
  makerRunFilter = signal<'ALL' | 'RECALCULATE' | 'DRAFT' | 'SUBMITTED' | 'PENDING' | 'APPROVED'>('ALL');
  makerSearchQuery = signal<string>('');

  renameModalOpen = signal<boolean>(false);
  runToRename = signal<StressTestRun | null>(null);
  renameValue = signal<string>('');

  viewDetailModalOpen = signal<boolean>(false);
  selectedRunDetail = signal<StressTestRun | null>(null);

  recalcRuns = computed(() => {
    return this.allRuns().filter(r => r.status === 'RECALCULATION_REQUESTED');
  });

  submittedRunsCount = computed(() => {
    return this.allRuns().filter(r => r.status === 'SUBMITTED').length;
  });

  approvedRunsCount = computed(() => {
    return this.allRuns().filter(r => r.status === 'APPROVED').length;
  });

  checkerRunFilter = signal<'ALL' | 'SUBMITTED' | 'PENDING' | 'RECALCULATE'>('ALL');

  checkerCheckDataIntegrity = signal<boolean>(true);
  checkerCheckEconomicLogic = signal<boolean>(true);
  checkerCheckCapitalAdequacy = signal<boolean>(true);
  selectedReviewDetail = signal<any | null>(null);
  checkerContractModalOpen = signal<boolean>(false);
  checkerContractSearch = signal<string>('');

  filteredReviewContracts = computed(() => {
    const detail = this.selectedReviewDetail();
    if (!detail || !detail.detailed_contracts) return [];
    const q = this.checkerContractSearch().trim().toLowerCase();
    if (!q) return detail.detailed_contracts;
    return detail.detailed_contracts.filter((c: any) =>
      (c.contract && String(c.contract).toLowerCase().includes(q)) ||
      (c.contract_customer_name && String(c.contract_customer_name).toLowerCase().includes(q)) ||
      (c.contract_sector && String(c.contract_sector).toLowerCase().includes(q))
    );
  });

  filteredCheckerRuns = computed(() => {
    const list = this.allRuns();
    const filter = this.checkerRunFilter();
    if (filter === 'SUBMITTED') return list.filter(r => r.status === 'SUBMITTED');
    if (filter === 'PENDING') return list.filter(r => r.status === 'PENDING_APPROVAL');
    if (filter === 'RECALCULATE') return list.filter(r => r.status === 'RECALCULATION_REQUESTED');
    return list;
  });

  filteredMakerRuns = computed(() => {
    let list = this.allRuns();
    const q = this.makerSearchQuery().toLowerCase().trim();
    if (q) {
      list = list.filter(r => 
        r.run_code.toLowerCase().includes(q) || 
        r.run_name.toLowerCase().includes(q) ||
        r.scenario_name.toLowerCase().includes(q)
      );
    }
    const filter = this.makerRunFilter();
    if (filter === 'ALL') return list;
    if (filter === 'RECALCULATE') return list.filter(r => r.status === 'RECALCULATION_REQUESTED');
    if (filter === 'DRAFT') return list.filter(r => r.status === 'DRAFT');
    if (filter === 'SUBMITTED') return list.filter(r => r.status === 'SUBMITTED');
    if (filter === 'PENDING') return list.filter(r => r.status === 'PENDING_APPROVAL');
    if (filter === 'APPROVED') return list.filter(r => r.status === 'APPROVED');
    return list;
  });

  setMakerView(view: 'simulation' | 'reports') {
    this.activeTab.set('maker');
    this.makerActiveView.set(view);
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  editRunProposal(run: StressTestRun) {
    this.loadRunParameters(run);
    this.makerActiveView.set('simulation');
  }

  openRenameModal(run: StressTestRun) {
    if (run.status === 'PENDING_APPROVAL' || run.status === 'APPROVED') {
      this.showNotification(
        this.currentLang() === 'vi'
          ? 'Đề án đã được duyệt hoặc đang chờ Giám đốc duyệt, không thể đổi tên!'
          : 'Cannot rename an approved proposal!',
        'error'
      );
      return;
    }
    this.runToRename.set(run);
    this.renameValue.set(run.run_name);
    this.renameModalOpen.set(true);
  }

  confirmRenameRun() {
    const run = this.runToRename();
    const newName = this.renameValue().trim();
    if (!run || !newName) return;

    this.http.patch<StressTestRun>(`${this.API_BASE}/stress-test/runs/${run.id}/manage/`, {
      run_name: newName,
      actor_id: this.currentUser()?.id || 1
    }).subscribe({
      next: (updated) => {
        this.renameModalOpen.set(false);
        this.runToRename.set(null);
        this.fetchRuns();
        this.showNotification(
          this.currentLang() === 'vi' 
            ? `Đã cập nhật tên đề án ${updated.run_code} thành: "${updated.run_name}"!` 
            : `Updated proposal name to "${updated.run_name}"!`
        );
      },
      error: () => this.showNotification(this.currentLang() === 'vi' ? 'Lỗi khi cập nhật tên đề án' : 'Error updating name', 'error')
    });
  }

  deleteRun(run: StressTestRun) {
    const confirmMsg = this.currentLang() === 'vi' 
      ? `Bạn có chắc chắn muốn xóa đề án ${run.run_code} ("${run.run_name}") không?` 
      : `Are you sure you want to delete proposal ${run.run_code}?`;
    if (typeof window !== 'undefined' && !window.confirm(confirmMsg)) return;

    this.http.delete(`${this.API_BASE}/stress-test/runs/${run.id}/manage/`).subscribe({
      next: () => {
        if (this.editingRun()?.id === run.id) {
          this.editingRun.set(null);
        }
        this.fetchRuns();
        this.showNotification(
          this.currentLang() === 'vi' 
            ? `Đã xóa đề án ${run.run_code} thành công!` 
            : `Deleted proposal ${run.run_code}!`
        );
      },
      error: () => this.showNotification(this.currentLang() === 'vi' ? 'Lỗi khi xóa đề án' : 'Error deleting proposal', 'error')
    });
  }

  openRunDetailModal(run: StressTestRun) {
    this.selectedRunDetail.set(run);
    this.viewDetailModalOpen.set(true);
  }

  loadRunParameters(run: StressTestRun) {
    if (run.status === 'PENDING_APPROVAL' || run.status === 'APPROVED') {
      this.showNotification(
        this.currentLang() === 'vi'
          ? 'Đề án đã được duyệt hoặc đang chờ Giám đốc duyệt, không thể chỉnh sửa!'
          : 'This proposal is approved or pending approval and cannot be modified!',
        'error'
      );
      return;
    }
    this.editingRun.set(run);
    if (run.custom_gdp_shock !== null && run.custom_gdp_shock !== undefined) {
      this.gdpShock.set(Number(run.custom_gdp_shock) * 100);
    }
    if (run.custom_ir_shock !== null && run.custom_ir_shock !== undefined) {
      this.irShock.set(Math.round(Number(run.custom_ir_shock) * 10000));
    }
    if (run.custom_unemp_shock !== null && run.custom_unemp_shock !== undefined) {
      this.unempShock.set(Number(run.custom_unemp_shock) * 100);
    }
    if (run.custom_re_shock !== null && run.custom_re_shock !== undefined) {
      this.reShock.set(Number(run.custom_re_shock) * 100);
    }
    this.selectedPreset.set('CUSTOM');
    const baseName = run.run_name.replace(/^\[(Tính lại|Recalculated)\]\s*/i, '');
    this.newRunName.set(
      run.status === 'RECALCULATION_REQUESTED'
        ? (this.currentLang() === 'vi' ? `[Tính lại] ${baseName}` : `[Recalculated] ${baseName}`)
        : run.run_name
    );
    this.runSimulation();
    
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    this.showNotification(
      this.currentLang() === 'vi'
        ? `Đang mở đề án ${run.run_code} để hiệu chỉnh tham số.`
        : `Loaded parameters for ${run.run_code}.`,
      'info'
    );
  }

  cancelEditingRun() {
    this.editingRun.set(null);
    this.showNotification(
      this.currentLang() === 'vi' 
        ? 'Đã thoát chế độ chỉnh sửa đề án cũ.' 
        : 'Exited edit mode.',
      'info'
    );
  }

  directive1Active = signal<boolean>(true);
  directive2Active = signal<boolean>(true);
  directive3Active = signal<boolean>(true);

  directive1Title = signal<string>('Cắt giảm hạn mức Bất động sản và Xây dựng');
  directive1CutPercent = signal<number>(15);
  directive1ActionNote = signal<string>('Khối KHDN tạm dừng giải ngân các khoản vay trung dài hạn mới thuộc lĩnh vực BĐS; ưu tiên điều chuyển dòng vốn sang nhóm sản xuất kinh doanh.');

  directive2Title = signal<string>('Phân bổ trích lập dự phòng phát sinh tăng');
  directive2Quarters = signal<number>(4);
  directive2ActionNote = signal<string>('Khối Tài chính Kế toán trích lập đều đặn theo từng quý vào chi phí hoạt động để ổn định kết quả kinh doanh và chỉ tiêu cổ tức.');

  directive3Title = signal<string>('Kích hoạt quy trình xử lý nợ sớm');
  directive3Scope = signal<'STAGE_2' | 'PD_2X' | 'GROUP_2'>('STAGE_2');
  directive3CustomScopeText = signal<string>('Khoản vay có rủi ro tín dụng gia tăng đáng kể');
  directive3ActionNote = signal<string>('Khối Xử lý và Thu hồi nợ tiến hành rà soát thực địa tài sản bảo đảm, đàm phán bổ sung tài sản thế chấp hoặc cơ cấu lại kỳ hạn.');

  directiveApproved = signal<boolean>(false);

  portfolioMode = signal<'ALL' | 'EARLY_WARNING'>('EARLY_WARNING');

  applyDirective1Preset(pct: number) {
    this.directive1CutPercent.set(pct);
  }

  applyDirective2Preset(q: number) {
    this.directive2Quarters.set(q);
  }

  applyDirective3Preset(scope: 'STAGE_2' | 'PD_2X' | 'GROUP_2') {
    this.directive3Scope.set(scope);
    if (scope === 'STAGE_2') {
      this.directive3CustomScopeText.set(this.currentLang() === 'vi' ? 'Khoản vay có rủi ro tín dụng gia tăng đáng kể' : 'Loans with significant increase in credit risk');
    } else if (scope === 'PD_2X') {
      this.directive3CustomScopeText.set(this.currentLang() === 'vi' ? 'Khoản vay có xác suất vỡ nợ tăng từ 2 lần trở lên' : 'Loans with default probability increased by 2x or more');
    } else {
      this.directive3CustomScopeText.set(this.currentLang() === 'vi' ? 'Hợp đồng nợ từ nhóm 2 trở lên' : 'Loans in Stage 2 and above');
    }
  }

  resetDirectivesToAI() {
    this.directive1CutPercent.set(15);
    this.directive1Title.set(this.currentLang() === 'vi' ? 'Cắt giảm hạn mức Bất động sản và Xây dựng' : 'Curtail Real Estate and Construction Credit Limits');
    this.directive1ActionNote.set(this.currentLang() === 'vi' 
      ? 'Khối KHDN tạm dừng giải ngân các khoản vay trung dài hạn mới thuộc lĩnh vực BĐS; ưu tiên điều chuyển dòng vốn sang nhóm sản xuất kinh doanh.'
      : 'Corporate Banking Unit pauses new long-term real estate loans; prioritize credit redirection to manufacturing.');

    this.directive2Quarters.set(4);
    this.directive2Title.set(this.currentLang() === 'vi' ? 'Phân bổ trích lập dự phòng phát sinh tăng' : 'Allocate Additional Provision Across Quarters');
    this.directive2ActionNote.set(this.currentLang() === 'vi' 
      ? 'Khối Tài chính Kế toán trích lập đều đặn theo từng quý vào chi phí hoạt động để ổn định kết quả kinh doanh và chỉ tiêu cổ tức.'
      : 'Finance and Accounting Division recognizes provisions quarterly to maintain operating targets and earnings stability.');

    this.directive3Scope.set('STAGE_2');
    this.directive3CustomScopeText.set(this.currentLang() === 'vi' ? 'Khoản vay có rủi ro tín dụng gia tăng đáng kể' : 'Loans with significant increase in credit risk');
    this.directive3Title.set(this.currentLang() === 'vi' ? 'Kích hoạt quy trình xử lý nợ sớm' : 'Activate Early Warning Workflows');
    this.directive3ActionNote.set(this.currentLang() === 'vi' 
      ? 'Khối Xử lý và Thu hồi nợ tiến hành rà soát thực địa tài sản bảo đảm, đàm phán bổ sung tài sản thế chấp hoặc cơ cấu lại kỳ hạn.'
      : 'Special Assets Unit conducts on-site collateral revaluation, negotiates additional security or term restructuring.');
  }

  goToEarlyWarningList() {
    this.activeTab.set('portfolio');
    this.portfolioMode.set('EARLY_WARNING');
  }

  getSectorBadgeClass(code: string): { bg: string; border: string; text: string; icon: string } {
    switch (code) {
      case 'REAL_ESTATE_CONSTRUCTION':
      case 'REAL_ESTATE':
      case 'CONSTRUCTION':
        return { bg: 'bg-rose-50/70', border: 'border-rose-300', text: 'text-rose-700', icon: 'fa-building' };
      case 'MANUFACTURING':
        return { bg: 'bg-blue-50/70', border: 'border-blue-300', text: 'text-blue-700', icon: 'fa-industry' };
      case 'AGRICULTURE':
        return { bg: 'bg-teal-50/70', border: 'border-teal-300', text: 'text-teal-700', icon: 'fa-wheat-awn' };
      case 'COMMERCE':
      case 'WHOLESALE_RETAIL':
        return { bg: 'bg-amber-50/70', border: 'border-amber-300', text: 'text-amber-700', icon: 'fa-cart-shopping' };
      case 'RETAIL':
      case 'CONSUMER_LOAN':
      default:
        return { bg: 'bg-indigo-50/70', border: 'border-indigo-300', text: 'text-indigo-700', icon: 'fa-user' };
    }
  }

  openCalcDetail(tab: 'all' | 'ead' | 'ecl' | 'deltaps' | 'car' | 'npl' = 'all') {
    this.selectedCalcTab.set(tab);
    this.methodologyModalOpen.set(true);
  }

  t(key: string): string {
    const lang = this.currentLang();
    return TRANSLATIONS[lang]?.[key] || TRANSLATIONS['vi']?.[key] || key;
  }

  toggleLanguage() {
    this.currentLang.set(this.currentLang() === 'vi' ? 'en' : 'vi');
  }

  getRoleLabel(role: string): string {
    if (!role) return '';
    const key = `role_${role.toLowerCase()}`;
    return this.t(key) || role;
  }

  getStatusLabel(status: string): string {
    if (!status) return '';
    if (this.currentLang() === 'vi') {
      switch (status) {
        case 'SUBMITTED': return 'Chờ thẩm định';
        case 'PENDING_APPROVAL': return 'Chờ phê duyệt';
        case 'APPROVED': return 'Đã phê duyệt';
        case 'RECALCULATION_REQUESTED': return 'Yêu cầu tính lại';
        case 'DRAFT': return 'Bản thảo';
        case 'REJECTED': return 'Đã từ chối';
        default: return status;
      }
    } else {
      switch (status) {
        case 'SUBMITTED': return 'Pending Review';
        case 'PENDING_APPROVAL': return 'Pending Approval';
        case 'APPROVED': return 'Approved';
        case 'RECALCULATION_REQUESTED': return 'Recalculation Requested';
        case 'DRAFT': return 'Draft';
        case 'REJECTED': return 'Rejected';
        default: return status;
      }
    }
  }

  getAuditActionLabel(action: string): string {
    if (!action) return '';
    if (this.currentLang() === 'vi') {
      switch (action) {
        case 'APPROVE': return 'Ký số Phê duyệt';
        case 'FORWARD_APPROVER': return 'Thẩm định Đạt';
        case 'RECALCULATE': return 'Yêu cầu Tính lại';
        case 'CANCEL_FORWARD': return 'Hủy Chuyển Duyệt';
        case 'CANCEL_APPROVE': return 'Hủy Phê Duyệt';
        case 'CANCEL_RECALCULATE': return 'Hủy Yêu Cầu Tính Lại';
        case 'CANCEL_SUBMIT': return 'Hủy Gửi Thẩm Định';
        case 'UPDATE': return 'Ghi Đè Bản Thảo';
        case 'RESUBMIT': return 'Ghi Đè và Gửi Lại';
        case 'SUBMIT':
        case 'CREATE_AND_SUBMIT': return 'Khởi tạo và Chuyển';
        case 'CREATE_DRAFT': return 'Tạo Bản Thảo';
        default: return action;
      }
    } else {
      switch (action) {
        case 'APPROVE': return 'CRO Approved';
        case 'FORWARD_APPROVER': return 'Review Passed';
        case 'RECALCULATE': return 'Recalculation Requested';
        case 'CANCEL_FORWARD': return 'Revoked Forward';
        case 'CANCEL_APPROVE': return 'Revoked Approval';
        case 'CANCEL_RECALCULATE': return 'Revoked Recalc Request';
        case 'CANCEL_SUBMIT': return 'Withdrawn to Draft';
        case 'UPDATE': return 'Updated Draft';
        case 'RESUBMIT': return 'Overwrote and Resubmitted';
        case 'SUBMIT':
        case 'CREATE_AND_SUBMIT': return 'Created and Submitted';
        case 'CREATE_DRAFT': return 'Created Draft';
        default: return action;
      }
    }
  }

  filteredContracts = computed(() => {
    const list = this.contracts();
    const query = this.searchQuery().toLowerCase().trim();
    const sec = this.selectedSectorFilter();
    const stg = this.selectedStageFilter();

    return list.filter(c => {
      const matchQuery = !query || 
        c.customer_name.toLowerCase().includes(query) || 
        c.contract_id.toLowerCase().includes(query) ||
        c.collateral_type.toLowerCase().includes(query);
      const matchSec = sec === 'ALL' || c.industry_sector === sec;
      const matchStg = stg === 'ALL' || c.initial_stage.toString() === stg;
      return matchQuery && matchSec && matchStg;
    });
  });

  earlyWarningContracts = computed(() => {
    const results = this.simulationResult()?.contract_results || [];
    return results.filter(r => r.is_sicr || r.stressed_stage > r.baseline_stage);
  });

  earlyWarningEAD = computed(() => {
    return this.earlyWarningContracts().reduce((sum, c) => sum + c.original_ead, 0);
  });

  earlyWarningDeltaPS = computed(() => {
    return this.earlyWarningContracts().reduce((sum, c) => sum + c.delta_provision, 0);
  });

  topStressedContracts = computed(() => {
    const results = [...(this.simulationResult()?.contract_results || [])];
    return results.sort((a, b) => b.delta_provision - a.delta_provision).slice(0, 5);
  });

  filteredStressedContracts = computed(() => {
    let list = this.simulationResult()?.contract_results || [];
    if (this.portfolioMode() === 'EARLY_WARNING') {
      list = list.filter(r => r.is_sicr || r.stressed_stage > r.baseline_stage);
    }
    const query = this.searchQuery().toLowerCase().trim();
    const sec = this.selectedSectorFilter();
    const stg = this.selectedStageFilter();

    return list.filter(c => {
      const matchQuery = !query || 
        c.customer_name.toLowerCase().includes(query) || 
        c.contract_id.toLowerCase().includes(query) ||
        (c.collateral_type && c.collateral_type.toLowerCase().includes(query));
      const matchSec = sec === 'ALL' || c.industry_sector === sec;
      const matchStg = stg === 'ALL' || c.stressed_stage.toString() === stg;
      return matchQuery && matchSec && matchStg;
    });
  });

  exportEarlyWarningCSV() {
    const data = this.portfolioMode() === 'EARLY_WARNING' ? this.earlyWarningContracts() : (this.simulationResult()?.contract_results || []);
    if (data.length === 0) return;

    let csvContent = 'data:text/csv;charset=utf-8,';
    csvContent += 'Mã HĐ,Khách Hàng,Phân Khúc,Ngành Nghề,Dư Nợ EAD (VND),Stage Gốc,Stage Sau Sốc,PD Gốc (%),PD Sau Sốc (%),Chênh Lệch PD (%),ΔPS Trích Thêm (VND),Cảnh Báo SICR,Biện Pháp Xử Lý\n';
    
    data.forEach(c => {
      const relIncrease = ((c.stressed_pd - c.baseline_pd) / (c.baseline_pd || 1) * 100).toFixed(1);
      csvContent += `"${c.contract_id}","${c.customer_name}","${c.customer_segment}","${c.sector_name_vn}",${c.original_ead},${c.baseline_stage},${c.stressed_stage},${(c.baseline_pd * 100).toFixed(2)},${(c.stressed_pd * 100).toFixed(2)},+${relIncrease}%,${c.delta_provision},"${c.is_sicr ? 'CẢNH BÁO SỚM' : 'CHUẨN'}","Định giá lại TSBĐ và kiểm tra thực địa"\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Early_Warning_List_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  filteredAuditLogs = computed(() => {
    const logs = this.allAuditLogs();
    const action = this.auditActionFilter();
    if (action === 'ALL') return logs;
    if (action === 'SUBMIT') {
      return logs.filter(l => l.action === 'SUBMIT' || l.action === 'CREATE_AND_SUBMIT' || l.action === 'RESUBMIT' || l.action === 'UPDATE');
    }
    return logs.filter(l => l.action === action);
  });

  currentSectorBreakdown = computed(() => {
    return this.simulationResult()?.sector_breakdown || [];
  });

  approverRuns = computed(() => {
    return this.allRuns().filter(r => r.status === 'PENDING_APPROVAL' || r.status === 'APPROVED');
  });

  openAuditTab() {
    this.activeTab.set('audit');
    this.fetchAuditLogs();
    this.fetchRuns();
  }

  fetchAuditLogs() {
    this.http.get<AuditLogItem[]>(`${this.API_BASE}/stress-test/audit-logs/`).subscribe({
      next: (logs) => this.allAuditLogs.set(logs),
      error: () => console.log('Could not fetch audit logs')
    });
  }

  ngOnInit() {
    const saved = localStorage.getItem('credit_risk_user');
    if (saved) {
      try {
        const u = JSON.parse(saved);
        this.setUser(u);
      } catch {
        this.setUser(this.TEST_ACCOUNTS[0]);
      }
    } else {
      this.setUser(this.TEST_ACCOUNTS[0]);
    }

    this.fetchInitialData();
  }

  loginWithAccount(user: SystemUser) {
    this.loginUsername.set(user.username);
    this.loginPassword.set('123456');
    this.http.post<SystemUser>(`${this.API_BASE}/login/`, {
      username: user.username,
      password: '123456',
      is_quick_login: true
    }).subscribe({
      next: (res) => {
        this.setUser(res);
        this.loginError.set('');
        this.showNotification(
          this.currentLang() === 'vi' 
            ? `Hỗ trợ đăng nhập nhanh thành công: ${this.getRoleLabel(res.role)}` 
            : `Quick login succeeded for ${this.getRoleLabel(res.role)}`
        );
      },
      error: () => {
        this.setUser(user);
        this.showNotification(this.currentLang() === 'vi' ? `Đăng nhập thành công với vai trò ${this.getRoleLabel(user.role)}` : `Logged in successfully as ${this.getRoleLabel(user.role)}`);
      }
    });
  }

  performLogin() {
    const uName = this.loginUsername().trim();
    const pwd = this.loginPassword();
    if (!uName) {
      this.loginError.set(this.currentLang() === 'vi' ? 'Vui lòng nhập tên đăng nhập' : 'Please enter username');
      return;
    }
    if (!pwd) {
      this.loginError.set(this.currentLang() === 'vi' ? 'Vui lòng nhập mật khẩu' : 'Please enter password');
      return;
    }

    this.http.post<SystemUser>(`${this.API_BASE}/login/`, {
      username: uName,
      password: pwd
    }).subscribe({
      next: (res) => {
        this.setUser(res);
        this.loginError.set('');
        this.showNotification(
          this.currentLang() === 'vi' 
            ? `Đăng nhập thành công với vai trò ${this.getRoleLabel(res.role)}` 
            : `Logged in successfully as ${this.getRoleLabel(res.role)}`
        );
      },
      error: (err) => {
        const msg = err.error?.error || (this.currentLang() === 'vi' ? 'Tài khoản hoặc mật khẩu không chính xác.' : 'Invalid username or password.');
        this.loginError.set(msg);
      }
    });
  }

  setUser(user: SystemUser) {
    this.currentUser.set(user);
    localStorage.setItem('credit_risk_user', JSON.stringify(user));

    if (user.role === 'MAKER') {
      this.activeTab.set('maker');
    } else if (user.role === 'CHECKER') {
      this.activeTab.set('checker');
    } else if (user.role === 'APPROVER') {
      this.activeTab.set('approver');
    } else {
      this.activeTab.set('portfolio');
    }
  }

  logout() {
    this.currentUser.set(null);
    localStorage.removeItem('credit_risk_user');
  }

  canAccess(tab: 'maker' | 'checker' | 'approver' | 'portfolio' | 'audit'): boolean {
    const role = this.currentUser()?.role;
    if (!role) return false;
    if (role === 'ADMIN') return true;
    if (tab === 'portfolio' || tab === 'audit') return true;
    if (tab === 'maker') return role === 'MAKER';
    if (tab === 'checker') return role === 'CHECKER';
    if (tab === 'approver') return role === 'APPROVER';
    return false;
  }

  showNotification(message: string, type: 'success' | 'error' | 'info' = 'success') {
    this.notification.set({ type, message });
    setTimeout(() => this.notification.set(null), 3500);
  }

  fetchInitialData() {
    this.isLoading.set(true);

    this.http.get<MacroScenario[]>(`${this.API_BASE}/scenarios/`).subscribe({
      next: (data) => this.scenarios.set(data),
      error: () => console.log('Offline/Starting')
    });

    this.http.get<LoanContract[]>(`${this.API_BASE}/loans/`).subscribe({
      next: (data) => this.contracts.set(data),
      error: () => console.log('Could not fetch contracts')
    });

    this.fetchRuns();
    this.runSimulation();
  }

  fetchRuns() {
    this.http.get<StressTestRun[]>(`${this.API_BASE}/stress-test/runs/`).subscribe({
      next: (runs) => {
        this.allRuns.set(runs);
        if (runs.length > 0) {
          const currentReview = this.selectedRunToReview();
          const target = currentReview ? (runs.find(r => r.id === currentReview.id) || runs[0]) : runs[0];
          this.selectedRunToReview.set(target);
          this.fetchRunReviewDetail(target.id);
        }
        
        const approverEligible = runs.filter(r => r.status === 'PENDING_APPROVAL' || r.status === 'APPROVED');
        if (approverEligible.length > 0) {
          const current = this.selectedApproverRun();
          const matched = current ? approverEligible.find(r => r.id === current.id) : null;
          this.selectedApproverRun.set(matched || approverEligible[0]);
        } else {
          this.selectedApproverRun.set(null);
        }
      }
    });

    this.http.get<AuditLogItem[]>(`${this.API_BASE}/stress-test/audit-logs/`).subscribe({
      next: (logs) => this.allAuditLogs.set(logs),
      error: () => console.log('Could not fetch audit logs')
    });
  }

  openCheckerTab() {
    this.activeTab.set('checker');
    const target = this.selectedRunToReview() || (this.allRuns().length > 0 ? this.allRuns()[0] : null);
    if (target) {
      this.selectedRunToReview.set(target);
      this.fetchRunReviewDetail(target.id);
    }
  }

  openApproverTab() {
    this.activeTab.set('approver');
    const approverEligible = this.allRuns().filter(r => r.status === 'PENDING_APPROVAL' || r.status === 'APPROVED');
    const target = this.selectedApproverRun() || (approverEligible.length > 0 ? approverEligible[0] : null);
    if (target) {
      this.selectedApproverRun.set(target);
      this.fetchRunReviewDetail(target.id);
    }
  }

  selectApproverRun(run: StressTestRun) {
    this.selectedApproverRun.set(run);
    this.fetchRunReviewDetail(run.id);
  }

  getStageCount(stageObj: any, stageNum: number | string): number {
    if (!stageObj) return 0;
    return stageObj[stageNum] ?? stageObj[String(stageNum)] ?? stageObj[`stage_${stageNum}`] ?? 0;
  }

  getReviewSectorBreakdown(): SectorBreakdown[] {
    const detail = this.selectedReviewDetail();
    if (detail && Array.isArray(detail.sector_breakdown) && detail.sector_breakdown.length > 0) {
      return detail.sector_breakdown;
    }
    const sim = this.simulationResult();
    if (sim && Array.isArray(sim.sector_breakdown)) {
      return sim.sector_breakdown;
    }
    return [];
  }

  getReviewStageMigration(): any {
    const detail = this.selectedReviewDetail();
    if (detail && detail.stage_migration && (detail.stage_migration.post_stress || detail.stage_migration.sicr_count !== undefined)) {
      return detail.stage_migration;
    }
    const sim = this.simulationResult();
    if (sim && sim.stage_migration) {
      return sim.stage_migration;
    }
    return null;
  }

  selectRunForReview(run: StressTestRun) {
    this.selectedRunToReview.set(run);
    this.checkerCheckDataIntegrity.set(true);
    this.checkerCheckEconomicLogic.set(true);
    this.checkerCheckCapitalAdequacy.set(true);
    this.fetchRunReviewDetail(run.id);
  }

  fetchRunReviewDetail(runId: number) {
    this.http.get<any>(`${this.API_BASE}/stress-test/runs/${runId}/`).subscribe({
      next: (data) => {
        this.selectedReviewDetail.set(data);
      },
      error: (err) => console.log('Could not fetch review detail', err)
    });
  }

  applyQuickSuggestion(text: string) {
    const current = this.recalculationNote().trim();
    if (!current) {
      this.recalculationNote.set(text);
    } else {
      this.recalculationNote.set(current + '; ' + text);
    }
  }

  onMacroInputChange(type: 'gdp' | 'ir' | 'unemp' | 're', val: any) {
    if (val === null || val === undefined || val === '') return;
    const num = Number(val);
    if (isNaN(num)) return;

    if (type === 'gdp') {
      this.gdpShock.set(num);
    } else if (type === 'ir') {
      this.irShock.set(Math.max(0, Math.round(num)));
    } else if (type === 'unemp') {
      this.unempShock.set(Math.max(0, num));
    } else if (type === 're') {
      this.reShock.set(num);
    }

    this.selectedPreset.set('CUSTOM');
    this.runSimulation();
  }

  applyPreset(preset: 'BASELINE' | 'ADVERSE' | 'SEVERE') {
    this.selectedPreset.set(preset);
    if (preset === 'BASELINE') {
      this.gdpShock.set(0.0);
      this.irShock.set(0);
      this.unempShock.set(0.0);
      this.reShock.set(0);
    } else if (preset === 'ADVERSE') {
      this.gdpShock.set(-1.5);
      this.irShock.set(200);
      this.unempShock.set(2.0);
      this.reShock.set(-15);
    } else if (preset === 'SEVERE') {
      this.gdpShock.set(-3.0);
      this.irShock.set(400);
      this.unempShock.set(4.5);
      this.reShock.set(-35);
    }
    this.runSimulation();
  }

  runSimulation() {
    this.isLoading.set(true);
    const body = {
      gdp_shock: this.gdpShock() / 100.0,
      ir_shock: this.irShock() / 10000.0,
      unemp_shock: this.unempShock() / 100.0,
      re_shock: this.reShock() / 100.0
    };

    this.http.post<SimulationResponse>(`${this.API_BASE}/stress-test/simulate/`, body).subscribe({
      next: (res) => {
        this.simulationResult.set(res);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });
  }

  openSaveModal() {
    if (!this.editingRun()) {
      const title = this.currentLang() === 'vi' 
        ? `Mô phỏng Kịch bản ${this.selectedPreset()} - ${new Date().toLocaleDateString('vi-VN')}`
        : `Stress Simulation ${this.selectedPreset()} - ${new Date().toLocaleDateString('en-US')}`;
      this.newRunName.set(title);
    }
    this.saveRunModalOpen.set(true);
  }

  confirmSaveRun(autoSubmit: boolean) {
    this.isSaving.set(true);
    const editing = this.editingRun();
    const body: any = {
      run_name: this.newRunName(),
      scenario_id: this.selectedPreset() === 'BASELINE' ? 1 : (this.selectedPreset() === 'ADVERSE' ? 2 : 3),
      maker_id: this.currentUser()?.id || 1,
      auto_submit: autoSubmit,
      gdp_shock: this.gdpShock() / 100.0,
      ir_shock: this.irShock() / 10000.0,
      unemp_shock: this.unempShock() / 100.0,
      re_shock: this.reShock() / 100.0
    };

    if (editing) {
      body.run_id = editing.id;
    }

    this.http.post<StressTestRun>(`${this.API_BASE}/stress-test/save-run/`, body).subscribe({
      next: (created) => {
        this.isSaving.set(false);
        this.saveRunModalOpen.set(false);
        this.editingRun.set(null);
        this.fetchRuns();
        this.showNotification(
          editing
            ? (autoSubmit 
                ? (this.currentLang() === 'vi' ? `Đã cập nhật ghi đè phiên ${created.run_code} và chuyển lại cho Trưởng phòng thẩm định!` : `Updated and resubmitted ${created.run_code} to Checker!`)
                : (this.currentLang() === 'vi' ? `Đã lưu cập nhật ghi đè bản thảo ${created.run_code}!` : `Updated draft ${created.run_code}!`))
            : (autoSubmit 
                ? (this.currentLang() === 'vi' ? `Đã lưu phiên ${created.run_code} và chuyển cho Trưởng phòng thẩm định!` : `Saved ${created.run_code} and forwarded to Checker!`)
                : (this.currentLang() === 'vi' ? `Đã lưu bản thảo ${created.run_code} thành công!` : `Saved draft ${created.run_code} successfully!`))
        );
      },
      error: () => {
        this.isSaving.set(false);
        this.showNotification(this.currentLang() === 'vi' ? 'Lỗi khi lưu phiên kiểm định' : 'Error saving simulation', 'error');
      }
    });
  }

  submitCheckerFeedback(action: 'RECALCULATE' | 'FORWARD_APPROVER' | 'CANCEL_FORWARD' | 'CANCEL_RECALCULATE') {
    const run = this.selectedRunToReview();
    if (!run) return;
    const note = this.recalculationNote().trim();

    if (action === 'CANCEL_FORWARD') {
      const cancelNote = note || (this.currentLang() === 'vi' 
        ? 'Trưởng phòng Quản lý rủi ro hủy chuyển phê duyệt, rút lại hồ sơ để tiếp tục rà soát.'
        : 'Checker revoked forward to approver to continue review.');
      this.executeWorkflow(run.id, 'CANCEL_FORWARD', cancelNote);
    } else if (action === 'CANCEL_RECALCULATE') {
      const cancelNote = note || (this.currentLang() === 'vi' 
        ? 'Trưởng phòng Quản lý rủi ro hủy yêu cầu tính lại, đưa hồ sơ về trạng thái Chờ thẩm định.'
        : 'Checker revoked recalculation request.');
      this.executeWorkflow(run.id, 'CANCEL_RECALCULATE', cancelNote);
    } else if (action === 'RECALCULATE') {
      const ok1 = this.checkerCheckDataIntegrity();
      const ok2 = this.checkerCheckEconomicLogic();
      const ok3 = this.checkerCheckCapitalAdequacy();

      const failedCriteria: string[] = [];
      if (!ok1) failedCriteria.push(this.currentLang() === 'vi' ? '1. Tính Toàn Vẹn Dữ Liệu' : '1. Data Integrity and Quality');
      if (!ok2) failedCriteria.push(this.currentLang() === 'vi' ? '2. Tính Logic Kinh Tế' : '2. Economic Sensitivity Logic');
      if (!ok3) failedCriteria.push(this.currentLang() === 'vi' ? '3. Điều Kiện Trình Phê Duyệt' : '3. Readiness for Approval');

      let feedback = '';
      if (failedCriteria.length > 0) {
        if (note) {
          feedback = `${note} (Tiêu chí chưa đạt: ${failedCriteria.join('; ')})`;
        } else {
          feedback = this.currentLang() === 'vi'
            ? `Đề án chưa đạt tiêu chuẩn thẩm định: [${failedCriteria.join('; ')}]. Đề nghị Chuyên viên kiểm tra lại và tính toán lại mô hình.`
            : `Proposal failed verification criteria: [${failedCriteria.join('; ')}]. Please review and recalculate.`;
        }
      } else {
        feedback = note || (this.currentLang() === 'vi' 
          ? 'Trưởng phòng Quản lý rủi ro yêu cầu Chuyên viên kiểm tra lại số liệu và điều chỉnh tham số kịch bản vĩ mô.'
          : 'Risk Management Head requested recalculation of scenario parameters.');
      }
      this.executeWorkflow(run.id, 'RECALCULATE', feedback);
    } else {
      const ok1 = this.checkerCheckDataIntegrity();
      const ok2 = this.checkerCheckEconomicLogic();
      const ok3 = this.checkerCheckCapitalAdequacy();
      if (!ok1 || !ok2 || !ok3) {
        const missing: string[] = [];
        if (!ok1) missing.push(this.currentLang() === 'vi' ? 'Tính Toàn Vẹn Dữ Liệu' : 'Data Integrity');
        if (!ok2) missing.push(this.currentLang() === 'vi' ? 'Tính Logic Kinh Tế' : 'Economic Sensitivity Logic');
        if (!ok3) missing.push(this.currentLang() === 'vi' ? 'Điều Kiện Trình Phê Duyệt' : 'Readiness for Approval');

        const warnMsg = this.currentLang() === 'vi'
          ? `Chưa thể chuyển phê duyệt: Tiêu chí kiểm soát [${missing.join(', ')}] chưa được đánh dấu đạt. Vui lòng rà soát và tích chọn đủ 3 tiêu chí.`
          : `Cannot forward: Checkpoints [${missing.join(', ')}] are not confirmed. Please verify all 3 checkpoints.`;
        this.showNotification(warnMsg, 'error');
        return;
      }

      const forwardNote = note || (this.currentLang() === 'vi' 
        ? 'Trưởng phòng Quản lý rủi ro đã thẩm định đạt 3 tiêu chuẩn: Tính toàn vẹn dữ liệu từ Core Banking, tính logic nhạy cảm chu kỳ kinh tế và mức độ xói mòn vốn đệm CAR. Kính trình Giám đốc Khối Quản lý rủi ro / CEO ký số phê duyệt.'
        : 'Risk Management Head verified and forwarded for executive approval.');
      this.executeWorkflow(run.id, 'FORWARD_APPROVER', forwardNote);
    }
  }

  executeWorkflow(runId: number, action: 'SUBMIT' | 'CANCEL_SUBMIT' | 'RECALCULATE' | 'CANCEL_RECALCULATE' | 'FORWARD_APPROVER' | 'CANCEL_FORWARD' | 'APPROVE' | 'CANCEL_APPROVE' | 'REJECT', comment: string = '') {
    const actorId = this.currentUser()?.id || 1;
    this.http.post<StressTestRun>(`${this.API_BASE}/stress-test/runs/${runId}/action/`, {
      action,
      actor_id: actorId,
      comment
    }).subscribe({
      next: (updated) => {
        this.fetchRuns();
        this.selectedRunToReview.set(updated);
        this.fetchRunReviewDetail(updated.id);
        this.selectedApproverRun.set(updated);
        this.recalculationModalOpen.set(false);
        this.recalculationNote.set('');
        
        let msg = '';
        if (action === 'FORWARD_APPROVER') {
          msg = this.currentLang() === 'vi' ? `Đã xác nhận và chuyển phiên ${updated.run_code} cho Giám đốc Khối Quản lý rủi ro / CEO!` : `Confirmed and submitted ${updated.run_code} to Chief Risk Officer / CEO!`;
        } else if (action === 'CANCEL_FORWARD') {
          msg = this.currentLang() === 'vi' ? `Đã hủy chuyển phê duyệt, rút lại phiên ${updated.run_code} về cấp Thẩm định!` : `Revoked submission of ${updated.run_code} back to Review!`;
        } else if (action === 'CANCEL_RECALCULATE') {
          msg = this.currentLang() === 'vi' ? `Đã hủy yêu cầu tính lại phiên ${updated.run_code}!` : `Revoked recalculation request for ${updated.run_code}!`;
        } else if (action === 'APPROVE') {
          this.directiveApproved.set(true);
          msg = this.currentLang() === 'vi' ? `Giám đốc Khối Quản lý rủi ro đã ký số ban hành quyết sách toàn hàng!` : `CRO has signed and authorized bank-wide directives!`;
        } else if (action === 'CANCEL_APPROVE') {
          this.directiveApproved.set(false);
          msg = this.currentLang() === 'vi' ? `Đã hủy ký số phê duyệt đề án ${updated.run_code}!` : `Revoked approval signature for ${updated.run_code}!`;
        } else if (action === 'RECALCULATE') {
          msg = this.currentLang() === 'vi' ? `Đã gửi nhận xét phản hồi và yêu cầu Chuyên viên tính toán lại!` : `Sent feedback and requested Analyst to recalculate!`;
        } else if (action === 'CANCEL_SUBMIT') {
          msg = this.currentLang() === 'vi' ? `Đã rút hồ sơ ${updated.run_code} về bản nháp!` : `Withdrawn ${updated.run_code} to draft!`;
        }
        if (msg) this.showNotification(msg, 'success');
      },
      error: (err) => {
        const errorMsg = err.error?.error || (this.currentLang() === 'vi' ? 'Thao tác không thành công hoặc bị từ chối do phân quyền!' : 'Operation failed or denied by RBAC!');
        this.showNotification(errorMsg, 'error');
      }
    });
  }

  exportCSV() {
    const data = this.filteredContracts();
    if (data.length === 0) return;

    let csvContent = 'data:text/csv;charset=utf-8,';
    csvContent += 'Contract ID,Customer ID,Customer Name,Segment,Industry,EAD (VND),Interest Rate,Tenor Months,Rating,IFRS 9 Stage,Baseline PD,Baseline LGD\n';
    
    data.forEach(c => {
      csvContent += `"${c.contract_id}","${c.customer_id}","${c.customer_name}","${c.customer_segment}","${c.industry_sector}",${c.original_ead},${c.interest_rate},${c.remaining_tenor_months},"${c.internal_rating}",${c.initial_stage},${c.baseline_pd},${c.baseline_lgd}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Loan_Portfolio_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  formatVND(value: any): string {
    if (value === undefined || value === null || value === '') return '0 VND';
    const num = typeof value === 'number' ? value : parseFloat(value);
    if (isNaN(num)) return '0 VND';
    if (Math.abs(num) >= 1_000_000_000_000) {
      const val = (num / 1_000_000_000_000).toLocaleString('vi-VN', { maximumFractionDigits: 2 });
      return this.currentLang() === 'vi' ? `${val} nghìn tỷ VND` : `${val} Trillion VND`;
    }
    if (Math.abs(num) >= 1_000_000_000) {
      const val = (num / 1_000_000_000).toLocaleString('vi-VN', { maximumFractionDigits: 1 });
      return this.currentLang() === 'vi' ? `${val} tỷ VND` : `${val} Billion VND`;
    }
    return num.toLocaleString('vi-VN') + ' VND';
  }

  formatPercent(val: any, decimals: number = 2): string {
    if (val === undefined || val === null || val === '') return '0.00%';
    let num = typeof val === 'number' ? val : parseFloat(val);
    if (isNaN(num)) return '0.00%';
    if (num > 0 && num <= 1.0) {
      num = num * 100.0;
    }
    return num.toFixed(decimals) + '%';
  }

  formatShock(val: any, multiplier: number = 100, decimals: number = 1, prefix: string = ''): string {
    if (val === undefined || val === null || val === '') return prefix + '0.0';
    const num = typeof val === 'number' ? val : parseFloat(val);
    if (isNaN(num)) return prefix + '0.0';
    return prefix + (num * multiplier).toFixed(decimals);
  }

  getSectorName(sectorCode: string): string {
    const mapVi: { [key: string]: string } = {
      'REAL_ESTATE_CONSTRUCTION': 'BĐS và Xây dựng',
      'MANUFACTURING': 'Sản xuất và Chế biến',
      'AGRICULTURE': 'Nông - Lâm - Thủy sản',
      'COMMERCE': 'Thương mại',
      'RETAIL': 'Bán lẻ',
      // Aliases
      'REAL_ESTATE': 'BĐS và Xây dựng',
      'CONSTRUCTION': 'BĐS và Xây dựng',
      'WHOLESALE_RETAIL': 'Thương mại',
      'CONSUMER_LOAN': 'Bán lẻ'
    };
    const mapEn: { [key: string]: string } = {
      'REAL_ESTATE_CONSTRUCTION': 'Real Estate & Construction',
      'MANUFACTURING': 'Manufacturing & Processing',
      'AGRICULTURE': 'Agriculture, Forestry & Fishery',
      'COMMERCE': 'Commerce & Trade',
      'RETAIL': 'Retail Banking',
      // Aliases
      'REAL_ESTATE': 'Real Estate & Construction',
      'CONSTRUCTION': 'Real Estate & Construction',
      'WHOLESALE_RETAIL': 'Commerce & Trade',
      'CONSUMER_LOAN': 'Retail Banking'
    };
    return this.currentLang() === 'vi' ? (mapVi[sectorCode] || sectorCode) : (mapEn[sectorCode] || sectorCode);
  }
}
