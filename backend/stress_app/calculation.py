import math
from decimal import Decimal
from .models import LoanAccount, IndustrySensitivity, MacroScenario


def calculate_stress_test(
    loan_contracts,
    gdp_shock,
    ir_shock,
    re_shock,
    unemp_shock=0.0,
    recovery_time_years=None,
    scenario_weight=1.0
):
    """
    Core mathematical engine for IFRS 9 Credit Stress Testing.
    Tuân thủ chặt chẽ đặc tả nghiệp vụ theo IFRS 9, Thông tư 14/2025/TT-NHNN và Báo cáo kiểm định:
    
    1. PD sốc (Probability of Default):
       - Hàm hồi quy Logit đa biến với các hệ số nhạy cảm vĩ mô tường minh (COEFF_GDP, COEFF_IR, COEFF_RE, COEFF_UNEMP).
       - Ở kịch bản cơ sở (shock = 0), PD sốc = PD0.
    
    2. LGD sốc (Loss Given Default):
       - LGD = 1 - PV(R_net) / EAD
       - PV(R_net) = [Giá trị TSBĐ sau sốc * (1 - Chi phí thanh lý Haircut)] / (1 + EIR)^t_rec
       - t_rec: Thời gian phát mại thu hồi tài sản (1.5 - 3.0 năm theo kịch bản vĩ mô).
       - TSBĐ BĐS chịu 100% sốc BĐS; TSBĐ phi BĐS (máy móc, hàng hóa) chịu 50% mức sốc khi sốc âm.
       - Sàn LGD tối thiểu 10% (0.10) theo Thông tư 14/2025/TT-NHNN.
       - Đảm bảo tính nhất quán: Kịch bản Cơ sở cho Delta PS = 0 tuyệt đối.
    
    3. Phân tầng rủi ro & Tiêu chí SICR (Staging Logic):
       - Stage 1 -> Stage 2 (SICR): Khi PD sốc >= 2.0 * PD0 VÀ PD sốc >= 3.0% (0.030), HOẶC quá hạn >= 30 ngày.
       - Stage 3: Khi quá hạn >= 90 ngày hoặc đã thuộc Stage 3 từ trước.
       - Bỏ các quy tắc tự chế ngoài đặc tả (như 35%/60 ngày).
    
    4. Kỳ tính ECL (T) & Hệ số chiết khấu (DF):
       - Stage 1: T = min(1.0 năm, kỳ hạn còn lại); ECL 12 tháng.
       - Stage 2 & Stage 3: T = kỳ hạn còn lại (năm), KHÔNG CÓ TRẦN 5 NĂM.
       - Hệ số chiết khấu: DF = 1 / (1 + EIR)^(T/2) cho Stage 1 & 2; DF = 1.0 cho Stage 3.
       - PD tích lũy trọn đời: PD_lifetime = 1 - (1 - PD sốc)^T.
    
    5. NPL kỳ vọng & Tỷ lệ bao phủ LLR (Expected NPL & LLR Ratio):
       - NPL kỳ vọng (theo giá trị tiền VNĐ) = [Dư nợ Stage 3 + Tổng(PD sốc * EAD của các khoản còn lại)] / Tổng EAD.
       - LLR = [Tổng dự phòng ECL sau sốc / Tổng nợ xấu kỳ vọng] * 100%.
    """
    gdp_shock = float(gdp_shock)
    ir_shock = float(ir_shock)
    re_shock = float(re_shock)
    unemp_shock = float(unemp_shock)
    scenario_weight = float(scenario_weight) if scenario_weight else 1.0

    # Kiểm tra kịch bản có phải là kịch bản Cơ sở tuyệt đối (không có sốc)
    is_zero_shock = (
        abs(gdp_shock) < 1e-6 and
        abs(ir_shock) < 1e-6 and
        abs(re_shock) < 1e-6 and
        abs(unemp_shock) < 1e-6
    )

    # 1. Tham số cấu hình mô hình lan truyền vĩ mô (Macro Transmission Coefficients)
    # Các hệ số giả định kinh tế lượng phản ánh độ co giãn vĩ mô
    COEFF_GDP = 8.0      # Độ nhạy với sụt giảm tăng trưởng kinh tế (GDP)
    COEFF_IR = 10.0      # Độ nhạy với gia tăng mặt bằng lãi suất điều hành (IR)
    COEFF_RE = 4.0       # Độ nhạy với suy giảm chỉ số giá thị trường BĐS (RE)
    COEFF_UNEMP = 6.0    # Độ nhạy với gia tăng tỷ lệ thất nghiệp (Unemp)

    # Thời gian phát mại tài sản bảo đảm t_rec (năm)
    if recovery_time_years and float(recovery_time_years) > 0:
        t_rec_scenario = float(recovery_time_years)
    elif is_zero_shock:
        t_rec_scenario = 1.5
    else:
        # Thời gian thanh lý kéo dài từ 1.5 năm (cơ sở) đến 3.0 năm (khủng hoảng)
        t_rec_scenario = min(3.5, 1.5 + 2.5 * abs(re_shock) + 10.0 * max(0.0, -gdp_shock))

    # Tải ma trận hệ số độ nhạy ngành (Sector Sensitivities)
    sensitivities = {
        s.sector_code: {
            'beta_gdp': float(s.beta_gdp),
            'beta_ir': float(s.beta_interest),
            'beta_re': float(s.beta_real_estate),
            'name_vn': s.sector_name_vn
        }
        for s in IndustrySensitivity.objects.all()
    }
    default_sens = {'beta_gdp': 1.2, 'beta_ir': 1.3, 'beta_re': -0.8, 'name_vn': 'Khác'}

    contract_results = []
    
    total_ead = 0.0
    total_baseline_ecl = 0.0
    total_stressed_ecl = 0.0
    
    stage_counts_pre = {1: 0, 2: 0, 3: 0}
    stage_counts_post = {1: 0, 2: 0, 3: 0}
    
    sector_summary = {}

    for loan in loan_contracts:
        ead = float(getattr(loan, 'original_ead', getattr(loan, 'ead', 0.0)))
        pd_base = float(getattr(loan, 'baseline_pd', getattr(loan, 'pd_base', 0.01)))
        stage_base = int(getattr(loan, 'initial_stage', getattr(loan, 'current_stage', 1)))
        
        if hasattr(loan, 'remaining_tenor_months'):
            tenor_years = max(0.25, float(loan.remaining_tenor_months) / 12.0)
        elif hasattr(loan, 'remaining_term'):
            tenor_years = max(0.25, float(loan.remaining_term))
        else:
            tenor_years = 1.0

        eir = float(getattr(loan, 'interest_rate', 0.10))
        
        if hasattr(loan, 'customer') and loan.customer:
            sector = loan.customer.sector_code
            customer_name = loan.customer.customer_name
            customer_segment = loan.customer.segment
            internal_rating = loan.customer.internal_rating or 'BBB'
        else:
            sector = getattr(loan, 'industry_sector', 'MANUFACTURING')
            customer_name = getattr(loan, 'customer_name', 'Khách hàng')
            customer_segment = getattr(loan, 'customer_segment', 'CORPORATE')
            internal_rating = getattr(loan, 'internal_rating', 'BBB')

        overdue_days = int(getattr(loan, 'days_past_due', getattr(loan, 'overdue_days', 0)))
        contract_id = str(getattr(loan, 'loan_id', getattr(loan, 'contract_id', 'LN-0001')))

        # Tài sản bảo đảm (từ LoanCollateral -> Collateral)
        if hasattr(loan, 'collateral_allocations') and loan.collateral_allocations.exists():
            allocs = list(loan.collateral_allocations.all())
            collateral_val = sum(float(a.allocated_value) for a in allocs)
            primary_col = allocs[0].collateral
            collateral_type = primary_col.collateral_type
            haircut_base = float(primary_col.liquidation_cost_rate)
        else:
            collateral_val = float(getattr(loan, 'collateral_value', 0.0))
            collateral_type = getattr(loan, 'collateral_type', 'Không')
            haircut_base = float(getattr(loan, 'baseline_haircut', 0.3000))
        
        total_ead += ead
        stage_counts_pre[stage_base] += 1

        sens = sensitivities.get(sector, default_sens)
        beta_unemp = 1.3 if sector in ['CONSUMER_LOAN', 'WHOLESALE_RETAIL', 'RETAIL'] else 1.0

        # ----------------------------------------------------------------------
        # 1. TÍNH TOÁN PD SỐC (PROBABILITY OF DEFAULT)
        # ----------------------------------------------------------------------
        pd_safe = max(0.0001, min(0.9999, pd_base))
        if is_zero_shock:
            pd_stressed = pd_safe
            z_macro = 0.0
        else:
            z_macro = (
                sens['beta_gdp'] * (-gdp_shock * COEFF_GDP) +
                sens['beta_ir'] * (ir_shock * COEFF_IR) +
                abs(sens['beta_re']) * (-re_shock * COEFF_RE) +
                beta_unemp * (unemp_shock * COEFF_UNEMP)
            )
            z_macro = max(-0.5, min(2.5, z_macro))
            logit_base = math.log(pd_safe / (1.0 - pd_safe))
            logit_stressed = logit_base + z_macro
            pd_stressed = 1.0 / (1.0 + math.exp(-logit_stressed))
            pd_stressed = max(0.001, min(0.990, round(pd_stressed, 5)))

        # ----------------------------------------------------------------------
        # 2. TÍNH TOÁN LGD VÀ ĐỊNH GIÁ LẠI TSBĐ (LOSS GIVEN DEFAULT)
        # LGD = 1 - PV(R_net) / EAD theo Thông tư 14/2025/TT-NHNN
        # ----------------------------------------------------------------------
        coll_type = str(collateral_type or '').upper()
        is_re = any(k in coll_type for k in ['BẤT ĐỘNG SẢN', 'BĐS', 'NHÀ', 'ĐẤT', 'REAL_ESTATE', 'PROPERTY'])
        is_unsecured = any(k in coll_type for k in ['KHÔNG', 'TÍN CHẤP', 'NONE', 'UNSECURED']) or collateral_val <= 0

        # LGD cơ sở tại điểm ban đầu (t_rec = 1.5 năm, shock = 0)
        if is_unsecured:
            lgd_base = 0.5500
        else:
            # PV thu hồi ròng cơ sở
            pv_base = (collateral_val * (1.0 - haircut_base)) / ((1.0 + eir) ** 1.5)
            recovery_base = min(pv_base, ead) / max(1.0, ead)
            lgd_base = max(0.100, min(0.900, round(1.0 - recovery_base, 4)))

        # LGD sau sốc căng thẳng
        if is_zero_shock:
            lgd_stressed = lgd_base
            collateral_stressed = collateral_val
        else:
            if is_unsecured:
                # Khoản vay không TSBĐ: LGD tăng thêm theo mức độ căng thẳng
                unsec_increase = min(0.20, abs(re_shock) * 0.4 + max(0.0, -gdp_shock) * 2.0)
                lgd_stressed = min(0.900, round(0.5500 + unsec_increase, 4))
                collateral_stressed = 0.0
            else:
                # TSBĐ BĐS chịu 100% mức sốc BĐS; TSBĐ phi BĐS (máy móc, hàng hóa) chịu 50% mức sốc âm
                shock_rate = re_shock if is_re else (0.5 * min(0.0, re_shock))
                collateral_stressed = collateral_val * max(0.20, 1.0 + shock_rate)
                
                # Chi phí xử lý tăng nhẹ khi thị trường đóng băng
                haircut_stressed = min(0.60, haircut_base + abs(shock_rate) * 0.10)
                
                # Chiết khấu dòng tiền thu hồi ròng qua thời gian thanh lý t_rec
                pv_stressed = (collateral_stressed * (1.0 - haircut_stressed)) / ((1.0 + eir) ** t_rec_scenario)
                recovery_stressed = min(pv_stressed, ead) / max(1.0, ead)
                
                # Sàn LGD tối thiểu 10% (0.100) theo Thông tư 14
                lgd_stressed = max(0.100, min(0.900, round(1.0 - recovery_stressed, 4)))

        # ----------------------------------------------------------------------
        # 3. PHÂN TẦNG RỦI RO & SICR (IFRS 9 STAGING)
        # ----------------------------------------------------------------------
        is_sicr = False
        if stage_base == 3 or overdue_days >= 90:
            stage_stressed = 3
            if stage_base != 3:
                is_sicr = True
        elif stage_base == 1:
            rel_increase = pd_stressed / pd_safe
            # Ngưỡng SICR chuẩn hóa: PD tăng >= 2.0 lần VÀ PD sốc >= 3.0% (0.030), hoặc quá hạn >= 30 ngày
            if (rel_increase >= 2.0 and pd_stressed >= 0.030) or overdue_days >= 30:
                stage_stressed = 2
                is_sicr = True
            else:
                stage_stressed = 1
        else:  # stage_base == 2
            # Đang ở Stage 2: Chỉ chuyển lên Stage 3 khi quá hạn >= 90 ngày
            if overdue_days >= 90:
                stage_stressed = 3
                is_sicr = True
            else:
                stage_stressed = 2

        stage_counts_post[stage_stressed] += 1

        # ----------------------------------------------------------------------
        # 4. TÍNH TOÁN TỔN THẤT TÍN DỤNG DỰ KIẾN ECL (EXPECTED CREDIT LOSS)
        # ECL = PD_T * LGD * EAD * DF
        # Bỏ trần 5 năm, dùng đúng kỳ hạn còn lại
        # ----------------------------------------------------------------------
        # A. Baseline ECL
        if stage_base == 1:
            T_base = min(1.0, tenor_years)
            df_base = 1.0 / ((1.0 + eir) ** (T_base / 2.0))
            pd_t_base = 1.0 - ((1.0 - pd_safe) ** T_base)
            ecl_base = pd_t_base * lgd_base * ead * df_base
        elif stage_base == 2:
            T_base = tenor_years  # Không có trần 5 năm
            df_base = 1.0 / ((1.0 + eir) ** (T_base / 2.0))
            pd_t_base = 1.0 - ((1.0 - pd_safe) ** T_base)
            ecl_base = pd_t_base * lgd_base * ead * df_base
        else:  # Stage 3
            df_base = 1.0
            pd_t_base = 1.0
            ecl_base = 1.0 * lgd_base * ead

        # B. Stressed ECL
        if stage_stressed == 1:
            T_str = min(1.0, tenor_years)
            df_str = 1.0 / ((1.0 + eir) ** (T_str / 2.0))
            pd_t_str = 1.0 - ((1.0 - pd_stressed) ** T_str)
            ecl_stressed = pd_t_str * lgd_stressed * ead * df_str
        elif stage_stressed == 2:
            T_str = tenor_years  # Không có trần 5 năm
            df_str = 1.0 / ((1.0 + eir) ** (T_str / 2.0))
            pd_t_str = 1.0 - ((1.0 - pd_stressed) ** T_str)
            ecl_stressed = pd_t_str * lgd_stressed * ead * df_str
        else:  # Stage 3
            df_str = 1.0
            pd_t_str = 1.0
            ecl_stressed = 1.0 * lgd_stressed * ead

        ecl_base = round(ecl_base, 2)
        ecl_stressed = round(ecl_stressed, 2)
        
        # Nếu ở kịch bản Cơ sở (zero shock), ép Delta PS = 0 tuyệt đối
        if is_zero_shock:
            ecl_stressed = ecl_base
            delta_provision = 0.0
        else:
            delta_provision = round(max(0.0, ecl_stressed - ecl_base), 2)

        total_baseline_ecl += ecl_base
        total_stressed_ecl += ecl_stressed

        # Tổng hợp theo ngành kinh tế
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
            'contract_id': contract_id,
            'customer_name': customer_name,
            'customer_segment': customer_segment,
            'industry_sector': sector,
            'sector_name_vn': sec_name,
            'original_ead': ead,
            'collateral_type': collateral_type,
            'collateral_value': round(collateral_stressed, 2),
            'internal_rating': internal_rating,
            'baseline_pd': pd_base,
            'stressed_pd': pd_stressed,
            'baseline_lgd': lgd_base,
            'stressed_lgd': lgd_stressed,
            'baseline_stage': stage_base,
            'stressed_stage': stage_stressed,
            'discount_factor': round(df_str, 6),
            'is_sicr': is_sicr,
            'baseline_ecl': ecl_base,
            'stressed_ecl': ecl_stressed,
            'delta_provision': delta_provision,
        })

    total_delta_provision = total_stressed_ecl - total_baseline_ecl
    if is_zero_shock:
        total_delta_provision = 0.0

    # --------------------------------------------------------------------------
    # 5. TÍNH TOÁN NPL KỲ VỌNG VÀ TỶ LỆ BAO PHỦ LLR (CHUẨN NGHIỆP VỤ BÁO CÁO)
    # NPL kỳ vọng = [Dư nợ Stage 3 + Tổng(PD sốc * EAD khoản còn lại)] / Tổng EAD
    # --------------------------------------------------------------------------
    # Baseline NPL
    ead_stage3_pre = sum(r['original_ead'] for r in contract_results if r['baseline_stage'] == 3)
    ead_performing_pre_weighted = sum(r['baseline_pd'] * r['original_ead'] for r in contract_results if r['baseline_stage'] != 3)
    expected_npl_pre = ead_stage3_pre + ead_performing_pre_weighted
    npl_ratio_expected_pre = round((expected_npl_pre / max(1.0, total_ead)) * 100.0, 2)
    npl_ratio_accounting_pre = round((ead_stage3_pre / max(1.0, total_ead)) * 100.0, 2)

    # Stressed NPL
    ead_stage3_post = sum(r['original_ead'] for r in contract_results if r['stressed_stage'] == 3)
    ead_performing_post_weighted = sum(r['stressed_pd'] * r['original_ead'] for r in contract_results if r['stressed_stage'] != 3)
    expected_npl_post = ead_stage3_post + ead_performing_post_weighted
    npl_ratio_expected_post = round((expected_npl_post / max(1.0, total_ead)) * 100.0, 2)
    npl_ratio_accounting_post = round((ead_stage3_post / max(1.0, total_ead)) * 100.0, 2)

    # LLR (Tỷ lệ bao phủ nợ xấu kỳ vọng): Tổng ECL / Tổng nợ xấu kỳ vọng
    llr_expected_post = round((total_stressed_ecl / max(1.0, expected_npl_post)) * 100.0, 2)
    llr_accounting_post = round((total_stressed_ecl / max(1.0, ead_stage3_post)) * 100.0, 2) if ead_stage3_post > 0 else 100.0

    # --------------------------------------------------------------------------
    # 6. TÁC ĐỘNG TỶ LỆ AN TOÀN VỐN (CAR - THÔNG TƯ 41/2016/TT-NHNN)
    # --------------------------------------------------------------------------
    baseline_tier1 = total_ead * 0.145
    baseline_tier2 = total_ead * 0.035
    baseline_rwa = total_ead * 0.920
    baseline_car = (baseline_tier1 + baseline_tier2) / baseline_rwa

    # Vốn cấp 1 sau sốc: Trích lập bổ sung khấu trừ trực tiếp vào Vốn Cấp 1
    stressed_tier1 = max(0.0, baseline_tier1 - total_delta_provision)
    
    # RWA sau sốc gia tăng do các khoản bị chuyển Stage (rủi ro cao hơn)
    migrated_stage2_ead = sum(r['original_ead'] for r in contract_results if r['baseline_stage'] == 1 and r['stressed_stage'] == 2)
    migrated_stage3_ead = sum(r['original_ead'] for r in contract_results if r['baseline_stage'] != 3 and r['stressed_stage'] == 3)
    rwa_increase = (migrated_stage2_ead * 0.50) + (migrated_stage3_ead * 1.00)
    stressed_rwa = baseline_rwa + rwa_increase
    stressed_car = (stressed_tier1 + baseline_tier2) / stressed_rwa
    car_change_bps = (stressed_car - baseline_car) * 10000.0

    # ECL có trọng số theo kịch bản (scenario_weight)
    weighted_stressed_ecl = round(total_stressed_ecl * scenario_weight, 2)

    return {
        'contract_results': contract_results,
        'summary': {
            'total_ead': round(total_ead, 2),
            'total_baseline_ecl': round(total_baseline_ecl, 2),
            'total_stressed_ecl': round(total_stressed_ecl, 2),
            'weighted_stressed_ecl': weighted_stressed_ecl,
            'scenario_weight': scenario_weight,
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
            # Chỉ số NPL kỳ vọng theo giá trị tiền (VNĐ)
            'npl_ratio_pre': npl_ratio_expected_pre,
            'npl_ratio_post': npl_ratio_expected_post,
            'npl_ratio_accounting_pre': npl_ratio_accounting_pre,
            'npl_ratio_accounting_post': npl_ratio_accounting_post,
            'expected_npl_amount': round(expected_npl_post, 2),
            'accounting_npl_amount': round(ead_stage3_post, 2),
            # Chỉ số bao phủ nợ xấu LLR (%)
            'llr_expected': llr_expected_post,
            'llr_accounting': llr_accounting_post,
            'recovery_time_years': round(t_rec_scenario, 2),
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
