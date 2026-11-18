import math
from decimal import Decimal
from .models import LoanContract, IndustrySensitivity, MacroScenario


def calculate_stress_test(loan_contracts, gdp_shock, ir_shock, re_shock, unemp_shock=0.0):
    """
    Core mathematical engine for IFRS 9 Credit Stress Testing.
    
    Inputs:
    - loan_contracts: QuerySet or list of LoanContract objects
    - gdp_shock: float (e.g. -0.015 for -1.5%)
    - ir_shock: float (e.g. 0.020 for +200 bps)
    - re_shock: float (e.g. -0.150 for -15%)
    - unemp_shock: float (e.g. 0.020 for +2.0% unemployment increase)
    
    Outputs:
    - contract_results: list of dicts with individual loan results
    - summary_metrics: aggregate bank-level KPIs (EAD, ECL, Delta PS, CAR)
    - sector_breakdown: ECL distribution by economic sector
    - stage_migration: counts of loans in Stage 1, 2, 3 before and after stress
    """
    gdp_shock = float(gdp_shock)
    ir_shock = float(ir_shock)
    re_shock = float(re_shock)
    unemp_shock = float(unemp_shock)

    # Load industry sensitivities
    sensitivities = {
        s.sector_code: {
            'beta_gdp': float(s.beta_gdp),
            'beta_ir': float(s.beta_interest),
            'beta_re': float(s.beta_real_estate),
            'name_vn': s.sector_name_vn
        }
        for s in IndustrySensitivity.objects.all()
    }

    # Fallback sensitivities if empty
    default_sens = {'beta_gdp': 1.2, 'beta_ir': 1.3, 'beta_re': -0.8, 'name_vn': 'Khác'}

    contract_results = []
    
    total_ead = 0.0
    total_baseline_ecl = 0.0
    total_stressed_ecl = 0.0
    
    stage_counts_pre = {1: 0, 2: 0, 3: 0}
    stage_counts_post = {1: 0, 2: 0, 3: 0}
    
    sector_summary = {}

    for loan in loan_contracts:
        ead = float(loan.original_ead)
        pd_base = float(loan.baseline_pd)
        lgd_base = float(loan.baseline_lgd)
        stage_base = loan.initial_stage
        tenor_years = max(1.0, float(loan.remaining_tenor_months) / 12.0)
        eir = float(loan.interest_rate)
        collateral_val = float(loan.collateral_value)
        haircut_base = float(loan.baseline_haircut)
        sector = loan.industry_sector
        
        total_ead += ead
        stage_counts_pre[stage_base] += 1

        # 1. Macro regression impact Z_j on PD logit with 4 channels
        sens = sensitivities.get(sector, default_sens)
        # Standard econometric transmission
        beta_unemp = 1.3 if sector in ['CONSUMER_LOAN', 'WHOLESALE_RETAIL', 'RETAIL'] else 1.0
        z_macro = (
            sens['beta_gdp'] * (-gdp_shock * 8.0) +
            sens['beta_ir'] * (ir_shock * 10.0) +
            abs(sens['beta_re']) * (-re_shock * 4.0) +
            beta_unemp * (unemp_shock * 6.0)
        )
        z_macro = max(-0.5, min(2.5, z_macro))  # Bound macro shock index

        # Logistic transformation for Stressed PD
        pd_safe = max(0.0001, min(0.9999, pd_base))
        logit_base = math.log(pd_safe / (1.0 - pd_safe))
        logit_stressed = logit_base + z_macro
        pd_stressed = 1.0 / (1.0 + math.exp(-logit_stressed))
        pd_stressed = max(0.001, min(0.950, round(pd_stressed, 5)))

        # 2. Stressed LGD calculation with collateral devaluation and haircut
        collateral_stressed = collateral_val * max(0.40, 1.0 + re_shock)
        haircut_stressed = min(0.80, haircut_base + abs(re_shock) * 0.20)
        recovery_stressed = (collateral_stressed * (1.0 - haircut_stressed)) / max(1.0, ead)
        lgd_stressed = max(0.180, min(0.900, round(1.0 - recovery_stressed, 4)))

        # 3. SICR and Stage Migration Logic (IFRS 9 - Chuẩn Mục 5.3.3 Báo cáo)
        # SICR: Khoản vay Stage 1 chuyển sang Stage 2 khi PD sốc >= 2 * PD0 và PD sốc >= 3.5%
        # Khoản vay chuyển sang Stage 3 khi quá hạn >= 90 ngày
        is_sicr = False
        if stage_base == 3:
            stage_stressed = 3
        elif loan.overdue_days >= 90:
            stage_stressed = 3
            if stage_base != 3:
                is_sicr = True
        elif stage_base == 1:
            rel_increase = pd_stressed / pd_safe
            if (rel_increase >= 2.0 and pd_stressed >= 0.035) or loan.overdue_days >= 30:
                stage_stressed = 2
                is_sicr = True
            else:
                stage_stressed = 1
        else:  # stage_base == 2
            if pd_stressed >= 0.35 and loan.overdue_days >= 60:
                stage_stressed = 3
                is_sicr = True
            else:
                stage_stressed = 2

        stage_counts_post[stage_stressed] += 1

        # 4. ECL Calculation
        # Baseline ECL
        if stage_base == 1:
            ecl_base = pd_base * lgd_base * ead
        elif stage_base == 2:
            pd_lifetime_base = 1.0 - ((1.0 - pd_base) ** min(5.0, tenor_years))
            df = 1.0 / ((1.0 + eir) ** min(2.0, tenor_years))
            ecl_base = pd_lifetime_base * lgd_base * ead * df
        else: # Stage 3
            ecl_base = 1.0 * lgd_base * ead

        # Stressed ECL
        if stage_stressed == 1:
            ecl_stressed = pd_stressed * lgd_stressed * ead
        elif stage_stressed == 2:
            pd_lifetime_stressed = 1.0 - ((1.0 - pd_stressed) ** min(5.0, tenor_years))
            df = 1.0 / ((1.0 + eir) ** min(2.0, tenor_years))
            ecl_stressed = pd_lifetime_stressed * lgd_stressed * ead * df
        else: # Stage 3
            ecl_stressed = 1.0 * lgd_stressed * ead

        ecl_base = round(ecl_base, 2)
        ecl_stressed = round(ecl_stressed, 2)
        delta_provision = round(max(0.0, ecl_stressed - ecl_base), 2)

        total_baseline_ecl += ecl_base
        total_stressed_ecl += ecl_stressed

        # Track sector breakdown
        sec_name = sens['name_vn']
        if sec_name not in sector_summary:
            sector_summary[sec_name] = {
                'sector_code': sector,
                'sector_name': sec_name,
                'ead': 0.0,
                'baseline_ecl': 0.0,
                'stressed_ecl': 0.0,
                'delta_provision': 0.0,
                'contract_count': 0
            }
        sector_summary[sec_name]['ead'] += ead
        sector_summary[sec_name]['baseline_ecl'] += ecl_base
        sector_summary[sec_name]['stressed_ecl'] += ecl_stressed
        sector_summary[sec_name]['delta_provision'] += delta_provision
        sector_summary[sec_name]['contract_count'] += 1

        contract_results.append({
            'contract_id': loan.contract_id,
            'customer_name': loan.customer_name,
            'customer_segment': loan.customer_segment,
            'industry_sector': sector,
            'sector_name_vn': sec_name,
            'original_ead': ead,
            'collateral_type': loan.collateral_type,
            'collateral_value': round(collateral_stressed, 2),
            'internal_rating': loan.internal_rating,
            'baseline_pd': pd_base,
            'stressed_pd': pd_stressed,
            'baseline_lgd': lgd_base,
            'stressed_lgd': lgd_stressed,
            'baseline_stage': stage_base,
            'stressed_stage': stage_stressed,
            'is_sicr': is_sicr,
            'baseline_ecl': ecl_base,
            'stressed_ecl': ecl_stressed,
            'delta_provision': delta_provision,
        })

    total_delta_provision = total_stressed_ecl - total_baseline_ecl

    # 5. Bank-wide Capital Adequacy Ratio (CAR) calculation
    # Realistic bank baseline figures (scaled to portfolio size for consistent percentage impact):
    # Tier 1 = 14% of total EAD, Tier 2 = 3.5% of total EAD, RWA = 95% of total EAD
    baseline_tier1 = total_ead * 0.145
    baseline_tier2 = total_ead * 0.035
    baseline_rwa = total_ead * 0.920
    baseline_car = (baseline_tier1 + baseline_tier2) / baseline_rwa

    # Stressed Capital: Delta provision directly deducts Tier 1 Capital
    stressed_tier1 = max(0.0, baseline_tier1 - total_delta_provision)
    # Stressed RWA increases because downgraded loans have higher risk weights (Basel II/III standard)
    migrated_stage2_ead = sum(r['original_ead'] for r in contract_results if r['baseline_stage'] == 1 and r['stressed_stage'] == 2)
    migrated_stage3_ead = sum(r['original_ead'] for r in contract_results if r['baseline_stage'] != 3 and r['stressed_stage'] == 3)
    rwa_increase = (migrated_stage2_ead * 0.50) + (migrated_stage3_ead * 1.00)
    stressed_rwa = baseline_rwa + rwa_increase
    stressed_car = (stressed_tier1 + baseline_tier2) / stressed_rwa
    car_change_bps = (stressed_car - baseline_car) * 10000.0

    return {
        'contract_results': contract_results,
        'summary': {
            'total_ead': round(total_ead, 2),
            'total_baseline_ecl': round(total_baseline_ecl, 2),
            'total_stressed_ecl': round(total_stressed_ecl, 2),
            'total_delta_provision': round(total_delta_provision, 2),
            'baseline_car': round(baseline_car * 100.0, 2),
            'stressed_car': round(stressed_car * 100.0, 2),
            'car_change_bps': round(car_change_bps, 1),
            'minimum_regulatory_car': 8.0,
            'is_capital_adequate': stressed_car >= 0.080,
            'baseline_tier1': round(baseline_tier1, 2),
            'stressed_tier1': round(stressed_tier1, 2),
            'baseline_rwa': round(baseline_rwa, 2),
            'stressed_rwa': round(stressed_rwa, 2),
            'npl_ratio_pre': round((stage_counts_pre[3] / max(1, len(loan_contracts))) * 100.0, 2),
            'npl_ratio_post': round((stage_counts_post[3] / max(1, len(loan_contracts))) * 100.0, 2),
        },
        'stage_migration': {
            'pre_stress': {
                1: stage_counts_pre[1], 2: stage_counts_pre[2], 3: stage_counts_pre[3],
                '1': stage_counts_pre[1], '2': stage_counts_pre[2], '3': stage_counts_pre[3],
                'stage_1': stage_counts_pre[1], 'stage_2': stage_counts_pre[2], 'stage_3': stage_counts_pre[3]
            },
            'post_stress': {
                1: stage_counts_post[1], 2: stage_counts_post[2], 3: stage_counts_post[3],
                '1': stage_counts_post[1], '2': stage_counts_post[2], '3': stage_counts_post[3],
                'stage_1': stage_counts_post[1], 'stage_2': stage_counts_post[2], 'stage_3': stage_counts_post[3]
            },
            'sicr_count': sum(1 for r in contract_results if r['is_sicr']),
            'migrated_to_stage2': sum(1 for r in contract_results if r['baseline_stage'] == 1 and r['stressed_stage'] == 2),
            'migrated_to_stage3': sum(1 for r in contract_results if r['baseline_stage'] != 3 and r['stressed_stage'] == 3),
        },
        'sector_breakdown': list(sector_summary.values())
    }
