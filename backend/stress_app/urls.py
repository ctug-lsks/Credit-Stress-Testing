from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/stats/', views.get_dashboard_stats, name='dashboard-stats'),
    path('auth/login/', views.api_login, name='api-login'),
    path('loans/', views.list_loan_contracts, name='loans-list'),
    path('scenarios/', views.list_macro_scenarios, name='scenarios-list'),
    path('stress-test/simulate/', views.run_instant_simulation, name='stress-test-simulate'),
    path('stress-test/save-run/', views.save_stress_test_run, name='stress-test-save-run'),
    path('stress-test/runs/', views.list_stress_test_runs, name='stress-test-runs-list'),
    path('stress-test/runs/<int:run_id>/', views.get_stress_test_run_detail, name='stress-test-run-detail'),
    path('stress-test/runs/<int:run_id>/manage/', views.manage_stress_test_run, name='stress-test-run-manage'),
    path('stress-test/runs/<int:run_id>/action/', views.execute_workflow_action, name='stress-test-run-action'),
    path('stress-test/audit-logs/', views.list_audit_logs, name='stress-test-audit-logs'),
]
