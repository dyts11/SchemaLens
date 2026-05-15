"""
column_aliases.py

Curated S2 (abbreviated) and S3 (descriptive) column-name mappings for every
BIRD dev database.

Design rules:
  - S3  : full, self-explanatory snake_case English words/phrases.  Where a
          column is a widely known abbreviation (NSLP, NCES, AST/ALT, MTGO,
          …), S3 uses the spelled-out form; codes with no clear public meaning
          (e.g. IRC in CA FRPM, PIC/TAT in this lab export) stay as in the
          source unless documented.
  - S2  : short abbreviations that a developer would recognise (e.g. cust_id,
          dept_nm, acct_id, dt, amt).
  - S1  : generated automatically (col_a, col_b …) — not stored here.
  - S4  : identical to S3; the description suffix is added by schema_builder.

Structure:
    ALIASES[db_id][original_col_name] = {"s2": ..., "s3": ...}

Fallback (column not in ALIASES): schema_builder uses the original name for
both S2 and S3.  This is intentional for short, neutral names like "id",
"date", "type", "name", "status", "url", "year", "text" — they need no
transformation.
"""

ALIASES: dict = {

    # =========================================================================
    # california_schools
    # =========================================================================
    # frpm  — original names are descriptive (S3); create S2 abbreviations
    # satscores — original names are abbreviated (S2); create S3 expansions
    # schools   — mixed; create both directions
    # =========================================================================
    "california_schools": {
        # ----- frpm table (original ≈ S3; add S2 abbreviations) -----
        "CDSCode":                                      {"s2": "cds_cd",        "s3": "county_district_school_code"},
        "Academic Year":                                {"s2": "acad_yr",       "s3": "academic_year"},
        "County Code":                                  {"s2": "cnty_cd",       "s3": "county_code"},
        "District Code":                                {"s2": "dist_cd",       "s3": "district_code"},
        "School Code":                                  {"s2": "sch_cd",        "s3": "school_code"},
        "County Name":                                  {"s2": "cnty_nm",       "s3": "county_name"},
        "District Name":                                {"s2": "dist_nm",       "s3": "district_name"},
        "School Name":                                  {"s2": "sch_nm",        "s3": "school_name"},
        "District Type":                                {"s2": "dist_type",     "s3": "district_type"},
        "School Type":                                  {"s2": "sch_type",      "s3": "school_type"},
        "Educational Option Type":                      {"s2": "edu_opt_type",  "s3": "educational_option_type"},
        "NSLP Provision Status":                        {"s2": "nslp_status",   "s3": "national_school_lunch_program_provision_status"},
        "Charter School (Y/N)":                         {"s2": "is_charter",    "s3": "is_charter_school"},
        "Charter School Number":                        {"s2": "charter_num",   "s3": "charter_school_number"},
        "Charter Funding Type":                         {"s2": "charter_fund",  "s3": "charter_funding_type"},
        "IRC":                                          {"s2": "irc",           "s3": "irc"},
        "Low Grade":                                    {"s2": "low_grd",       "s3": "low_grade"},
        "High Grade":                                   {"s2": "high_grd",      "s3": "high_grade"},
        "Enrollment (K-12)":                            {"s2": "enroll_k12",    "s3": "enrollment_k12"},
        "Free Meal Count (K-12)":                       {"s2": "free_meal_k12", "s3": "free_meal_count_k12"},
        "Percent (%) Eligible Free (K-12)":             {"s2": "pct_free_k12",  "s3": "percent_eligible_free_k12"},
        "FRPM Count (K-12)":                            {"s2": "frpm_k12",      "s3": "free_or_reduced_price_meal_count_k12"},
        "Percent (%) Eligible FRPM (K-12)":             {"s2": "pct_frpm_k12",  "s3": "percent_eligible_free_or_reduced_price_meal_k12"},
        "Enrollment (Ages 5-17)":                       {"s2": "enroll_5_17",   "s3": "enrollment_ages_5_17"},
        "Free Meal Count (Ages 5-17)":                  {"s2": "free_meal_5_17","s3": "free_meal_count_ages_5_17"},
        "Percent (%) Eligible Free (Ages 5-17)":        {"s2": "pct_free_5_17", "s3": "percent_eligible_free_ages_5_17"},
        "FRPM Count (Ages 5-17)":                       {"s2": "frpm_5_17",     "s3": "free_or_reduced_price_meal_count_ages_5_17"},
        "Percent (%) Eligible FRPM (Ages 5-17)":        {"s2": "pct_frpm_5_17", "s3": "percent_eligible_free_or_reduced_price_meal_ages_5_17"},
        "2013-14 CALPADS Fall 1 Certification Status":  {"s2": "calpads_cert",  "s3": "california_longitudinal_pupil_achievement_data_system_fall_1_certification_status"},
        # ----- satscores table (original ≈ S2; expand to S3) -----
        "cds":          {"s2": "cds",           "s3": "county_district_school_code"},
        "rtype":        {"s2": "rtype",          "s3": "record_type"},
        "sname":        {"s2": "sname",          "s3": "school_name"},
        "dname":        {"s2": "dname",          "s3": "district_name"},
        "cname":        {"s2": "cname",          "s3": "county_name"},
        "enroll12":     {"s2": "enroll12",       "s3": "enrollment_grade_12"},
        "NumTstTakr":   {"s2": "num_tst_takr",   "s3": "number_test_takers"},
        "AvgScrRead":   {"s2": "avg_scr_read",   "s3": "average_score_reading"},
        "AvgScrMath":   {"s2": "avg_scr_math",   "s3": "average_score_math"},
        "AvgScrWrite":  {"s2": "avg_scr_write",  "s3": "average_score_writing"},
        "NumGE1500":    {"s2": "num_ge_1500",     "s3": "number_scores_1500_or_above"},
        # ----- schools table (mixed; map everything) -----
        "NCESDist":     {"s2": "nces_dist",      "s3": "national_center_for_education_statistics_district_id"},
        "NCESSchool":   {"s2": "nces_sch",       "s3": "national_center_for_education_statistics_school_id"},
        "StatusType":   {"s2": "status_type",    "s3": "status_type"},
        "StreetAbr":    {"s2": "street_abr",     "s3": "street_abbreviated"},
        "MailStreet":   {"s2": "mail_street",    "s3": "mailing_street"},
        "MailStrAbr":   {"s2": "mail_str_abr",   "s3": "mailing_street_abbreviated"},
        "MailCity":     {"s2": "mail_city",      "s3": "mailing_city"},
        "MailZip":      {"s2": "mail_zip",       "s3": "mailing_zip_code"},
        "MailState":    {"s2": "mail_state",     "s3": "mailing_state"},
        "Ext":          {"s2": "ext",            "s3": "phone_extension"},
        "OpenDate":     {"s2": "open_dt",        "s3": "open_date"},
        "ClosedDate":   {"s2": "close_dt",       "s3": "closed_date"},
        "CharterNum":   {"s2": "charter_num",    "s3": "charter_number"},
        "FundingType":  {"s2": "fund_type",      "s3": "funding_type"},
        "DOC":          {"s2": "doc",            "s3": "district_ownership_code"},
        "DOCType":      {"s2": "doc_type",       "s3": "district_ownership_type"},
        "SOC":          {"s2": "soc",            "s3": "school_ownership_code"},
        "SOCType":      {"s2": "soc_type",       "s3": "school_ownership_type"},
        "EdOpsCode":    {"s2": "ed_ops_cd",      "s3": "educational_option_code"},
        "EdOpsName":    {"s2": "ed_ops_nm",      "s3": "educational_option_name"},
        "EILCode":      {"s2": "eil_cd",         "s3": "instruction_level_code"},
        "EILName":      {"s2": "eil_nm",         "s3": "instruction_level_name"},
        "GSoffered":    {"s2": "gs_offered",     "s3": "grade_span_offered"},
        "GSserved":     {"s2": "gs_served",      "s3": "grade_span_served"},
        "LastUpdate":   {"s2": "last_upd",       "s3": "last_update"},
        "AdmFName1":    {"s2": "adm_fname1",     "s3": "admin_first_name_1"},
        "AdmLName1":    {"s2": "adm_lname1",     "s3": "admin_last_name_1"},
        "AdmEmail1":    {"s2": "adm_email1",     "s3": "admin_email_1"},
        "AdmFName2":    {"s2": "adm_fname2",     "s3": "admin_first_name_2"},
        "AdmLName2":    {"s2": "adm_lname2",     "s3": "admin_last_name_2"},
        "AdmEmail2":    {"s2": "adm_email2",     "s3": "admin_email_2"},
        "AdmFName3":    {"s2": "adm_fname3",     "s3": "admin_first_name_3"},
        "AdmLName3":    {"s2": "adm_lname3",     "s3": "admin_last_name_3"},
        "AdmEmail3":    {"s2": "adm_email3",     "s3": "admin_email_3"},
    },

    # =========================================================================
    # financial
    # =========================================================================
    # district.A2–A16 are essentially anonymous (S1/S2); expand to S3.
    # disp_id, k_symbol, bank_to, account_to are S2; expand to S3.
    # S3 tables (loan, client, account) need S2 abbreviations.
    # =========================================================================
    "financial": {
        # ----- district table (A2–A16 anonymous) -----
        "district_id":      {"s2": "dist_id",       "s3": "district_id"},
        "A2":               {"s2": "dist_nm",        "s3": "district_name"},
        "A3":               {"s2": "region",         "s3": "region"},
        "A4":               {"s2": "num_inhab",      "s3": "number_inhabitants"},
        "A5":               {"s2": "num_mun_lt499",  "s3": "number_municipalities_below_499"},
        "A6":               {"s2": "num_mun_500",    "s3": "number_municipalities_500_to_1999"},
        "A7":               {"s2": "num_mun_2000",   "s3": "number_municipalities_2000_to_9999"},
        "A8":               {"s2": "num_mun_gt10k",  "s3": "number_municipalities_above_10000"},
        "A9":               {"s2": "num_cities",     "s3": "number_cities"},
        "A10":              {"s2": "urban_ratio",    "s3": "urban_inhabitant_ratio"},
        "A11":              {"s2": "avg_sal",        "s3": "average_salary"},
        "A12":              {"s2": "unemp_95",       "s3": "unemployment_rate_1995"},
        "A13":              {"s2": "unemp_96",       "s3": "unemployment_rate_1996"},
        "A14":              {"s2": "entre_per_1k",   "s3": "entrepreneurs_per_1000"},
        "A15":              {"s2": "crimes_95",      "s3": "number_crimes_1995"},
        "A16":              {"s2": "crimes_96",      "s3": "number_crimes_1996"},
        # ----- disp table (abbreviated table name / column) -----
        "disp_id":          {"s2": "disp_id",        "s3": "disposition_id"},
        # ----- card table -----
        "card_id":          {"s2": "card_id",        "s3": "card_id"},
        "issued":           {"s2": "issued_dt",      "s3": "issued_date"},
        # ----- account table -----
        "account_id":       {"s2": "acct_id",        "s3": "account_id"},
        "frequency":        {"s2": "freq",           "s3": "statement_frequency"},
        # ----- client table -----
        "client_id":        {"s2": "client_id",      "s3": "client_id"},
        "birth_date":       {"s2": "birth_dt",       "s3": "birth_date"},
        # ----- order table -----
        "order_id":         {"s2": "order_id",       "s3": "order_id"},
        "bank_to":          {"s2": "bank_to",        "s3": "recipient_bank"},
        "account_to":       {"s2": "acct_to",        "s3": "recipient_account"},
        "k_symbol":         {"s2": "k_sym",          "s3": "transaction_type_code"},
        # ----- trans table -----
        "trans_id":         {"s2": "txn_id",         "s3": "transaction_id"},
        "operation":        {"s2": "op",             "s3": "transaction_operation"},
        "balance":          {"s2": "bal",            "s3": "balance_after_transaction"},
        # ----- loan table -----
        "loan_id":          {"s2": "loan_id",        "s3": "loan_id"},
        "duration":         {"s2": "dur_months",     "s3": "duration_months"},
        "payments":         {"s2": "payment_amt",    "s3": "monthly_payment_amount"},
    },

    # =========================================================================
    # thrombosis_prediction
    # =========================================================================
    # Nearly all Laboratory columns are medical abbreviations (S2).
    # Patient.SEX is S2; Examination columns are S2 medical codes.
    # =========================================================================
    "thrombosis_prediction": {
        # ----- Patient table -----
        "SEX":          {"s2": "sex",           "s3": "sex"},
        "Birthday":     {"s2": "bday",          "s3": "birthday"},
        "Description":  {"s2": "first_rec_dt",  "s3": "first_record_date"},
        "First Date":   {"s2": "admit_dt",      "s3": "first_hospital_visit_date"},
        "Admission":    {"s2": "admission",     "s3": "admission_type"},
        "Diagnosis":    {"s2": "diag",          "s3": "diagnosis"},
        # ----- Examination table -----
        "Examination Date": {"s2": "exam_dt",   "s3": "examination_date"},
        "aCL IgG":      {"s2": "acl_igg",       "s3": "anticardiolipin_igg"},
        "aCL IgM":      {"s2": "acl_igm",       "s3": "anticardiolipin_igm"},
        "ANA":          {"s2": "ana",            "s3": "antinuclear_antibody"},
        "ANA Pattern":  {"s2": "ana_pattern",   "s3": "antinuclear_antibody_pattern"},
        "aCL IgA":      {"s2": "acl_iga",       "s3": "anticardiolipin_iga"},
        "KCT":          {"s2": "kct",            "s3": "kaolin_clotting_time"},
        "RVVT":         {"s2": "rvvt",           "s3": "russell_viper_venom_time"},
        "LAC":          {"s2": "lac",            "s3": "lupus_anticoagulant"},
        "Symptoms":     {"s2": "symptoms",      "s3": "symptoms"},
        "Thrombosis":   {"s2": "thrombosis",    "s3": "thrombosis_degree"},
        # ----- Laboratory table -----
        "GOT":          {"s2": "got",           "s3": "aspartate_aminotransferase"},
        "GPT":          {"s2": "gpt",           "s3": "alanine_aminotransferase"},
        "LDH":          {"s2": "ldh",           "s3": "lactate_dehydrogenase"},
        "ALP":          {"s2": "alp",           "s3": "alkaline_phosphatase"},
        "TP":           {"s2": "tp",            "s3": "total_protein"},
        "ALB":          {"s2": "alb",           "s3": "albumin"},
        "UA":           {"s2": "ua",            "s3": "uric_acid"},
        "UN":           {"s2": "un",            "s3": "urea_nitrogen"},
        "CRE":          {"s2": "cre",           "s3": "creatinine"},
        "T-BIL":        {"s2": "t_bil",         "s3": "total_bilirubin"},
        "T-CHO":        {"s2": "t_cho",         "s3": "total_cholesterol"},
        "TG":           {"s2": "tg",            "s3": "triglyceride"},
        "CPK":          {"s2": "cpk",           "s3": "creatinine_phosphokinase"},
        "GLU":          {"s2": "glu",           "s3": "blood_glucose"},
        "WBC":          {"s2": "wbc",           "s3": "white_blood_cell_count"},
        "RBC":          {"s2": "rbc",           "s3": "red_blood_cell_count"},
        "HGB":          {"s2": "hgb",           "s3": "hemoglobin"},
        "HCT":          {"s2": "hct",           "s3": "hematocrit"},
        "PLT":          {"s2": "plt",           "s3": "platelet_count"},
        "PT":           {"s2": "pt",            "s3": "prothrombin_time"},
        "APTT":         {"s2": "aptt",          "s3": "activated_partial_thromboplastin_time"},
        "FG":           {"s2": "fg",            "s3": "fibrinogen"},
        "PIC":          {"s2": "pic",           "s3": "pic"},
        "TAT":          {"s2": "tat",           "s3": "tat"},
        "TAT2":         {"s2": "tat2",          "s3": "tat2"},
        "U-PRO":        {"s2": "u_pro",         "s3": "proteinuria"},
        "IGG":          {"s2": "igg",           "s3": "immunoglobulin_g"},
        "IGA":          {"s2": "iga",           "s3": "immunoglobulin_a"},
        "IGM":          {"s2": "igm",           "s3": "immunoglobulin_m"},
        "CRP":          {"s2": "crp",           "s3": "c_reactive_protein"},
        "RA":           {"s2": "ra",            "s3": "rheumatoid_factor_ra"},
        "RF":           {"s2": "rf",            "s3": "raha_titer"},
        "C3":           {"s2": "c3",            "s3": "complement_component_3"},
        "C4":           {"s2": "c4",            "s3": "complement_component_4"},
        "RNP":          {"s2": "rnp",           "s3": "anti_ribonuclear_protein"},
        "SM":           {"s2": "sm",            "s3": "anti_sm"},
        "SC170":        {"s2": "sc170",         "s3": "anti_scl70"},
        "SSA":          {"s2": "ssa",           "s3": "anti_ssa"},
        "SSB":          {"s2": "ssb",           "s3": "anti_ssb"},
        "CENTROMEA":    {"s2": "centromea",     "s3": "anti_centromere"},
        "DNA":          {"s2": "dna",           "s3": "anti_dna"},
        "DNA-II":       {"s2": "dna_ii",        "s3": "anti_dna_ii"},
    },

    # =========================================================================
    # formula_1
    # =========================================================================
    # Most columns are already S3-quality (camelCase readable).
    # A handful are abbreviated: lat/lng/alt/dob/circuitRef/driverRef/q1-q3.
    # Add S2 downgrades for the already-descriptive columns too.
    # =========================================================================
    "formula_1": {
        # circuits
        "circuitId":            {"s2": "cir_id",        "s3": "circuit_id"},
        "circuitRef":           {"s2": "cir_ref",       "s3": "circuit_ref_name"},
        "lat":                  {"s2": "lat",           "s3": "latitude"},
        "lng":                  {"s2": "lng",           "s3": "longitude"},
        "alt":                  {"s2": "alt",           "s3": "altitude"},
        # constructors
        "constructorId":        {"s2": "ctor_id",       "s3": "constructor_id"},
        "constructorRef":       {"s2": "ctor_ref",      "s3": "constructor_ref_name"},
        "nationality":          {"s2": "nation",        "s3": "nationality"},
        # drivers
        "driverId":             {"s2": "drv_id",        "s3": "driver_id"},
        "driverRef":            {"s2": "drv_ref",       "s3": "driver_ref_name"},
        "code":                 {"s2": "code",          "s3": "driver_code"},
        "forename":             {"s2": "fname",         "s3": "first_name"},
        "surname":              {"s2": "lname",         "s3": "last_name"},
        "dob":                  {"s2": "dob",           "s3": "date_of_birth"},
        # races
        "raceId":               {"s2": "race_id",       "s3": "race_id"},
        # constructorResults
        "constructorResultsId": {"s2": "ctor_res_id",   "s3": "constructor_results_id"},
        # constructorStandings
        "constructorStandingsId": {"s2": "ctor_std_id", "s3": "constructor_standings_id"},
        "positionText":         {"s2": "pos_txt",       "s3": "position_text"},
        # driverStandings
        "driverStandingsId":    {"s2": "drv_std_id",    "s3": "driver_standings_id"},
        # lapTimes
        "milliseconds":         {"s2": "ms",            "s3": "milliseconds"},
        # pitStops
        "stop":                 {"s2": "stop_num",      "s3": "stop_number"},
        # qualifying
        "qualifyId":            {"s2": "qual_id",       "s3": "qualify_id"},
        "q1":                   {"s2": "q1",            "s3": "qualifying_1_time"},
        "q2":                   {"s2": "q2",            "s3": "qualifying_2_time"},
        "q3":                   {"s2": "q3",            "s3": "qualifying_3_time"},
        # results
        "resultId":             {"s2": "res_id",        "s3": "result_id"},
        "grid":                 {"s2": "grid",          "s3": "grid_position"},
        "positionOrder":        {"s2": "pos_order",     "s3": "position_order"},
        "fastestLap":           {"s2": "fast_lap",      "s3": "fastest_lap_number"},
        "fastestLapTime":       {"s2": "fast_lap_tm",   "s3": "fastest_lap_time"},
        "fastestLapSpeed":      {"s2": "fast_lap_spd",  "s3": "fastest_lap_speed"},
        "statusId":             {"s2": "status_id",     "s3": "status_id"},
        # status
        "statusId_tbl":         {"s2": "status_id",     "s3": "status_id"},
    },

    # =========================================================================
    # european_football_2
    # =========================================================================
    # Player / Player_Attributes / Team / Team_Attributes / League / Country
    # are S3-quality (snake_case descriptive).  The Match table has betting
    # odds codes (B365H, BWH …) that are S2.
    # =========================================================================
    "european_football_2": {
        # ----- Player -----
        "player_api_id":        {"s2": "plr_api_id",    "s3": "player_api_id"},
        "player_fifa_api_id":   {"s2": "fifa_api_id",   "s3": "player_fifa_api_id"},
        "player_name":          {"s2": "plr_nm",        "s3": "player_name"},
        "birthday":             {"s2": "bday",          "s3": "birthday"},
        "height":               {"s2": "ht",            "s3": "height"},
        "weight":               {"s2": "wt",            "s3": "weight"},
        # ----- Player_Attributes -----
        "overall_rating":       {"s2": "ovr_rtg",       "s3": "overall_rating"},
        "potential":            {"s2": "potential",     "s3": "potential"},
        "preferred_foot":       {"s2": "pref_foot",     "s3": "preferred_foot"},
        "attacking_work_rate":  {"s2": "atk_wr",        "s3": "attacking_work_rate"},
        "defensive_work_rate":  {"s2": "def_wr",        "s3": "defensive_work_rate"},
        "crossing":             {"s2": "cross",         "s3": "crossing"},
        "finishing":            {"s2": "finish",        "s3": "finishing"},
        "heading_accuracy":     {"s2": "head_acc",      "s3": "heading_accuracy"},
        "short_passing":        {"s2": "sh_pass",       "s3": "short_passing"},
        "volleys":              {"s2": "volleys",       "s3": "volleys"},
        "dribbling":            {"s2": "dribble",       "s3": "dribbling"},
        "curve":                {"s2": "curve",         "s3": "curve"},
        "free_kick_accuracy":   {"s2": "fk_acc",        "s3": "free_kick_accuracy"},
        "long_passing":         {"s2": "lng_pass",      "s3": "long_passing"},
        "ball_control":         {"s2": "ball_ctrl",     "s3": "ball_control"},
        "acceleration":         {"s2": "accel",         "s3": "acceleration"},
        "sprint_speed":         {"s2": "sprt_spd",      "s3": "sprint_speed"},
        "agility":              {"s2": "agility",       "s3": "agility"},
        "reactions":            {"s2": "react",         "s3": "reactions"},
        "balance":              {"s2": "balance",       "s3": "balance"},
        "shot_power":           {"s2": "shot_pwr",      "s3": "shot_power"},
        "jumping":              {"s2": "jump",          "s3": "jumping"},
        "stamina":              {"s2": "stamina",       "s3": "stamina"},
        "strength":             {"s2": "strength",      "s3": "strength"},
        "long_shots":           {"s2": "lng_shots",     "s3": "long_shots"},
        "aggression":           {"s2": "aggr",          "s3": "aggression"},
        "interceptions":        {"s2": "interc",        "s3": "interceptions"},
        "positioning":          {"s2": "pos",           "s3": "positioning"},
        "vision":               {"s2": "vision",        "s3": "vision"},
        "penalties":            {"s2": "pens",          "s3": "penalties"},
        "marking":              {"s2": "marking",       "s3": "marking"},
        "standing_tackle":      {"s2": "std_tackle",    "s3": "standing_tackle"},
        "sliding_tackle":       {"s2": "sld_tackle",    "s3": "sliding_tackle"},
        "gk_diving":            {"s2": "gk_div",        "s3": "goalkeeper_diving"},
        "gk_handling":          {"s2": "gk_hand",       "s3": "goalkeeper_handling"},
        "gk_kicking":           {"s2": "gk_kick",       "s3": "goalkeeper_kicking"},
        "gk_positioning":       {"s2": "gk_pos",        "s3": "goalkeeper_positioning"},
        "gk_reflexes":          {"s2": "gk_ref",        "s3": "goalkeeper_reflexes"},
        # ----- Team -----
        "team_api_id":          {"s2": "team_api_id",   "s3": "team_api_id"},
        "team_fifa_api_id":     {"s2": "fifa_team_id",  "s3": "team_fifa_api_id"},
        "team_long_name":       {"s2": "team_nm",       "s3": "team_long_name"},
        "team_short_name":      {"s2": "team_abbr",     "s3": "team_short_name"},
        # ----- Team_Attributes -----
        "buildUpPlaySpeed":         {"s2": "bu_spd",        "s3": "buildup_play_speed"},
        "buildUpPlaySpeedClass":    {"s2": "bu_spd_cls",    "s3": "buildup_play_speed_class"},
        "buildUpPlayDribbling":     {"s2": "bu_drib",       "s3": "buildup_play_dribbling"},
        "buildUpPlayDribblingClass":{"s2": "bu_drib_cls",   "s3": "buildup_play_dribbling_class"},
        "buildUpPlayPassing":       {"s2": "bu_pass",       "s3": "buildup_play_passing"},
        "buildUpPlayPassingClass":  {"s2": "bu_pass_cls",   "s3": "buildup_play_passing_class"},
        "buildUpPlayPositioningClass": {"s2": "bu_pos_cls", "s3": "buildup_play_positioning_class"},
        "chanceCreationPassing":    {"s2": "cc_pass",       "s3": "chance_creation_passing"},
        "chanceCreationPassingClass": {"s2": "cc_pass_cls", "s3": "chance_creation_passing_class"},
        "chanceCreationCrossing":   {"s2": "cc_cross",      "s3": "chance_creation_crossing"},
        "chanceCreationCrossingClass": {"s2": "cc_cross_cls","s3": "chance_creation_crossing_class"},
        "chanceCreationShooting":   {"s2": "cc_shoot",      "s3": "chance_creation_shooting"},
        "chanceCreationShootingClass": {"s2": "cc_shoot_cls","s3": "chance_creation_shooting_class"},
        "chanceCreationPositioningClass": {"s2": "cc_pos_cls","s3": "chance_creation_positioning_class"},
        "defencePressure":          {"s2": "def_press",     "s3": "defence_pressure"},
        "defencePressureClass":     {"s2": "def_press_cls", "s3": "defence_pressure_class"},
        "defenceAggression":        {"s2": "def_aggr",      "s3": "defence_aggression"},
        "defenceAggressionClass":   {"s2": "def_aggr_cls",  "s3": "defence_aggression_class"},
        "defenceTeamWidth":         {"s2": "def_width",     "s3": "defence_team_width"},
        "defenceTeamWidthClass":    {"s2": "def_width_cls", "s3": "defence_team_width_class"},
        "defenceDefenderLineClass": {"s2": "def_line_cls",  "s3": "defence_defender_line_class"},
        # ----- Match — general -----
        "match_api_id":         {"s2": "match_api_id",  "s3": "match_api_id"},
        "home_team_api_id":     {"s2": "home_team_id",  "s3": "home_team_api_id"},
        "away_team_api_id":     {"s2": "away_team_id",  "s3": "away_team_api_id"},
        "home_team_goal":       {"s2": "home_goals",    "s3": "home_team_goals"},
        "away_team_goal":       {"s2": "away_goals",    "s3": "away_team_goals"},
        "shoton":               {"s2": "shots_on",      "s3": "shots_on_target"},
        "shotoff":              {"s2": "shots_off",     "s3": "shots_off_target"},
        "foulcommit":           {"s2": "fouls",         "s3": "fouls_committed"},
        "possession":           {"s2": "poss",          "s3": "possession"},
        # ----- Match — player X/Y coordinates -----
        **{f"home_player_X{i}": {"s2": f"hp{i}_x",   "s3": f"home_player_{i}_x_position"} for i in range(1, 12)},
        **{f"away_player_X{i}": {"s2": f"ap{i}_x",   "s3": f"away_player_{i}_x_position"} for i in range(1, 12)},
        **{f"home_player_Y{i}": {"s2": f"hp{i}_y",   "s3": f"home_player_{i}_y_position"} for i in range(1, 12)},
        **{f"away_player_Y{i}": {"s2": f"ap{i}_y",   "s3": f"away_player_{i}_y_position"} for i in range(1, 12)},
        # ----- Match — player IDs -----
        **{f"home_player_{i}":  {"s2": f"hp{i}_id",  "s3": f"home_player_{i}_api_id"} for i in range(1, 12)},
        **{f"away_player_{i}":  {"s2": f"ap{i}_id",  "s3": f"away_player_{i}_api_id"} for i in range(1, 12)},
        # ----- Match — betting odds (S2 → S3) -----
        "B365H": {"s2": "b365h",   "s3": "bet365_home_odds"},
        "B365D": {"s2": "b365d",   "s3": "bet365_draw_odds"},
        "B365A": {"s2": "b365a",   "s3": "bet365_away_odds"},
        "BWH":   {"s2": "bwh",     "s3": "bwin_home_odds"},
        "BWD":   {"s2": "bwd",     "s3": "bwin_draw_odds"},
        "BWA":   {"s2": "bwa",     "s3": "bwin_away_odds"},
        "IWH":   {"s2": "iwh",     "s3": "interwetten_home_odds"},
        "IWD":   {"s2": "iwd",     "s3": "interwetten_draw_odds"},
        "IWA":   {"s2": "iwa",     "s3": "interwetten_away_odds"},
        "LBH":   {"s2": "lbh",     "s3": "ladbrokes_home_odds"},
        "LBD":   {"s2": "lbd",     "s3": "ladbrokes_draw_odds"},
        "LBA":   {"s2": "lba",     "s3": "ladbrokes_away_odds"},
        "PSH":   {"s2": "psh",     "s3": "pinnacle_home_odds"},
        "PSD":   {"s2": "psd",     "s3": "pinnacle_draw_odds"},
        "PSA":   {"s2": "psa",     "s3": "pinnacle_away_odds"},
        "WHH":   {"s2": "whh",     "s3": "william_hill_home_odds"},
        "WHD":   {"s2": "whd",     "s3": "william_hill_draw_odds"},
        "WHA":   {"s2": "wha",     "s3": "william_hill_away_odds"},
        "SJH":   {"s2": "sjh",     "s3": "stan_james_home_odds"},
        "SJD":   {"s2": "sjd",     "s3": "stan_james_draw_odds"},
        "SJA":   {"s2": "sja",     "s3": "stan_james_away_odds"},
        "VCH":   {"s2": "vch",     "s3": "vcbet_home_odds"},
        "VCD":   {"s2": "vcd",     "s3": "vcbet_draw_odds"},
        "VCA":   {"s2": "vca",     "s3": "vcbet_away_odds"},
        "GBH":   {"s2": "gbh",     "s3": "gamebookers_home_odds"},
        "GBD":   {"s2": "gbd",     "s3": "gamebookers_draw_odds"},
        "GBA":   {"s2": "gba",     "s3": "gamebookers_away_odds"},
        "BSH":   {"s2": "bsh",     "s3": "bluesquare_home_odds"},
        "BSD":   {"s2": "bsd",     "s3": "bluesquare_draw_odds"},
        "BSA":   {"s2": "bsa",     "s3": "bluesquare_away_odds"},
    },

    # =========================================================================
    # card_games
    # =========================================================================
    # Most columns are S3-quality camelCase. Only the external platform IDs
    # (mcmId, mtgoId, scryfallId …) are S2 abbreviations.
    # =========================================================================
    "card_games": {
        # already-S3 columns → need S2 abbreviations
        "asciiName":                {"s2": "ascii_nm",          "s3": "ascii_name"},
        "availability":             {"s2": "avail",             "s3": "availability"},
        "borderColor":              {"s2": "bdr_clr",           "s3": "border_color"},
        "colorIdentity":            {"s2": "clr_id",            "s3": "color_identity"},
        "colorIndicator":           {"s2": "clr_ind",           "s3": "color_indicator"},
        "convertedManaCost":        {"s2": "cmc",               "s3": "converted_mana_cost"},
        "duelDeck":                 {"s2": "duel_deck",         "s3": "duel_deck"},
        "faceConvertedManaCost":    {"s2": "face_cmc",          "s3": "face_converted_mana_cost"},
        "faceName":                 {"s2": "face_nm",           "s3": "face_name"},
        "flavorName":               {"s2": "flvr_nm",           "s3": "flavor_name"},
        "flavorText":               {"s2": "flvr_txt",          "s3": "flavor_text"},
        "frameEffects":             {"s2": "frm_fx",            "s3": "frame_effects"},
        "frameVersion":             {"s2": "frm_ver",           "s3": "frame_version"},
        "hasAlternativeDeckLimit":  {"s2": "has_alt_deck",      "s3": "has_alternative_deck_limit"},
        "hasContentWarning":        {"s2": "has_warn",          "s3": "has_content_warning"},
        "hasFoil":                  {"s2": "has_foil",          "s3": "has_foil"},
        "hasNonFoil":               {"s2": "has_nonfoil",       "s3": "has_non_foil"},
        "isAlternative":            {"s2": "is_alt",            "s3": "is_alternative"},
        "isFullArt":                {"s2": "is_full_art",       "s3": "is_full_art"},
        "isOnlineOnly":             {"s2": "is_online",         "s3": "is_online_only"},
        "isOversized":              {"s2": "is_oversized",      "s3": "is_oversized"},
        "isPromo":                  {"s2": "is_promo",          "s3": "is_promo"},
        "isReprint":                {"s2": "is_reprint",        "s3": "is_reprint"},
        "isReserved":               {"s2": "is_reserved",       "s3": "is_reserved"},
        "isStarter":                {"s2": "is_starter",        "s3": "is_starter"},
        "isStorySpotlight":         {"s2": "is_story",          "s3": "is_story_spotlight"},
        "isTextless":               {"s2": "is_textless",       "s3": "is_textless"},
        "isTimeshifted":            {"s2": "is_timeshifted",    "s3": "is_timeshifted"},
        "leadershipSkills":         {"s2": "lead_skills",       "s3": "leadership_skills"},
        "manaCost":                 {"s2": "mana_cost",         "s3": "mana_cost"},
        "originalReleaseDate":      {"s2": "orig_rel_dt",       "s3": "original_release_date"},
        "originalText":             {"s2": "orig_txt",          "s3": "original_text"},
        "originalType":             {"s2": "orig_type",         "s3": "original_type"},
        "otherFaceIds":             {"s2": "other_ids",         "s3": "other_face_ids"},
        "promoTypes":               {"s2": "promo_types",       "s3": "promo_types"},
        "purchaseUrls":             {"s2": "buy_urls",          "s3": "purchase_urls"},
        "setCode":                  {"s2": "set_cd",            "s3": "set_code"},
        "subtypes":                 {"s2": "subtypes",          "s3": "subtypes"},
        "supertypes":               {"s2": "supertypes",        "s3": "supertypes"},
        "watermark":                {"s2": "watermark",         "s3": "watermark"},
        # platform IDs (S2 → S3 expansions)
        "edhrecRank":               {"s2": "edhrec_rank",       "s3": "edhrec_rank"},
        "cardKingdomFoilId":        {"s2": "ck_foil_id",        "s3": "card_kingdom_foil_id"},
        "cardKingdomId":            {"s2": "ck_id",             "s3": "card_kingdom_id"},
        "mcmId":                    {"s2": "mcm_id",            "s3": "magic_cardmarket_id"},
        "mcmMetaId":                {"s2": "mcm_meta_id",       "s3": "magic_cardmarket_meta_id"},
        "mtgArenaId":               {"s2": "arena_id",          "s3": "magic_the_gathering_arena_id"},
        "mtgjsonV4Id":              {"s2": "mtgjson_id",        "s3": "mtgjson_v4_id"},
        "mtgoFoilId":               {"s2": "mtgo_foil_id",      "s3": "magic_the_gathering_online_foil_id"},
        "mtgoId":                   {"s2": "mtgo_id",           "s3": "magic_the_gathering_online_id"},
        "multiverseId":             {"s2": "mv_id",             "s3": "multiverse_id"},
        "scryfallId":               {"s2": "sf_id",             "s3": "scryfall_id"},
        "scryfallIllustrationId":   {"s2": "sf_illus_id",       "s3": "scryfall_illustration_id"},
        "scryfallOracleId":         {"s2": "sf_oracle_id",      "s3": "scryfall_oracle_id"},
        "tcgplayerProductId":       {"s2": "tcg_prod_id",       "s3": "tcgplayer_product_id"},
        # sets table
        "baseSetSize":              {"s2": "base_sz",           "s3": "base_set_size"},
        "isFoilOnly":               {"s2": "foil_only",         "s3": "is_foil_only"},
        "isForeignOnly":            {"s2": "foreign_only",      "s3": "is_foreign_only"},
        "isNonFoilOnly":            {"s2": "nonfoil_only",      "s3": "is_non_foil_only"},
        "isPartialPreview":         {"s2": "partial_prev",      "s3": "is_partial_preview"},
        "keyruneCode":              {"s2": "keyrune_cd",        "s3": "keyrune_icon_code"},
        "mcmIdExtras":              {"s2": "mcm_extra_id",      "s3": "magic_cardmarket_id_extras"},
        "mcmName":                  {"s2": "mcm_nm",            "s3": "magic_cardmarket_name"},
        "mtgoCode":                 {"s2": "mtgo_cd",           "s3": "mtgo_set_code"},
        "parentCode":               {"s2": "parent_cd",         "s3": "parent_set_code"},
        "releaseDate":              {"s2": "rel_dt",            "s3": "release_date"},
        "tcgplayerGroupId":         {"s2": "tcg_grp_id",        "s3": "tcgplayer_group_id"},
        "totalSetSize":             {"s2": "total_sz",          "s3": "total_set_size"},
        # set_translations
        "translation":              {"s2": "trans",             "s3": "translation"},
        # foreign_data
        "multiverseid":             {"s2": "mv_id",             "s3": "multiverse_id"},
    },

    # =========================================================================
    # student_club  (original ≈ S3; add S2 abbreviations)
    # =========================================================================
    "student_club": {
        "event_id":             {"s2": "evt_id",    "s3": "event_id"},
        "event_name":           {"s2": "evt_nm",    "s3": "event_name"},
        "event_date":           {"s2": "evt_dt",    "s3": "event_date"},
        "notes":                {"s2": "notes",     "s3": "notes"},
        "location":             {"s2": "loc",       "s3": "location"},
        "major_id":             {"s2": "maj_id",    "s3": "major_id"},
        "major_name":           {"s2": "maj_nm",    "s3": "major_name"},
        "department":           {"s2": "dept",      "s3": "department"},
        "college":              {"s2": "coll",      "s3": "college"},
        "zip_code":             {"s2": "zip_cd",    "s3": "zip_code"},
        "county":               {"s2": "cnty",      "s3": "county"},
        "short_state":          {"s2": "st",        "s3": "state_abbr"},
        "link_to_event":        {"s2": "evt_id",    "s3": "event_id"},
        "link_to_member":       {"s2": "mbr_id",    "s3": "member_id"},
        "budget_id":            {"s2": "bgt_id",    "s3": "budget_id"},
        "category":             {"s2": "cat",       "s3": "category"},
        "spent":                {"s2": "spent",     "s3": "amount_spent"},
        "remaining":            {"s2": "remain",    "s3": "amount_remaining"},
        "amount":               {"s2": "amt",       "s3": "amount"},
        "event_status":         {"s2": "evt_status","s3": "event_status"},
        "link_to_budget":       {"s2": "bgt_id",    "s3": "budget_id"},
        "expense_id":           {"s2": "exp_id",    "s3": "expense_id"},
        "expense_description":  {"s2": "exp_desc",  "s3": "expense_description"},
        "expense_date":         {"s2": "exp_dt",    "s3": "expense_date"},
        "approved":             {"s2": "aprvd",     "s3": "is_approved"},
        "income_id":            {"s2": "inc_id",    "s3": "income_id"},
        "date_received":        {"s2": "rcvd_dt",   "s3": "date_received"},
        "source":               {"s2": "src",       "s3": "income_source"},
        "member_id":            {"s2": "mbr_id",    "s3": "member_id"},
        "first_name":           {"s2": "fname",     "s3": "first_name"},
        "last_name":            {"s2": "lname",     "s3": "last_name"},
        "email":                {"s2": "email",     "s3": "email"},
        "position":             {"s2": "pos",       "s3": "position"},
        "t_shirt_size":         {"s2": "shirt_sz",  "s3": "t_shirt_size"},
        "phone":                {"s2": "phone",     "s3": "phone"},
        "zip":                  {"s2": "zip",       "s3": "zip_code"},
        "link_to_major":        {"s2": "maj_id",    "s3": "major_id"},
    },

    # =========================================================================
    # superhero  (original ≈ S3; add S2 abbreviations)
    # =========================================================================
    "superhero": {
        "alignment":        {"s2": "align",         "s3": "alignment"},
        "attribute_name":   {"s2": "attr_nm",        "s3": "attribute_name"},
        "colour":           {"s2": "color",          "s3": "colour"},
        "publisher_name":   {"s2": "pub_nm",         "s3": "publisher_name"},
        "superhero_name":   {"s2": "hero_nm",        "s3": "superhero_name"},
        "full_name":        {"s2": "full_nm",        "s3": "full_name"},
        "gender_id":        {"s2": "gender_id",      "s3": "gender_id"},
        "eye_colour_id":    {"s2": "eye_clr_id",     "s3": "eye_colour_id"},
        "hair_colour_id":   {"s2": "hair_clr_id",    "s3": "hair_colour_id"},
        "skin_colour_id":   {"s2": "skin_clr_id",    "s3": "skin_colour_id"},
        "race_id":          {"s2": "race_id",        "s3": "race_id"},
        "publisher_id":     {"s2": "pub_id",         "s3": "publisher_id"},
        "alignment_id":     {"s2": "align_id",       "s3": "alignment_id"},
        "height_cm":        {"s2": "ht_cm",          "s3": "height_cm"},
        "weight_kg":        {"s2": "wt_kg",          "s3": "weight_kg"},
        "hero_id":          {"s2": "hero_id",        "s3": "hero_id"},
        "attribute_id":     {"s2": "attr_id",        "s3": "attribute_id"},
        "attribute_value":  {"s2": "attr_val",       "s3": "attribute_value"},
        "power_name":       {"s2": "pwr_nm",         "s3": "power_name"},
        "power_id":         {"s2": "pwr_id",         "s3": "power_id"},
    },

    # =========================================================================
    # toxicology  (original ≈ S3; add S2 abbreviations)
    # =========================================================================
    "toxicology": {
        "atom_id":      {"s2": "atm_id",   "s3": "atom_id"},
        "molecule_id":  {"s2": "mol_id",   "s3": "molecule_id"},
        "element":      {"s2": "elem",     "s3": "element"},
        "bond_id":      {"s2": "bnd_id",   "s3": "bond_id"},
        "bond_type":    {"s2": "bnd_type", "s3": "bond_type"},
        "atom_id2":     {"s2": "atm_id2",  "s3": "atom_id2"},
        "label":        {"s2": "lbl",      "s3": "label"},
    },

    # =========================================================================
    # debit_card_specializing  (original ≈ S3 PascalCase; add S2)
    # =========================================================================
    "debit_card_specializing": {
        "CustomerID":   {"s2": "cust_id",   "s3": "customer_id"},
        "Segment":      {"s2": "seg",       "s3": "segment"},
        "Currency":     {"s2": "curr",      "s3": "currency"},
        "GasStationID": {"s2": "gs_id",     "s3": "gas_station_id"},
        "ChainID":      {"s2": "chain_id",  "s3": "chain_id"},
        "Country":      {"s2": "ctry",      "s3": "country"},
        "ProductID":    {"s2": "prod_id",   "s3": "product_id"},
        "Description":  {"s2": "descr",     "s3": "description"},
        "TransactionID":{"s2": "txn_id",    "s3": "transaction_id"},
        "Date":         {"s2": "date",      "s3": "date"},
        "Time":         {"s2": "time",      "s3": "time"},
        "CardID":       {"s2": "card_id",   "s3": "card_id"},
        "Amount":       {"s2": "amt",       "s3": "amount"},
        "Price":        {"s2": "price",     "s3": "price"},
        "Consumption":  {"s2": "consump",   "s3": "consumption"},
    },

    # =========================================================================
    # codebase_community  (original ≈ S3 PascalCase; add S2)
    # =========================================================================
    "codebase_community": {
        "UserId":               {"s2": "usr_id",        "s3": "user_id"},
        "Name":                 {"s2": "nm",            "s3": "name"},
        "PostId":               {"s2": "post_id",       "s3": "post_id"},
        "Score":                {"s2": "score",         "s3": "score"},
        "Text":                 {"s2": "txt",           "s3": "text"},
        "CreationDate":         {"s2": "cre_dt",        "s3": "creation_date"},
        "UserDisplayName":      {"s2": "usr_nm",        "s3": "user_display_name"},
        "PostHistoryTypeId":    {"s2": "ph_type_id",    "s3": "post_history_type_id"},
        "RevisionGUID":         {"s2": "rev_guid",      "s3": "revision_guid"},
        "Comment":              {"s2": "cmt",           "s3": "comment"},
        "RelatedPostId":        {"s2": "rel_post_id",   "s3": "related_post_id"},
        "LinkTypeId":           {"s2": "lnk_type_id",   "s3": "link_type_id"},
        "PostTypeId":           {"s2": "post_type_id",  "s3": "post_type_id"},
        "AcceptedAnswerId":     {"s2": "ans_id",        "s3": "accepted_answer_id"},
        "CreaionDate":          {"s2": "cre_dt",        "s3": "creation_date"},   # typo in original
        "ViewCount":            {"s2": "views",         "s3": "view_count"},
        "Body":                 {"s2": "body",          "s3": "body"},
        "OwnerUserId":          {"s2": "owner_id",      "s3": "owner_user_id"},
        "LasActivityDate":      {"s2": "last_act_dt",   "s3": "last_activity_date"},  # typo in original
        "Title":                {"s2": "title",         "s3": "title"},
        "Tags":                 {"s2": "tags",          "s3": "tags"},
        "AnswerCount":          {"s2": "ans_cnt",       "s3": "answer_count"},
        "CommentCount":         {"s2": "cmt_cnt",       "s3": "comment_count"},
        "FavoriteCount":        {"s2": "fav_cnt",       "s3": "favorite_count"},
        "LastEditorUserId":     {"s2": "last_ed_id",    "s3": "last_editor_user_id"},
        "LastEditDate":         {"s2": "last_ed_dt",    "s3": "last_edit_date"},
        "CommunityOwnedDate":   {"s2": "comm_own_dt",   "s3": "community_owned_date"},
        "ParentId":             {"s2": "par_id",        "s3": "parent_post_id"},
        "ClosedDate":           {"s2": "close_dt",      "s3": "closed_date"},
        "OwnerDisplayName":     {"s2": "owner_nm",      "s3": "owner_display_name"},
        "LastEditorDisplayName":{"s2": "last_ed_nm",    "s3": "last_editor_display_name"},
        "TagName":              {"s2": "tag_nm",        "s3": "tag_name"},
        "Count":                {"s2": "cnt",           "s3": "count"},
        "ExcerptPostId":        {"s2": "excerpt_id",    "s3": "excerpt_post_id"},
        "WikiPostId":           {"s2": "wiki_id",       "s3": "wiki_post_id"},
        "Reputation":           {"s2": "rep",           "s3": "reputation"},
        "DisplayName":          {"s2": "disp_nm",       "s3": "display_name"},
        "LastAccessDate":       {"s2": "last_acc_dt",   "s3": "last_access_date"},
        "WebsiteUrl":           {"s2": "web_url",       "s3": "website_url"},
        "Location":             {"s2": "loc",           "s3": "location"},
        "AboutMe":              {"s2": "about",         "s3": "about_me"},
        "Views":                {"s2": "views",         "s3": "views"},
        "UpVotes":              {"s2": "up_votes",      "s3": "up_votes"},
        "DownVotes":            {"s2": "dn_votes",      "s3": "down_votes"},
        "AccountId":            {"s2": "acct_id",       "s3": "account_id"},
        "Age":                  {"s2": "age",           "s3": "age"},
        "ProfileImageUrl":      {"s2": "prof_img",      "s3": "profile_image_url"},
        "VoteTypeId":           {"s2": "vote_type_id",  "s3": "vote_type_id"},
        "BountyAmount":         {"s2": "bounty_amt",    "s3": "bounty_amount"},
    },
}


def get_name(db_id: str, original: str, semantic_level: int) -> str:
    """
    Return the column name for the given semantic level.

    semantic_level 1  →  caller generates 'col_a', 'col_b' … externally.
    semantic_level 2  →  abbreviated name (S2).
    semantic_level 3  →  descriptive name (S3).
    semantic_level 4  →  same as S3 (description suffix added by schema_builder).

    Falls back to the original name if no mapping is found.
    """
    level_key = {2: "s2", 3: "s3", 4: "s3"}.get(semantic_level)
    if level_key is None:
        return original
    entry = ALIASES.get(db_id, {}).get(original)
    if entry:
        return entry[level_key]
    return original
