from django.contrib import admin
from .models import (
    Customer,
    LoanAccount,
    Collateral,
    LoanCollateral,
    MacroScenario,
    IndustrySensitivity,
    StressTestRun,
    ECLResult,
    SystemUser,
    AuditLog,
    CarImpact
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'customer_name', 'segment', 'sector_code', 'internal_rating', 'created_at')
    list_filter = ('segment', 'sector_code', 'internal_rating')
    search_fields = ('customer_id', 'customer_name')
    ordering = ('customer_id',)


@admin.register(LoanAccount)
class LoanAccountAdmin(admin.ModelAdmin):
    list_display = ('loan_id', 'customer', 'ead', 'interest_rate', 'remaining_term', 'debt_group', 'current_stage', 'pd_base', 'snapshot_date')
    list_filter = ('current_stage', 'debt_group', 'snapshot_date')
    search_fields = ('loan_id', 'customer__customer_name', 'customer__customer_id')
    ordering = ('loan_id',)


@admin.register(Collateral)
class CollateralAdmin(admin.ModelAdmin):
    list_display = ('collateral_id', 'collateral_type', 'appraised_value', 'liquidation_cost_rate', 'appraisal_date')
    list_filter = ('collateral_type',)
    search_fields = ('collateral_id', 'collateral_type')
    ordering = ('collateral_id',)


@admin.register(LoanCollateral)
class LoanCollateralAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan', 'collateral', 'allocated_value')
    search_fields = ('loan__loan_id', 'collateral__collateral_id', 'collateral__collateral_type')


@admin.register(MacroScenario)
class MacroScenarioAdmin(admin.ModelAdmin):
    list_display = ('scenario_code', 'scenario_name', 'scenario_type', 'gdp_growth_shock', 'interest_rate_shock', 'unemployment_shock', 'real_estate_price_shock', 'is_active')
    list_filter = ('scenario_type', 'is_active')
    search_fields = ('scenario_code', 'scenario_name')


@admin.register(IndustrySensitivity)
class IndustrySensitivityAdmin(admin.ModelAdmin):
    list_display = ('sector_code', 'sector_name_vn', 'beta_gdp', 'beta_interest', 'beta_real_estate', 'pd_multiplier')
    search_fields = ('sector_code', 'sector_name_vn')


@admin.register(StressTestRun)
class StressTestRunAdmin(admin.ModelAdmin):
    list_display = ('run_code', 'run_name', 'status', 'maker', 'checker', 'approver', 'total_ead', 'total_stressed_ecl', 'total_delta_provision', 'created_at')
    list_filter = ('status', 'scenario')
    search_fields = ('run_code', 'run_name', 'maker__full_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ECLResult)
class ECLResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'loan_account', 'baseline_stage', 'stressed_stage', 'is_sicr', 'early_warning_flag', 'delta_provision')
    list_filter = ('is_sicr', 'early_warning_flag', 'baseline_stage', 'stressed_stage')
    search_fields = ('loan_account__loan_id', 'loan_account__customer__customer_name', 'run__run_code')


@admin.register(SystemUser)
class SystemUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'email', 'role', 'department', 'is_active', 'created_at')
    list_filter = ('role', 'department', 'is_active')
    search_fields = ('username', 'full_name', 'email')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'actor', 'action', 'action_note', 'created_at')
    list_filter = ('action', 'actor')
    search_fields = ('run__run_code', 'actor__full_name', 'action_note')
    readonly_fields = ('created_at',)


@admin.register(CarImpact)
class CarImpactAdmin(admin.ModelAdmin):
    list_display = ('run', 'baseline_car', 'stressed_car', 'car_change_bps', 'is_capital_adequate', 'calculated_at')
    list_filter = ('is_capital_adequate',)
    search_fields = ('run__run_code',)


# Customize Admin Site Branding
admin.site.site_header = "Hệ Thống Kiểm Định Rủi Ro Tín Dụng IFRS 9"
admin.site.site_title = "Quản Trị Cơ Sở Dữ Liệu IFRS 9"
admin.site.index_title = "Danh Mục Thực Thể Dữ Liệu (Theo Báo Cáo Nghiên Cứu)"
