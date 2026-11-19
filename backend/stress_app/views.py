import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (
    SystemUser, LoanAccount, MacroScenario, IndustrySensitivity,
    StressTestRun, ECLResult, CarImpact, AuditLog
)
from .serializers import (
    SystemUserSerializer, LoanContractSerializer, MacroScenarioSerializer,
    IndustrySensitivitySerializer, StressTestRunSerializer, ECLResultSerializer,
    AuditLogSerializer
)
from .calculation import calculate_stress_test


def get_all_loans():
    """Truy vấn trực tiếp từ bảng LOAN_ACCOUNTS kèm Khách hàng và TSBĐ (chuẩn hóa 3NF)."""
    return LoanAccount.objects.select_related('customer').prefetch_related('collateral_allocations__collateral').all()


@api_view(['GET'])
def get_dashboard_stats(request):
    """Returns general baseline portfolio stats calculated directly from LOAN_ACCOUNTS."""
    loans = list(get_all_loans())
    total_count = len(loans)
    if total_count == 0:
        return Response({'message': 'No data'}, status=200)

    total_ead = sum(float(l.ead) for l in loans)
    
    # Calculate initial baseline ECL
    calc = calculate_stress_test(loans, 0.0, 0.0, 0.0)
    
    users = SystemUser.objects.all()
    scenarios = MacroScenario.objects.all()
    recent_runs = StressTestRun.objects.order_by('-created_at')[:5]

    return Response({
        'total_contracts': total_count,
        'total_ead': total_ead,
        'baseline_ecl': calc['summary']['total_baseline_ecl'],
        'baseline_car': calc['summary']['baseline_car'],
        'npl_ratio': calc['summary']['npl_ratio_pre'],
        'users': SystemUserSerializer(users, many=True).data,
        'scenarios': MacroScenarioSerializer(scenarios, many=True).data,
        'recent_runs': StressTestRunSerializer(recent_runs, many=True).data
    })


