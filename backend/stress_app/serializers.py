from rest_framework import serializers
from .models import (
    SystemUser, LoanAccount, MacroScenario, IndustrySensitivity,
    StressTestRun, ECLResult, CarImpact, AuditLog
)


class SystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        exclude = ['password_hash']


class LoanAccountPortfolioSerializer(serializers.ModelSerializer):
    """
    Serializer cho LOAN_ACCOUNTS (chuẩn hóa 3NF) kết hợp thông tin Khách hàng và TSBĐ.
    Đảm bảo 100% tương thích với hợp đồng dữ liệu của Frontend Angular.
    """
    contract_id = serializers.CharField(source='loan_id')
    customer_id = serializers.CharField(source='customer.customer_id')
    customer_name = serializers.CharField(source='customer.customer_name')
    customer_segment = serializers.CharField(source='customer.segment')
    industry_sector = serializers.CharField(source='customer.sector_code')
    original_ead = serializers.DecimalField(source='ead', max_digits=18, decimal_places=2)
    remaining_tenor_months = serializers.SerializerMethodField()
    collateral_type = serializers.SerializerMethodField()
    collateral_value = serializers.SerializerMethodField()
    baseline_haircut = serializers.SerializerMethodField()
    internal_rating = serializers.CharField(source='customer.internal_rating')
    baseline_pd = serializers.DecimalField(source='pd_base', max_digits=8, decimal_places=6)
    initial_stage = serializers.IntegerField(source='current_stage')
    overdue_days = serializers.IntegerField(source='days_past_due')

    class Meta:
        model = LoanAccount
        fields = [
            'contract_id', 'customer_id', 'customer_name', 'customer_segment',
            'industry_sector', 'original_ead', 'interest_rate', 'remaining_tenor_months',
            'collateral_type', 'collateral_value', 'baseline_haircut', 'internal_rating',
            'baseline_pd', 'baseline_lgd', 'initial_stage', 'overdue_days', 'created_at'
        ]

    def get_remaining_tenor_months(self, obj):
        return int(round(float(obj.remaining_term) * 12))

    def get_collateral_type(self, obj):
        alloc = obj.collateral_allocations.first()
        return alloc.collateral.collateral_type if alloc else 'Không'

    def get_collateral_value(self, obj):
        allocs = obj.collateral_allocations.all()
        return float(sum(a.allocated_value for a in allocs)) if allocs else 0.0

    def get_baseline_haircut(self, obj):
        alloc = obj.collateral_allocations.first()
        return float(alloc.collateral.liquidation_cost_rate) if alloc else 0.3000


# Alias for backward compatibility with frontend endpoints
LoanContractSerializer = LoanAccountPortfolioSerializer


class MacroScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MacroScenario
        fields = '__all__'


class IndustrySensitivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = IndustrySensitivity
        fields = '__all__'


class ECLResultSerializer(serializers.ModelSerializer):
    contract_id = serializers.CharField(source='loan_account.loan_id', read_only=True)
    contract_customer_name = serializers.CharField(source='loan_account.customer.customer_name', read_only=True)
    contract_sector = serializers.CharField(source='loan_account.customer.sector_code', read_only=True)
    contract_ead = serializers.DecimalField(source='loan_account.ead', max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = ECLResult
        fields = '__all__'


class CarImpactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarImpact
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', read_only=True)
    actor_role = serializers.CharField(source='actor.role', read_only=True)
    run_code = serializers.SerializerMethodField()
    run_name = serializers.CharField(source='run.run_name', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = '__all__'

    def get_run_code(self, obj):
        if obj.run and hasattr(obj.run, 'run_code'):
            return obj.run.run_code
        return obj.run_code or 'N/A'


class StressTestRunSerializer(serializers.ModelSerializer):
    scenario_name = serializers.CharField(source='scenario.scenario_name', read_only=True)
    maker_name = serializers.CharField(source='maker.full_name', read_only=True)
    checker_name = serializers.CharField(source='checker.full_name', read_only=True, default='')
    approver_name = serializers.CharField(source='approver.full_name', read_only=True, default='')
    car_impact = CarImpactSerializer(read_only=True)
    audit_logs = AuditLogSerializer(many=True, read_only=True)

    class Meta:
        model = StressTestRun
        fields = '__all__'
