from rest_framework import serializers
from .models import (
    SystemUser, LoanContract, MacroScenario, IndustrySensitivity,
    StressTestRun, ECLResult, CarImpact, AuditLog
)


class SystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = '__all__'


class LoanContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanContract
        fields = '__all__'


class MacroScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MacroScenario
        fields = '__all__'


class IndustrySensitivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = IndustrySensitivity
        fields = '__all__'


class ECLResultSerializer(serializers.ModelSerializer):
    contract_customer_name = serializers.CharField(source='contract.customer_name', read_only=True)
    contract_sector = serializers.CharField(source='contract.industry_sector', read_only=True)
    contract_ead = serializers.DecimalField(source='contract.original_ead', max_digits=15, decimal_places=2, read_only=True)

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
    run_code = serializers.CharField(source='run.run_code', read_only=True)
    run_name = serializers.CharField(source='run.run_name', read_only=True)

    class Meta:
        model = AuditLog
        fields = '__all__'


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