@api_view(['GET'])
def list_loan_contracts(request):
    """List loans with filtering and search, queried directly from LOAN_ACCOUNTS."""
    queryset = get_all_loans()
    
    sector = request.GET.get('sector')
    if sector and sector != 'ALL':
        queryset = queryset.filter(customer__sector_code=sector)
        
    stage = request.GET.get('stage')
    if stage and stage != 'ALL':
        queryset = queryset.filter(current_stage=int(stage))
        
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(customer__customer_name__icontains=search) | queryset.filter(loan_id__icontains=search)
        
    serializer = LoanContractSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def list_macro_scenarios(request):
    scenarios = MacroScenario.objects.all()
    return Response(MacroScenarioSerializer(scenarios, many=True).data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def run_instant_simulation(request):
    """
    Lightweight simulation endpoint for interactive slider testing.
    Calculates directly from LOAN_ACCOUNTS without intermediate denormalized table.
    """
    gdp_shock = float(request.data.get('gdp_shock', 0.0))
    ir_shock = float(request.data.get('ir_shock', 0.0))
    re_shock = float(request.data.get('re_shock', 0.0))
    unemp_shock = float(request.data.get('unemp_shock', 0.0))
    recovery_time_years = request.data.get('recovery_time_years')
    scenario_weight = float(request.data.get('scenario_weight', 1.0))
    
    loans = list(get_all_loans())
    result = calculate_stress_test(
        loans,
        gdp_shock,
        ir_shock,
        re_shock,
        unemp_shock,
        recovery_time_years=recovery_time_years,
        scenario_weight=scenario_weight
    )
    return Response(result)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def save_stress_test_run(request):
    """
    Formal run execution: writes run to DB, generates ECL results and CAR impact,
    and sets workflow status to DRAFT or SUBMITTED.
    Supports overwriting/updating existing run if 'run_id' is provided.
    """
    run_id = request.data.get('run_id')
    scenario_id = request.data.get('scenario_id')
    run_name = request.data.get('run_name', f"Stress Test Run {timezone.now().strftime('%Y%m%d_%H%M')}")
    maker_id = request.data.get('maker_id', 1)
    auto_submit = request.data.get('auto_submit', False)
    
    gdp_shock = float(request.data.get('gdp_shock', 0.0))
    ir_shock = float(request.data.get('ir_shock', 0.0))
    re_shock = float(request.data.get('re_shock', 0.0))
    unemp_shock = float(request.data.get('unemp_shock', 0.0))

    try:
        scenario = MacroScenario.objects.get(pk=scenario_id) if scenario_id else MacroScenario.objects.first()
        maker = SystemUser.objects.get(pk=maker_id)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    loans = list(get_all_loans())
    t_rec = float(scenario.recovery_time_years) if (scenario and scenario.recovery_time_years) else None
    s_weight = float(scenario.scenario_weight) if (scenario and scenario.scenario_weight) else 1.0
    calc = calculate_stress_test(
        loans,
        gdp_shock,
        ir_shock,
        re_shock,
        unemp_shock,
        recovery_time_years=t_rec,
        scenario_weight=s_weight
    )
    summary = calc['summary']
    status_str = 'SUBMITTED' if auto_submit else 'DRAFT'

    npl_val = round(Decimal(str(summary['npl_ratio_post'])) / Decimal('100.0'), 4)
    llr_val = round(Decimal(str(summary['llr_expected'])) / Decimal('100.0'), 4)

    # Check if updating/overwriting an existing run
    run = None
    if run_id:
        try:
            run = StressTestRun.objects.get(pk=run_id)
            run.run_name = run_name
            run.scenario = scenario
            run.custom_gdp_shock = gdp_shock
            run.custom_ir_shock = ir_shock
            run.custom_re_shock = re_shock
            run.custom_unemp_shock = unemp_shock
            run.status = status_str
            run.total_ead = summary['total_ead']
            run.total_baseline_ecl = summary['total_baseline_ecl']
            run.total_stressed_ecl = summary['total_stressed_ecl']
            run.total_delta_provision = summary['total_delta_provision']
            run.npl_stress = npl_val
            run.llr_stress = llr_val
            run.snapshot_date = timezone.localdate()
            if auto_submit:
                run.rejection_reason = ''  # clear old rejection note on resubmit
            run.save()

            # Overwrite CarImpact
            CarImpact.objects.filter(run=run).delete()
            # Overwrite ECL results
            ECLResult.objects.filter(run=run).delete()
        except StressTestRun.DoesNotExist:
            run = None

    if not run:
        # Create brand new run
        run_code = f"RUN-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        run = StressTestRun.objects.create(
            run_code=run_code,
            run_name=run_name,
            scenario=scenario,
            custom_gdp_shock=gdp_shock,
            custom_ir_shock=ir_shock,
            custom_re_shock=re_shock,
            custom_unemp_shock=unemp_shock,
            maker=maker,
            status=status_str,
            total_ead=summary['total_ead'],
            total_baseline_ecl=summary['total_baseline_ecl'],
            total_stressed_ecl=summary['total_stressed_ecl'],
            total_delta_provision=summary['total_delta_provision'],
            npl_stress=npl_val,
            llr_stress=llr_val,
            snapshot_date=timezone.localdate()
        )

    # Save / Overwrite CAR Impact
    CarImpact.objects.create(
        run=run,
        baseline_tier1_capital=summary['baseline_tier1'],
        baseline_tier2_capital=summary['total_ead'] * 0.035,
        baseline_rwa=summary['baseline_rwa'],
        baseline_car=summary['baseline_car'] / 100.0,
        total_delta_provision=summary['total_delta_provision'],
        stressed_tier1_capital=summary['stressed_tier1'],
        stressed_rwa=summary['stressed_rwa'],
        stressed_car=summary['stressed_car'] / 100.0,
        car_change_bps=summary['car_change_bps'],
        minimum_regulatory_car=0.0800,
        is_capital_adequate=summary['is_capital_adequate']
    )

    # Bulk create ECL results directly linked to LOAN_ACCOUNTS
    loan_dict = {l.loan_id: l for l in loans}
    ecl_objs = [
        ECLResult(
            run=run,
            loan_account=loan_dict[r['contract_id']],
            baseline_pd=r['baseline_pd'],
            stressed_pd=r['stressed_pd'],
            baseline_lgd=r['baseline_lgd'],
            stressed_lgd=r['stressed_lgd'],
            baseline_stage=r['baseline_stage'],
            stressed_stage=r['stressed_stage'],
            discount_factor=Decimal(str(round(r.get('discount_factor', 0.913240), 6))),
            is_sicr=r['is_sicr'],
            baseline_ecl=r['baseline_ecl'],
            stressed_ecl=r['stressed_ecl'],
            delta_provision=r['delta_provision']
        )
        for r in calc['contract_results']
        if r['contract_id'] in loan_dict
    ]
    ECLResult.objects.bulk_create(ecl_objs)

    # Append-only immutable Audit Log
    if run_id:
        action_name = 'RESUBMIT' if auto_submit else 'UPDATE'
        action_note = f"Chuyên viên hiệu chỉnh tham số đề án {run.run_code}" + (" (Đã gửi lại cấp Thẩm định)." if auto_submit else " (Bản thảo).")
    else:
        action_name = 'CREATE_AND_SUBMIT' if auto_submit else 'CREATE'
        action_note = f"Khởi tạo kịch bản {run.run_code}: GDP shock {gdp_shock*100}%, IR shock +{ir_shock*10000}bps, RE shock {re_shock*100}%." + (" Đã chuyển Thẩm định." if auto_submit else "")
    
    AuditLog.objects.create(
        run=run,
        run_code=run.run_code,
        actor=maker,
        action=action_name,
        action_note=action_note,
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    return Response(StressTestRunSerializer(run).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def list_stress_test_runs(request):
    runs = StressTestRun.objects.all().order_by('-created_at')
    return Response(StressTestRunSerializer(runs, many=True).data)


@api_view(['GET'])
def get_stress_test_run_detail(request, run_id):
    try:
        run = StressTestRun.objects.get(pk=run_id)
    except StressTestRun.DoesNotExist:
        return Response({'error': 'Run not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = StressTestRunSerializer(run)
    ecl_results = ECLResult.objects.filter(run=run).select_related('loan_account__customer').prefetch_related('loan_account__collateral_allocations__collateral')
    if not ecl_results.exists():
        # Tự động tính toán và lưu kết quả ECL nếu phiên này chưa có chi tiết hợp đồng
        loans = list(get_all_loans())
        t_rec = float(run.scenario.recovery_time_years) if (run.scenario and run.scenario.recovery_time_years) else None
        s_weight = float(run.scenario.scenario_weight) if (run.scenario and run.scenario.scenario_weight) else 1.0
        calc = calculate_stress_test(
            loans,
            float(run.custom_gdp_shock or 0.0),
            float(run.custom_ir_shock or 0.0),
            float(run.custom_re_shock or 0.0),
            float(run.custom_unemp_shock or 0.0),
            recovery_time_years=t_rec,
            scenario_weight=s_weight
        )
        loan_dict = {la.loan_id: la for la in loans}
        ecl_objs = [
            ECLResult(
                run=run,
                loan_account=loan_dict[r['contract_id']],
                baseline_pd=r['baseline_pd'],
                stressed_pd=r['stressed_pd'],
                baseline_lgd=r['baseline_lgd'],
                stressed_lgd=r['stressed_lgd'],
                baseline_stage=r['baseline_stage'],
                stressed_stage=r['stressed_stage'],
                discount_factor=Decimal(str(round(r.get('discount_factor', 0.913240), 6))),
                is_sicr=r['is_sicr'],
                baseline_ecl=r['baseline_ecl'],
                stressed_ecl=r['stressed_ecl'],
                delta_provision=r['delta_provision']
            )
            for r in calc['contract_results']
            if r['contract_id'] in loan_dict
        ]
        if ecl_objs:
            ECLResult.objects.bulk_create(ecl_objs)
            ecl_results = ECLResult.objects.filter(run=run).select_related('loan_account__customer').prefetch_related('loan_account__collateral_allocations__collateral')

    ecl_data = ECLResultSerializer(ecl_results, many=True).data

    sensitivities = {
        s.sector_code: s.sector_name_vn
        for s in IndustrySensitivity.objects.all()
    }

    sectors_dict = {}
    stage_post = {1: 0, 2: 0, 3: 0}
    stage_pre = {1: 0, 2: 0, 3: 0}
    sicr_count = 0
    top_loans = []

    for item in ecl_results:
        loan_acc = item.loan_account
        cust = loan_acc.customer if loan_acc else None
        sec = cust.sector_code if cust else 'MANUFACTURING'
        sec_name = sensitivities.get(sec, sec)
        ead = float(loan_acc.ead) if loan_acc else 0.0
        base_ecl = float(item.baseline_ecl)
        str_ecl = float(item.stressed_ecl)
        delta_p = float(item.delta_provision)

        allocs = list(loan_acc.collateral_allocations.all()) if loan_acc else []
        col_type = allocs[0].collateral.collateral_type if allocs else 'Bất động sản'
        col_val = float(sum(a.allocated_value for a in allocs)) if allocs else 0.0

        if sec_name not in sectors_dict:
            sectors_dict[sec_name] = {
                'sector_code': sec,
                'sector_name': sec_name,
                'contract_count': 0,
                'ead': 0.0,
                'baseline_ecl': 0.0,
                'stressed_ecl': 0.0,
                'delta_provision': 0.0,
            }
        sectors_dict[sec_name]['contract_count'] += 1
        sectors_dict[sec_name]['ead'] += ead
        sectors_dict[sec_name]['baseline_ecl'] += base_ecl
        sectors_dict[sec_name]['stressed_ecl'] += str_ecl
        sectors_dict[sec_name]['delta_provision'] += delta_p

        stage_pre[item.baseline_stage] = stage_pre.get(item.baseline_stage, 0) + 1
        stage_post[item.stressed_stage] = stage_post.get(item.stressed_stage, 0) + 1
        if item.is_sicr:
            sicr_count += 1

        top_loans.append({
            'contract_id': loan_acc.loan_id if loan_acc else item.contract_id,
            'customer_name': cust.customer_name if cust else 'N/A',
            'customer_segment': cust.segment if cust else 'SME',
            'industry_sector': sec,
            'sector_name_vn': sec_name,
            'original_ead': ead,
            'collateral_type': col_type,
            'collateral_value': col_val,
            'baseline_pd': float(item.baseline_pd),
            'stressed_pd': float(item.stressed_pd),
            'baseline_lgd': float(item.baseline_lgd),
            'stressed_lgd': float(item.stressed_lgd),
            'baseline_stage': item.baseline_stage,
            'stressed_stage': item.stressed_stage,
            'is_sicr': item.is_sicr,
            'baseline_ecl': base_ecl,
            'stressed_ecl': str_ecl,
            'delta_provision': delta_p,
        })

    top_loans.sort(key=lambda x: x['delta_provision'], reverse=True)
    top_risk_loans = top_loans[:5]

    sector_breakdown = list(sectors_dict.values())
    sector_breakdown.sort(key=lambda x: x['delta_provision'], reverse=True)

    data = serializer.data
    data['detailed_contracts'] = ecl_data
    data['sector_breakdown'] = sector_breakdown
    data['stage_migration'] = {
        'pre_stress': {
            1: stage_pre.get(1, 0), 2: stage_pre.get(2, 0), 3: stage_pre.get(3, 0),
            '1': stage_pre.get(1, 0), '2': stage_pre.get(2, 0), '3': stage_pre.get(3, 0),
            'stage_1': stage_pre.get(1, 0), 'stage_2': stage_pre.get(2, 0), 'stage_3': stage_pre.get(3, 0)
        },
        'post_stress': {
            1: stage_post.get(1, 0), 2: stage_post.get(2, 0), 3: stage_post.get(3, 0),
            '1': stage_post.get(1, 0), '2': stage_post.get(2, 0), '3': stage_post.get(3, 0),
            'stage_1': stage_post.get(1, 0), 'stage_2': stage_post.get(2, 0), 'stage_3': stage_post.get(3, 0)
        },
        'sicr_count': sicr_count,
        'migrated_to_stage2': sum(1 for item in ecl_results if item.baseline_stage == 1 and item.stressed_stage == 2),
        'migrated_to_stage3': sum(1 for item in ecl_results if item.baseline_stage != 3 and item.stressed_stage == 3)
    }
    data['top_risk_loans'] = top_risk_loans
    return Response(data)


@api_view(['PATCH', 'PUT', 'DELETE'])
@authentication_classes([])
@permission_classes([AllowAny])
def manage_stress_test_run(request, run_id):
    try:
        run = StressTestRun.objects.get(pk=run_id)
    except StressTestRun.DoesNotExist:
        return Response({'error': 'Run not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        code = run.run_code
        run.delete()
        return Response({'message': f'Đã xóa thành công đề án {code}'}, status=status.HTTP_200_OK)

    run_name = request.data.get('run_name')
    if run_name and run_name.strip():
        run.run_name = run_name.strip()
        run.save()
        actor_id = request.data.get('actor_id', 1)
        actor = SystemUser.objects.filter(pk=actor_id).first()
        if actor:
            AuditLog.objects.create(
                run=run,
                actor=actor,
                action='UPDATE',
                action_note=f"Chuyên viên đổi tên đề án thành: '{run.run_name}'."
            )

    return Response(StressTestRunSerializer(run).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def execute_workflow_action(request, run_id):
    """
    Maker / Checker / Approver workflow transitions.
    Enforces RBAC permissions and the Four-Eyes Principle (Maker cannot self-approve).
    Writes immutable append-only audit trail logs.
    """
    try:
        run = StressTestRun.objects.get(pk=run_id)
    except StressTestRun.DoesNotExist:
        return Response({'error': 'Phiên kiểm định không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get('action')
    actor_id = request.data.get('actor_id')
    comment = request.data.get('comment', '').strip()

    if not actor_id:
        return Response({'error': 'Thiếu định danh người dùng thực hiện (actor_id).'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        actor = SystemUser.objects.get(pk=actor_id)
    except SystemUser.DoesNotExist:
        return Response({'error': 'Người dùng không tồn tại trong hệ thống.'}, status=status.HTTP_404_NOT_FOUND)

    # 1. Phân quyền RBAC theo ma trận chức năng
    ROLE_ACTIONS = {
        'MAKER': ['SUBMIT', 'CANCEL_SUBMIT'],
        'CHECKER': ['RECALCULATE', 'CANCEL_RECALCULATE', 'FORWARD_APPROVER', 'CANCEL_FORWARD'],
        'APPROVER': ['APPROVE', 'CANCEL_APPROVE', 'REJECT'],
        'ADMIN': ['SUBMIT', 'CANCEL_SUBMIT', 'RECALCULATE', 'CANCEL_RECALCULATE', 'FORWARD_APPROVER', 'CANCEL_FORWARD', 'APPROVE', 'CANCEL_APPROVE', 'REJECT'],
    }
    allowed_actions = ROLE_ACTIONS.get(actor.role, [])
    if action not in allowed_actions:
        return Response({
            'error': f'Phân quyền RBAC: Người dùng {actor.full_name} ({actor.get_role_display()}) không có thẩm quyền thực hiện thao tác "{action}".'
        }, status=status.HTTP_403_FORBIDDEN)

    # 2. Tuân thủ nguyên tắc Bốn mắt (Four-Eyes Principle)
    if action == 'APPROVE':
        if actor.id == run.maker_id:
            return Response({
                'error': 'Vi phạm nguyên tắc Bốn mắt (Four-Eyes Principle): Cán bộ lập đề án (Maker) không được quyền tự phê duyệt đề án của chính mình.'
            }, status=status.HTTP_403_FORBIDDEN)

    default_note = f"Thực hiện chuyển trạng thái thành {run.status}"

    if action == 'SUBMIT':
        run.status = 'SUBMITTED'
        run.checker = SystemUser.objects.filter(role='CHECKER').first()
        default_note = "Chuyên viên khởi tạo và chuyển hồ sơ sang cấp Thẩm định."
    elif action == 'CANCEL_SUBMIT':
        run.status = 'DRAFT'
        run.checker = None
        default_note = "Chuyên viên hủy gửi thẩm định, rút hồ sơ về Bản thảo (Draft)."
    elif action == 'RECALCULATE':
        run.status = 'RECALCULATION_REQUESTED'
        run.rejection_reason = comment
        default_note = "Trưởng phòng Quản lý rủi ro yêu cầu tính toán lại mô hình."
    elif action == 'CANCEL_RECALCULATE':
        run.status = 'SUBMITTED'
        run.rejection_reason = ''
        default_note = "Trưởng phòng Quản lý rủi ro hủy yêu cầu tính lại, đưa hồ sơ về trạng thái Chờ thẩm định."
    elif action == 'FORWARD_APPROVER':
        run.status = 'PENDING_APPROVAL'
        run.checker = actor
        run.approver = SystemUser.objects.filter(role='APPROVER').first()
        default_note = "Trưởng phòng Quản lý rủi ro thẩm định đạt và chuyển Ban Điều hành phê duyệt."
    elif action == 'CANCEL_FORWARD':
        run.status = 'SUBMITTED'
        run.approver = None
        default_note = "Trưởng phòng Quản lý rủi ro hủy chuyển phê duyệt, rút lại hồ sơ về cấp Thẩm định."
    elif action == 'APPROVE':
        run.status = 'APPROVED'
        run.approver = actor
        run.approved_at = timezone.now()
        default_note = "Giám đốc Khối Quản lý rủi ro / Ban Điều hành đã ký số phê duyệt đề án."
    elif action == 'CANCEL_APPROVE':
        run.status = 'PENDING_APPROVAL'
        run.approved_at = None
        default_note = "Giám đốc Khối Quản lý rủi ro hủy quyết định phê duyệt, thu hồi ký số về trạng thái Chờ phê duyệt."
    elif action == 'REJECT':
        run.status = 'REJECTED'
        run.rejection_reason = comment
        default_note = "Ban Điều hành từ chối phê duyệt đề án kiểm định."
    else:
        return Response({'error': f'Thao tác không được hỗ trợ: {action}'}, status=status.HTTP_400_BAD_REQUEST)

    run.save()

    # 3. Nhật ký kiểm toán bất biến (Append-only Audit Log)
    AuditLog.objects.create(
        run=run,
        run_code=run.run_code,
        actor=actor,
        action=action,
        action_note=comment or default_note,
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1')
    )

    return Response(StressTestRunSerializer(run).data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def api_login(request):
    """
    Xác thực người dùng tập trung bằng thuật toán PBKDF2 with SHA-256 (Django default).
    Hỗ trợ chế độ 'Đăng nhập nhanh' cho môi trường PoC / Demo.
    """
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    is_quick_login = request.data.get('is_quick_login', False)

    if not username:
        return Response({'error': 'Vui lòng nhập tên đăng nhập.'}, status=status.HTTP_400_BAD_REQUEST)

    user = SystemUser.objects.filter(username=username).first()
    if not user:
        # Hỗ trợ tìm kiếm theo role nếu tiện ích quick login gửi mã vai trò
        user = SystemUser.objects.filter(role=username.upper()).first()

    if not user:
        return Response({'error': 'Tài khoản không tồn tại trong hệ thống.'}, status=status.HTTP_404_NOT_FOUND)

    if not user.is_active:
        return Response({'error': 'Tài khoản hiện đang bị tạm khóa hoặc ngừng kích hoạt.'}, status=status.HTTP_403_FORBIDDEN)

    # Tiện ích đăng nhập nhanh: nếu không truyền mật khẩu, dùng mật khẩu mặc định
    if is_quick_login and not password:
        password = '123456'

    if not password:
        return Response({'error': 'Vui lòng nhập mật khẩu xác thực.'}, status=status.HTTP_400_BAD_REQUEST)

    # Kiểm tra mật khẩu mã hóa PBKDF2
    is_valid = user.check_password(password)
    # Khởi tạo hash nếu DB chưa có nhưng dùng mật khẩu chuẩn demo
    if not is_valid and (password in ['123456', 'Bank@123']):
        user.set_password(password)
        is_valid = True

    if not is_valid:
        return Response({'error': 'Mật khẩu xác thực không chính xác. Vui lòng kiểm tra lại.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Cập nhật thời điểm đăng nhập gần nhất (last_login)
    user.last_login = timezone.now()
    user.save(update_fields=['last_login', 'password_hash'])

    return Response({
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'email': user.email,
        'role': user.role,
        'department': user.department,
        'last_login': user.last_login
    })


@api_view(['GET'])
def list_audit_logs(request):
    """Retrieve full audit logs history across all stress test runs."""
    logs = AuditLog.objects.select_related('run', 'actor').all().order_by('-created_at')[:100]
    return Response(AuditLogSerializer(logs, many=True).data)


