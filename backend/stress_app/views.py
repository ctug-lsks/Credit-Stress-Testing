import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (
    SystemUser, LoanContract, MacroScenario, IndustrySensitivity,
    StressTestRun, ECLResult, CarImpact, AuditLog
)
from .serializers import (
    SystemUserSerializer, LoanContractSerializer, MacroScenarioSerializer,
    IndustrySensitivitySerializer, StressTestRunSerializer, ECLResultSerializer,
    AuditLogSerializer
)
from .calculation import calculate_stress_test


@api_view(['GET'])
def get_dashboard_stats(request):
    """Returns general baseline portfolio stats."""
    contracts = LoanContract.objects.all()
    total_count = contracts.count()
    if total_count == 0:
        return Response({'message': 'No data'}, status=200)

    total_ead = sum(float(c.original_ead) for c in contracts)
    
    # Calculate initial baseline ECL
    calc = calculate_stress_test(contracts, 0.0, 0.0, 0.0)
    
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
    """List contracts with filtering and search."""
    queryset = LoanContract.objects.all()
    
    sector = request.GET.get('sector')
    if sector and sector != 'ALL':
        queryset = queryset.filter(industry_sector=sector)
        
    stage = request.GET.get('stage')
    if stage and stage != 'ALL':
        queryset = queryset.filter(initial_stage=int(stage))
        
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(customer_name__icontains=search) | queryset.filter(contract_id__icontains=search)
        
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
    Does not write to DB; returns immediate calculation results.
    """
    gdp_shock = float(request.data.get('gdp_shock', 0.0))
    ir_shock = float(request.data.get('ir_shock', 0.0))
    re_shock = float(request.data.get('re_shock', 0.0))
    unemp_shock = float(request.data.get('unemp_shock', 0.0))
    
    contracts = LoanContract.objects.all()
    result = calculate_stress_test(contracts, gdp_shock, ir_shock, re_shock, unemp_shock)
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

    contracts = list(LoanContract.objects.all())
    calc = calculate_stress_test(contracts, gdp_shock, ir_shock, re_shock, unemp_shock)
    summary = calc['summary']
    status_str = 'SUBMITTED' if auto_submit else 'DRAFT'

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

    # Bulk create ECL results
    contract_dict = {c.contract_id: c for c in contracts}
    ecl_objs = [
        ECLResult(
            run=run,
            contract=contract_dict[r['contract_id']],
            baseline_pd=r['baseline_pd'],
            stressed_pd=r['stressed_pd'],
            baseline_lgd=r['baseline_lgd'],
            stressed_lgd=r['stressed_lgd'],
            baseline_stage=r['baseline_stage'],
            stressed_stage=r['stressed_stage'],
            is_sicr=r['is_sicr'],
            baseline_ecl=r['baseline_ecl'],
            stressed_ecl=r['stressed_ecl'],
            delta_provision=r['delta_provision']
        )
        for r in calc['contract_results']
    ]
    ECLResult.objects.bulk_create(ecl_objs)

    # Log action cleanly (avoid redundant duplicate entries)
    if run_id:
        action_name = 'RESUBMIT' if auto_submit else 'UPDATE'
        action_note = f"Chuyên viên hiệu chỉnh tham số và ghi đè đề án {run.run_code}" + (" (Đã gửi lại cấp Thẩm định)." if auto_submit else " (Bản thảo).")
        latest_log = AuditLog.objects.filter(run=run).order_by('-id').first()
        if latest_log and latest_log.actor == maker and latest_log.action == action_name:
            latest_log.action_note = action_note
            latest_log.created_at = timezone.now()
            latest_log.save()
        else:
            AuditLog.objects.create(run=run, actor=maker, action=action_name, action_note=action_note)
    else:
        action_name = 'CREATE_AND_SUBMIT' if auto_submit else 'CREATE'
        action_note = f"Khởi tạo kịch bản {run.run_code}: GDP shock {gdp_shock*100}%, IR shock +{ir_shock*10000}bps, RE shock {re_shock*100}%." + (" Đã chuyển Thẩm định." if auto_submit else "")
        AuditLog.objects.create(run=run, actor=maker, action=action_name, action_note=action_note)

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
    ecl_results = ECLResult.objects.filter(run=run).select_related('contract')
    ecl_data = ECLResultSerializer(ecl_results, many=True).data

    data = serializer.data
    data['detailed_contracts'] = ecl_data
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
    Supported actions:
    - SUBMIT: Maker -> Checker
    - CANCEL_SUBMIT: Maker revokes submission back to DRAFT
    - RECALCULATE: Checker -> Maker (with notes)
    - CANCEL_RECALCULATE: Checker cancels recalculation request, back to SUBMITTED
    - FORWARD_APPROVER: Checker -> Approver
    - CANCEL_FORWARD: Checker cancels forward to approver, back to SUBMITTED
    - APPROVE: Approver approves and signs
    - CANCEL_APPROVE: Approver cancels approval, back to PENDING_APPROVAL
    - REJECT: Approver rejects
    """
    try:
        run = StressTestRun.objects.get(pk=run_id)
    except StressTestRun.DoesNotExist:
        return Response({'error': 'Run not found'}, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get('action')
    actor_id = request.data.get('actor_id', 1)
    comment = request.data.get('comment', '')

    try:
        actor = SystemUser.objects.get(pk=actor_id)
    except SystemUser.DoesNotExist:
        actor = SystemUser.objects.first()

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
        return Response({'error': f'Unsupported action {action}'}, status=status.HTTP_400_BAD_REQUEST)

    run.save()

    # Avoid redundant duplicate audit logs: if last log on this run is identical action and actor, update it instead of creating duplicates
    last_log = AuditLog.objects.filter(run=run).order_by('-created_at').first()
    if last_log and last_log.action == action and last_log.actor == actor:
        last_log.action_note = comment or default_note
        last_log.created_at = timezone.now()
        last_log.save()
    else:
        AuditLog.objects.create(
            run=run,
            actor=actor,
            action=action,
            action_note=comment or default_note
        )

    return Response(StressTestRunSerializer(run).data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def api_login(request):
    """Authenticate user and return role details."""
    username = request.data.get('username', '').strip()
    try:
        user = SystemUser.objects.get(username=username)
    except SystemUser.DoesNotExist:
        user = SystemUser.objects.filter(role=username.upper()).first()
        if not user:
            return Response({'error': 'Tài khoản không tồn tại trong hệ thống.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'email': user.email,
        'role': user.role,
        'department': user.department
    })


@api_view(['GET'])
def list_audit_logs(request):
    """Retrieve full audit logs history across all stress test runs."""
    logs = AuditLog.objects.select_related('run', 'actor').all().order_by('-created_at')[:100]
    return Response(AuditLogSerializer(logs, many=True).data)


