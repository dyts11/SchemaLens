"""
column_aliases.py

Curated S2 (abbreviated) and S3 (descriptive) column-name mappings for every
BIRD dev database.

Design rules:
  - S3  : snake_case version of the ORIGINAL name.  Rule: only columns whose
          original name contains an abbreviation are changed, and only the
          abbreviated token(s) are replaced by their full form — no words are
          added or dropped (GLU -> glucose, AdmFName1 -> administrator_first_name_1,
          MailZip -> mail_zip unchanged apart from casing).
            * `id`, `url`, `zip`, `api` count as ordinary words and stay as is.
            * Proper-noun acronyms are expanded too (VC -> victor_chandler,
              FIFA -> federation_internationale_de_football_association).
            * Anonymous / opaque codes with no meaning in BIRD (A2..A16, IRC,
              PIC, TAT, k_symbol) are expanded from external documentation of
              the source dataset (CDE FRPM data dictionary, PKDD'99 Berka /
              thrombosis data descriptions).
  - S2  : abbreviated version of the ORIGINAL name, built token by token:
            * tokens that are already abbreviations stay as they are, lower-cased
              (cds, dob, LDH -> ldh, B365H -> b365h, A2 -> a2);
            * `id`, `url`, `zip`, `api` and prepositions stay as they are;
            * every full word is replaced from the fixed word tables in
              analysis/summarize_original_column_names.py (S2_GROUP_A/B/C):
                A  conventional abbreviation      (number -> num, date -> dt)
                B  truncation, no conventional one (player -> plyr, team -> tm)
                C  short word, truncated if possible (home -> hm); the six that
                   cannot be shortened stay as is: up, air, eye, sex, pay, mail;
            * only abbreviation, never renaming: token order and count are
              preserved (home_team_goal -> hm_tm_gl, link_to_event -> lnk_to_evt).
          SQL keywords are avoided (description -> descr, interceptions -> intc).
  - S1  : generated automatically (col_a, col_b …) — not stored here.
  - S4  : identical to S3; the description suffix is added by schema_builder.

Structure:
    ALIASES[db_id][original_col_name] = {"s2": ..., "s3": ...}

Every column of the 11 experiment databases (9 BIRD + car_1, tvshow) has an
explicit entry.  Fallback (column not in ALIASES): schema_builder uses the
original name for both S2 and S3; this only applies to databases outside the
experiment set (card_games, codebase_community, wamex), whose blocks below
still follow the older, looser conventions.
"""

ALIASES: dict = {

    # =========================================================================
    # california_schools
    # =========================================================================
    # frpm: descriptive originals; satscores: abbreviated; schools: mixed.
    # =========================================================================
    "california_schools": {
        # ----- frpm -----
        "CDSCode":                        {"s2": "cds_cd",             "s3": "county_district_school_code"},  # also in schools
        "Academic Year":                  {"s2": "acad_yr",            "s3": "academic_year"},
        "County Code":                    {"s2": "cnty_cd",            "s3": "county_code"},
        "District Code":                  {"s2": "dist_cd",            "s3": "district_code"},
        "School Code":                    {"s2": "sch_cd",             "s3": "school_code"},
        "County Name":                    {"s2": "cnty_nm",            "s3": "county_name"},
        "District Name":                  {"s2": "dist_nm",            "s3": "district_name"},
        "School Name":                    {"s2": "sch_nm",             "s3": "school_name"},
        "District Type":                  {"s2": "dist_typ",           "s3": "district_type"},
        "School Type":                    {"s2": "sch_typ",            "s3": "school_type"},
        "Educational Option Type":        {"s2": "edu_opt_typ",        "s3": "educational_option_type"},
        "NSLP Provision Status":          {"s2": "nslp_prov_stat",     "s3": "national_school_lunch_program_provision_status"},
        "Charter School (Y/N)":           {"s2": "chrt_sch_y_n",       "s3": "charter_school_yes_no"},
        "Charter School Number":          {"s2": "chrt_sch_num",       "s3": "charter_school_number"},
        "Charter Funding Type":           {"s2": "chrt_fnd_typ",       "s3": "charter_funding_type"},
        "IRC":                            {"s2": "irc",                "s3": "independently_reporting_charter"},
        "Low Grade":                      {"s2": "lo_grd",             "s3": "low_grade"},
        "High Grade":                     {"s2": "hi_grd",             "s3": "high_grade"},
        "Enrollment (K-12)":              {"s2": "enrl_k_12",          "s3": "enrollment_kindergarten_to_grade_12"},
        "Free Meal Count (K-12)":         {"s2": "fr_ml_cnt_k_12",     "s3": "free_meal_count_kindergarten_to_grade_12"},
        "Percent (%) Eligible Free (K-12)":{"s2": "pct_elig_fr_k_12",   "s3": "percent_eligible_free_kindergarten_to_grade_12"},
        "FRPM Count (K-12)":              {"s2": "frpm_cnt_k_12",      "s3": "free_or_reduced_price_meal_count_kindergarten_to_grade_12"},
        "Percent (%) Eligible FRPM (K-12)":{"s2": "pct_elig_frpm_k_12", "s3": "percent_eligible_free_or_reduced_price_meal_kindergarten_to_grade_12"},
        "Enrollment (Ages 5-17)":         {"s2": "enrl_ags_5_17",      "s3": "enrollment_ages_5_to_17"},
        "Free Meal Count (Ages 5-17)":    {"s2": "fr_ml_cnt_ags_5_17", "s3": "free_meal_count_ages_5_to_17"},
        "Percent (%) Eligible Free (Ages 5-17)":{"s2": "pct_elig_fr_ags_5_17","s3": "percent_eligible_free_ages_5_to_17"},
        "FRPM Count (Ages 5-17)":         {"s2": "frpm_cnt_ags_5_17",  "s3": "free_or_reduced_price_meal_count_ages_5_to_17"},
        "Percent (%) Eligible FRPM (Ages 5-17)":{"s2": "pct_elig_frpm_ags_5_17","s3": "percent_eligible_free_or_reduced_price_meal_ages_5_to_17"},
        "2013-14 CALPADS Fall 1 Certification Status":{"s2": "2013_14_calpads_fll_1_cert_stat","s3": "2013_14_california_longitudinal_pupil_achievement_data_system_fall_1_certification_status"},
        # ----- satscores -----
        "cds":                            {"s2": "cds",                "s3": "county_district_school"},
        "rtype":                          {"s2": "rtype",              "s3": "record_type"},
        "sname":                          {"s2": "sname",              "s3": "school_name"},
        "dname":                          {"s2": "dname",              "s3": "district_name"},
        "cname":                          {"s2": "cname",              "s3": "county_name"},
        "enroll12":                       {"s2": "enroll12",           "s3": "enrollment_12"},
        "NumTstTakr":                     {"s2": "num_tst_takr",       "s3": "number_test_takers"},
        "AvgScrRead":                     {"s2": "avg_scr_rd",         "s3": "average_score_read"},
        "AvgScrMath":                     {"s2": "avg_scr_mth",        "s3": "average_score_math"},
        "AvgScrWrite":                    {"s2": "avg_scr_wr",         "s3": "average_score_write"},
        "NumGE1500":                      {"s2": "num_ge_1500",        "s3": "number_greater_or_equal_1500"},
        # ----- schools -----
        "NCESDist":                       {"s2": "nces_dist",          "s3": "national_center_for_education_statistics_district"},
        "NCESSchool":                     {"s2": "nces_sch",           "s3": "national_center_for_education_statistics_school"},
        "StatusType":                     {"s2": "stat_typ",           "s3": "status_type"},
        "County":                         {"s2": "cnty",               "s3": "county"},
        "District":                       {"s2": "dist",               "s3": "district"},
        "School":                         {"s2": "sch",                "s3": "school"},
        "Street":                         {"s2": "str",                "s3": "street"},
        "StreetAbr":                      {"s2": "str_abr",            "s3": "street_abbreviated"},
        "City":                           {"s2": "cty",                "s3": "city"},
        "Zip":                            {"s2": "zip",                "s3": "zip"},
        "State":                          {"s2": "st",                 "s3": "state"},
        "MailStreet":                     {"s2": "mail_str",           "s3": "mail_street"},
        "MailStrAbr":                     {"s2": "mail_str_abr",       "s3": "mail_street_abbreviated"},
        "MailCity":                       {"s2": "mail_cty",           "s3": "mail_city"},
        "MailZip":                        {"s2": "mail_zip",           "s3": "mail_zip"},
        "MailState":                      {"s2": "mail_st",            "s3": "mail_state"},
        "Phone":                          {"s2": "ph",                 "s3": "phone"},
        "Ext":                            {"s2": "ext",                "s3": "extension"},
        "Website":                        {"s2": "web",                "s3": "website"},
        "OpenDate":                       {"s2": "opn_dt",             "s3": "open_date"},
        "ClosedDate":                     {"s2": "clsd_dt",            "s3": "closed_date"},
        "Charter":                        {"s2": "chrt",               "s3": "charter"},
        "CharterNum":                     {"s2": "chrt_num",           "s3": "charter_number"},
        "FundingType":                    {"s2": "fnd_typ",            "s3": "funding_type"},
        "DOC":                            {"s2": "doc",                "s3": "district_ownership_code"},
        "DOCType":                        {"s2": "doc_typ",            "s3": "district_ownership_type"},
        "SOC":                            {"s2": "soc",                "s3": "school_ownership_code"},
        "SOCType":                        {"s2": "soc_typ",            "s3": "school_ownership_type"},
        "EdOpsCode":                      {"s2": "ed_ops_cd",          "s3": "educational_option_code"},
        "EdOpsName":                      {"s2": "ed_ops_nm",          "s3": "educational_option_name"},
        "EILCode":                        {"s2": "eil_cd",             "s3": "educational_instruction_level_code"},
        "EILName":                        {"s2": "eil_nm",             "s3": "educational_instruction_level_name"},
        "GSoffered":                      {"s2": "gs_offd",            "s3": "grade_span_offered"},
        "GSserved":                       {"s2": "gs_srvd",            "s3": "grade_span_served"},
        "Virtual":                        {"s2": "virt",               "s3": "virtual"},
        "Magnet":                         {"s2": "mgnt",               "s3": "magnet"},
        "Latitude":                       {"s2": "lat",                "s3": "latitude"},
        "Longitude":                      {"s2": "lng",                "s3": "longitude"},
        "AdmFName1":                      {"s2": "adm_f_nm_1",         "s3": "administrator_first_name_1"},
        "AdmLName1":                      {"s2": "adm_l_nm_1",         "s3": "administrator_last_name_1"},
        "AdmEmail1":                      {"s2": "adm_eml_1",          "s3": "administrator_email_1"},
        "AdmFName2":                      {"s2": "adm_f_nm_2",         "s3": "administrator_first_name_2"},
        "AdmLName2":                      {"s2": "adm_l_nm_2",         "s3": "administrator_last_name_2"},
        "AdmEmail2":                      {"s2": "adm_eml_2",          "s3": "administrator_email_2"},
        "AdmFName3":                      {"s2": "adm_f_nm_3",         "s3": "administrator_first_name_3"},
        "AdmLName3":                      {"s2": "adm_l_nm_3",         "s3": "administrator_last_name_3"},
        "AdmEmail3":                      {"s2": "adm_eml_3",          "s3": "administrator_email_3"},
        "LastUpdate":                     {"s2": "lst_upd",            "s3": "last_update"},
    },

    # =========================================================================
    # financial
    # =========================================================================
    # district.A2–A16 are anonymous codes: S2 keeps the code, S3 expands from
    # the Berka dataset description.
    # =========================================================================
    "financial": {
        # ----- account -----
        "account_id":                     {"s2": "acct_id",            "s3": "account_id"},  # also in disp, loan, order, trans
        "district_id":                    {"s2": "dist_id",            "s3": "district_id"},  # also in client, district
        "frequency":                      {"s2": "freq",               "s3": "frequency"},
        "date":                           {"s2": "dt",                 "s3": "date"},  # also in loan, trans
        # ----- card -----
        "card_id":                        {"s2": "crd_id",             "s3": "card_id"},
        "disp_id":                        {"s2": "disp_id",            "s3": "disposition_id"},  # also in disp
        "type":                           {"s2": "typ",                "s3": "type"},  # also in disp, trans
        "issued":                         {"s2": "issd",               "s3": "issued"},
        # ----- client -----
        "client_id":                      {"s2": "clt_id",             "s3": "client_id"},  # also in disp
        "gender":                         {"s2": "gndr",               "s3": "gender"},
        "birth_date":                     {"s2": "brth_dt",            "s3": "birth_date"},
        # ----- disp -----
        # ----- district -----
        "A2":                             {"s2": "a2",                 "s3": "district_name"},
        "A3":                             {"s2": "a3",                 "s3": "region"},
        "A4":                             {"s2": "a4",                 "s3": "number_inhabitants"},
        "A5":                             {"s2": "a5",                 "s3": "number_municipalities_below_499"},
        "A6":                             {"s2": "a6",                 "s3": "number_municipalities_500_to_1999"},
        "A7":                             {"s2": "a7",                 "s3": "number_municipalities_2000_to_9999"},
        "A8":                             {"s2": "a8",                 "s3": "number_municipalities_above_10000"},
        "A9":                             {"s2": "a9",                 "s3": "number_cities"},
        "A10":                            {"s2": "a10",                "s3": "urban_inhabitant_ratio"},
        "A11":                            {"s2": "a11",                "s3": "average_salary"},
        "A12":                            {"s2": "a12",                "s3": "unemployment_rate_1995"},
        "A13":                            {"s2": "a13",                "s3": "unemployment_rate_1996"},
        "A14":                            {"s2": "a14",                "s3": "entrepreneurs_per_1000"},
        "A15":                            {"s2": "a15",                "s3": "number_crimes_1995"},
        "A16":                            {"s2": "a16",                "s3": "number_crimes_1996"},
        # ----- loan -----
        "loan_id":                        {"s2": "ln_id",              "s3": "loan_id"},
        "amount":                         {"s2": "amt",                "s3": "amount"},  # also in order, trans
        "duration":                       {"s2": "dur",                "s3": "duration"},
        "payments":                       {"s2": "pmts",               "s3": "payments"},
        "status":                         {"s2": "stat",               "s3": "status"},
        # ----- order -----
        "order_id":                       {"s2": "ord_id",             "s3": "order_id"},
        "bank_to":                        {"s2": "bnk_to",             "s3": "bank_to"},
        "account_to":                     {"s2": "acct_to",            "s3": "account_to"},
        "k_symbol":                       {"s2": "k_sym",              "s3": "constant_symbol"},  # also in trans
        # ----- trans -----
        "trans_id":                       {"s2": "trans_id",           "s3": "transaction_id"},
        "operation":                      {"s2": "op",                 "s3": "operation"},
        "balance":                        {"s2": "bal",                "s3": "balance"},
        "bank":                           {"s2": "bnk",                "s3": "bank"},
        "account":                        {"s2": "acct",               "s3": "account"},
    },

    # =========================================================================
    # thrombosis_prediction
    # =========================================================================
    # Laboratory / Examination columns are medical abbreviations: S2 keeps them,
    # S3 expands them (BIRD description, else PKDD'99 data description).
    # =========================================================================
    "thrombosis_prediction": {
        # ----- Examination -----
        "ID":                             {"s2": "id",                 "s3": "id"},  # also in Patient, Laboratory
        "Examination Date":               {"s2": "exam_dt",            "s3": "examination_date"},
        "aCL IgG":                        {"s2": "acl_igg",            "s3": "anticardiolipin_immunoglobulin_g"},
        "aCL IgM":                        {"s2": "acl_igm",            "s3": "anticardiolipin_immunoglobulin_m"},
        "ANA":                            {"s2": "ana",                "s3": "antinuclear_antibody"},
        "ANA Pattern":                    {"s2": "ana_ptrn",           "s3": "antinuclear_antibody_pattern"},
        "aCL IgA":                        {"s2": "acl_iga",            "s3": "anticardiolipin_immunoglobulin_a"},
        "Diagnosis":                      {"s2": "diag",               "s3": "diagnosis"},  # also in Patient
        "KCT":                            {"s2": "kct",                "s3": "kaolin_clotting_time"},
        "RVVT":                           {"s2": "rvvt",               "s3": "russell_viper_venom_time"},
        "LAC":                            {"s2": "lac",                "s3": "lupus_anticoagulant"},
        "Symptoms":                       {"s2": "symp",               "s3": "symptoms"},
        "Thrombosis":                     {"s2": "thrmb",              "s3": "thrombosis"},
        # ----- Patient -----
        "SEX":                            {"s2": "sex",                "s3": "sex"},
        "Birthday":                       {"s2": "bday",               "s3": "birthday"},
        "Description":                    {"s2": "descr",              "s3": "description"},
        "First Date":                     {"s2": "fst_dt",             "s3": "first_date"},
        "Admission":                      {"s2": "adm",                "s3": "admission"},
        # ----- Laboratory -----
        "Date":                           {"s2": "dt",                 "s3": "date"},
        "GOT":                            {"s2": "got",                "s3": "glutamic_oxaloacetic_transaminase"},
        "GPT":                            {"s2": "gpt",                "s3": "glutamic_pyruvic_transaminase"},
        "LDH":                            {"s2": "ldh",                "s3": "lactate_dehydrogenase"},
        "ALP":                            {"s2": "alp",                "s3": "alkaline_phosphatase"},
        "TP":                             {"s2": "tp",                 "s3": "total_protein"},
        "ALB":                            {"s2": "alb",                "s3": "albumin"},
        "UA":                             {"s2": "ua",                 "s3": "uric_acid"},
        "UN":                             {"s2": "un",                 "s3": "urea_nitrogen"},
        "CRE":                            {"s2": "cre",                "s3": "creatinine"},
        "T-BIL":                          {"s2": "t_bil",              "s3": "total_bilirubin"},
        "T-CHO":                          {"s2": "t_cho",              "s3": "total_cholesterol"},
        "TG":                             {"s2": "tg",                 "s3": "triglyceride"},
        "CPK":                            {"s2": "cpk",                "s3": "creatinine_phosphokinase"},
        "GLU":                            {"s2": "glu",                "s3": "glucose"},
        "WBC":                            {"s2": "wbc",                "s3": "white_blood_cell"},
        "RBC":                            {"s2": "rbc",                "s3": "red_blood_cell"},
        "HGB":                            {"s2": "hgb",                "s3": "hemoglobin"},
        "HCT":                            {"s2": "hct",                "s3": "hematocrit"},
        "PLT":                            {"s2": "plt",                "s3": "platelet"},
        "PT":                             {"s2": "pt",                 "s3": "prothrombin_time"},
        "APTT":                           {"s2": "aptt",               "s3": "activated_partial_thromboplastin_time"},
        "FG":                             {"s2": "fg",                 "s3": "fibrinogen"},
        "PIC":                            {"s2": "pic",                "s3": "plasmin_alpha2_plasmin_inhibitor_complex"},
        "TAT":                            {"s2": "tat",                "s3": "thrombin_antithrombin_complex"},
        "TAT2":                           {"s2": "tat2",               "s3": "thrombin_antithrombin_complex_2"},
        "U-PRO":                          {"s2": "u_pro",              "s3": "urine_protein"},
        "IGG":                            {"s2": "igg",                "s3": "immunoglobulin_g"},
        "IGA":                            {"s2": "iga",                "s3": "immunoglobulin_a"},
        "IGM":                            {"s2": "igm",                "s3": "immunoglobulin_m"},
        "CRP":                            {"s2": "crp",                "s3": "c_reactive_protein"},
        "RA":                             {"s2": "ra",                 "s3": "rheumatoid_factor"},
        "RF":                             {"s2": "rf",                 "s3": "rheumatoid_arthritis_hemagglutination"},
        "C3":                             {"s2": "c3",                 "s3": "complement_3"},
        "C4":                             {"s2": "c4",                 "s3": "complement_4"},
        "RNP":                            {"s2": "rnp",                "s3": "anti_ribonucleoprotein"},
        "SM":                             {"s2": "sm",                 "s3": "anti_smith"},
        "SC170":                          {"s2": "sc170",              "s3": "anti_scleroderma_70"},
        "SSA":                            {"s2": "ssa",                "s3": "anti_sjogren_syndrome_a"},
        "SSB":                            {"s2": "ssb",                "s3": "anti_sjogren_syndrome_b"},
        "CENTROMEA":                      {"s2": "centromea",          "s3": "anti_centromere"},
        "DNA":                            {"s2": "dna",                "s3": "anti_deoxyribonucleic_acid"},
        "DNA-II":                         {"s2": "dna_ii",             "s3": "anti_deoxyribonucleic_acid_ii"},
    },

    # =========================================================================
    # formula_1
    # =========================================================================
    # Most columns are already S3-quality (camelCase readable).
    # A handful are abbreviated: lat/lng/alt/dob/circuitRef/driverRef/q1-q3.
    # Add S2 downgrades for the already-descriptive columns too.
    # =========================================================================
    "formula_1": {
        # ----- circuits -----
        "circuitId":                      {"s2": "cir_id",             "s3": "circuit_id"},  # also in races
        "circuitRef":                     {"s2": "cir_ref",            "s3": "circuit_reference"},
        "name":                           {"s2": "nm",                 "s3": "name"},  # also in constructors, races
        "location":                       {"s2": "loc",                "s3": "location"},
        "country":                        {"s2": "ctry",               "s3": "country"},
        "lat":                            {"s2": "lat",                "s3": "latitude"},
        "lng":                            {"s2": "lng",                "s3": "longitude"},
        "alt":                            {"s2": "alt",                "s3": "altitude"},
        # ----- constructors -----
        "constructorId":                  {"s2": "ctor_id",            "s3": "constructor_id"},  # also in constructorResults, constructorStandings, qualifying, results
        "constructorRef":                 {"s2": "ctor_ref",           "s3": "constructor_reference"},
        "nationality":                    {"s2": "nat",                "s3": "nationality"},  # also in drivers
        # ----- drivers -----
        "driverId":                       {"s2": "drv_id",             "s3": "driver_id"},  # also in driverStandings, lapTimes, pitStops, qualifying, results
        "driverRef":                      {"s2": "drv_ref",            "s3": "driver_reference"},
        "number":                         {"s2": "num",                "s3": "number"},  # also in qualifying, results
        "code":                           {"s2": "cd",                 "s3": "code"},
        "forename":                       {"s2": "fname",              "s3": "forename"},
        "surname":                        {"s2": "sname",              "s3": "surname"},
        "dob":                            {"s2": "dob",                "s3": "date_of_birth"},
        # ----- seasons -----
        "year":                           {"s2": "yr",                 "s3": "year"},  # also in races
        # ----- races -----
        "raceId":                         {"s2": "rc_id",              "s3": "race_id"},  # also in constructorResults, constructorStandings, driverStandings, lapTimes, pitStops, qualifying, results
        "round":                          {"s2": "rnd",                "s3": "round"},
        "date":                           {"s2": "dt",                 "s3": "date"},
        "time":                           {"s2": "tm",                 "s3": "time"},  # also in lapTimes, pitStops, results
        # ----- constructorResults -----
        "constructorResultsId":           {"s2": "ctor_res_id",        "s3": "constructor_results_id"},
        "points":                         {"s2": "pts",                "s3": "points"},  # also in constructorStandings, driverStandings, results
        "status":                         {"s2": "stat",               "s3": "status"},  # also in status
        # ----- constructorStandings -----
        "constructorStandingsId":         {"s2": "ctor_stnd_id",       "s3": "constructor_standings_id"},
        "position":                       {"s2": "pos",                "s3": "position"},  # also in driverStandings, lapTimes, qualifying, results
        "positionText":                   {"s2": "pos_txt",            "s3": "position_text"},  # also in driverStandings, results
        "wins":                           {"s2": "wns",                "s3": "wins"},  # also in driverStandings
        # ----- driverStandings -----
        "driverStandingsId":              {"s2": "drv_stnd_id",        "s3": "driver_standings_id"},
        # ----- lapTimes -----
        "lap":                            {"s2": "lp",                 "s3": "lap"},  # also in pitStops
        "milliseconds":                   {"s2": "ms",                 "s3": "milliseconds"},  # also in pitStops, results
        # ----- pitStops -----
        "stop":                           {"s2": "stp",                "s3": "stop"},
        "duration":                       {"s2": "dur",                "s3": "duration"},
        # ----- qualifying -----
        "qualifyId":                      {"s2": "qual_id",            "s3": "qualify_id"},
        "q1":                             {"s2": "q1",                 "s3": "qualifying_1"},
        "q2":                             {"s2": "q2",                 "s3": "qualifying_2"},
        "q3":                             {"s2": "q3",                 "s3": "qualifying_3"},
        # ----- status -----
        "statusId":                       {"s2": "stat_id",            "s3": "status_id"},  # also in results
        # ----- results -----
        "resultId":                       {"s2": "res_id",             "s3": "result_id"},
        "grid":                           {"s2": "grd",                "s3": "grid"},
        "positionOrder":                  {"s2": "pos_ord",            "s3": "position_order"},
        "laps":                           {"s2": "lps",                "s3": "laps"},
        "fastestLap":                     {"s2": "fast_lp",            "s3": "fastest_lap"},
        "rank":                           {"s2": "rnk",                "s3": "rank"},
        "fastestLapTime":                 {"s2": "fast_lp_tm",         "s3": "fastest_lap_time"},
        "fastestLapSpeed":                {"s2": "fast_lp_spd",        "s3": "fastest_lap_speed"},
    },

    # =========================================================================
    # european_football_2
    # =========================================================================
    # Player / Player_Attributes / Team / Team_Attributes / League / Country
    # are S3-quality (snake_case descriptive).  The Match table has betting
    # odds codes (B365H, BWH …) that are S2.
    # =========================================================================
    "european_football_2": {
        # ----- Player_Attributes -----
        "player_fifa_api_id":             {"s2": "plyr_fifa_api_id",   "s3": "player_federation_internationale_de_football_association_api_id"},  # also in Player
        "player_api_id":                  {"s2": "plyr_api_id",        "s3": "player_api_id"},  # also in Player
        "date":                           {"s2": "dt",                 "s3": "date"},  # also in Team_Attributes, Match
        "overall_rating":                 {"s2": "ovr_rtg",            "s3": "overall_rating"},
        "potential":                      {"s2": "pot",                "s3": "potential"},
        "preferred_foot":                 {"s2": "pref_ft",            "s3": "preferred_foot"},
        "attacking_work_rate":            {"s2": "atk_wrk_rt",         "s3": "attacking_work_rate"},
        "defensive_work_rate":            {"s2": "def_wrk_rt",         "s3": "defensive_work_rate"},
        "crossing":                       {"s2": "crss",               "s3": "crossing"},
        "finishing":                      {"s2": "fnsh",               "s3": "finishing"},
        "heading_accuracy":               {"s2": "hdg_acc",            "s3": "heading_accuracy"},
        "short_passing":                  {"s2": "sht_pass",           "s3": "short_passing"},
        "volleys":                        {"s2": "vly",                "s3": "volleys"},
        "dribbling":                      {"s2": "drbl",               "s3": "dribbling"},
        "curve":                          {"s2": "crv",                "s3": "curve"},
        "free_kick_accuracy":             {"s2": "fr_kck_acc",         "s3": "free_kick_accuracy"},
        "long_passing":                   {"s2": "lng_pass",           "s3": "long_passing"},
        "ball_control":                   {"s2": "bl_ctrl",            "s3": "ball_control"},
        "acceleration":                   {"s2": "accel",              "s3": "acceleration"},
        "sprint_speed":                   {"s2": "sprt_spd",           "s3": "sprint_speed"},
        "agility":                        {"s2": "agil",               "s3": "agility"},
        "reactions":                      {"s2": "rctn",               "s3": "reactions"},
        "balance":                        {"s2": "bal",                "s3": "balance"},
        "shot_power":                     {"s2": "sht_pwr",            "s3": "shot_power"},
        "jumping":                        {"s2": "jmp",                "s3": "jumping"},
        "stamina":                        {"s2": "stam",               "s3": "stamina"},
        "strength":                       {"s2": "strn",               "s3": "strength"},
        "long_shots":                     {"s2": "lng_shts",           "s3": "long_shots"},
        "aggression":                     {"s2": "aggr",               "s3": "aggression"},
        "interceptions":                  {"s2": "intc",               "s3": "interceptions"},
        "positioning":                    {"s2": "pos",                "s3": "positioning"},
        "vision":                         {"s2": "vis",                "s3": "vision"},
        "penalties":                      {"s2": "pen",                "s3": "penalties"},
        "marking":                        {"s2": "mrk",                "s3": "marking"},
        "standing_tackle":                {"s2": "stdg_tkl",           "s3": "standing_tackle"},
        "sliding_tackle":                 {"s2": "sld_tkl",            "s3": "sliding_tackle"},
        "gk_diving":                      {"s2": "gk_dvg",             "s3": "goalkeeper_diving"},
        "gk_handling":                    {"s2": "gk_hndl",            "s3": "goalkeeper_handling"},
        "gk_kicking":                     {"s2": "gk_kckg",            "s3": "goalkeeper_kicking"},
        "gk_positioning":                 {"s2": "gk_pos",             "s3": "goalkeeper_positioning"},
        "gk_reflexes":                    {"s2": "gk_rflx",            "s3": "goalkeeper_reflexes"},
        # ----- Player -----
        "player_name":                    {"s2": "plyr_nm",            "s3": "player_name"},
        "birthday":                       {"s2": "bday",               "s3": "birthday"},
        "height":                         {"s2": "ht",                 "s3": "height"},
        "weight":                         {"s2": "wt",                 "s3": "weight"},
        # ----- League -----
        "country_id":                     {"s2": "ctry_id",            "s3": "country_id"},  # also in Match
        "name":                           {"s2": "nm",                 "s3": "name"},  # also in Country
        # ----- Country -----
        # ----- Team -----
        "team_api_id":                    {"s2": "tm_api_id",          "s3": "team_api_id"},  # also in Team_Attributes
        "team_fifa_api_id":               {"s2": "tm_fifa_api_id",     "s3": "team_federation_internationale_de_football_association_api_id"},  # also in Team_Attributes
        "team_long_name":                 {"s2": "tm_lng_nm",          "s3": "team_long_name"},
        "team_short_name":                {"s2": "tm_sht_nm",          "s3": "team_short_name"},
        # ----- Team_Attributes -----
        "buildUpPlaySpeed":               {"s2": "bld_up_ply_spd",     "s3": "build_up_play_speed"},
        "buildUpPlaySpeedClass":          {"s2": "bld_up_ply_spd_cls", "s3": "build_up_play_speed_class"},
        "buildUpPlayDribbling":           {"s2": "bld_up_ply_drbl",    "s3": "build_up_play_dribbling"},
        "buildUpPlayDribblingClass":      {"s2": "bld_up_ply_drbl_cls","s3": "build_up_play_dribbling_class"},
        "buildUpPlayPassing":             {"s2": "bld_up_ply_pass",    "s3": "build_up_play_passing"},
        "buildUpPlayPassingClass":        {"s2": "bld_up_ply_pass_cls","s3": "build_up_play_passing_class"},
        "buildUpPlayPositioningClass":    {"s2": "bld_up_ply_pos_cls", "s3": "build_up_play_positioning_class"},
        "chanceCreationPassing":          {"s2": "chnc_crtn_pass",     "s3": "chance_creation_passing"},
        "chanceCreationPassingClass":     {"s2": "chnc_crtn_pass_cls", "s3": "chance_creation_passing_class"},
        "chanceCreationCrossing":         {"s2": "chnc_crtn_crss",     "s3": "chance_creation_crossing"},
        "chanceCreationCrossingClass":    {"s2": "chnc_crtn_crss_cls", "s3": "chance_creation_crossing_class"},
        "chanceCreationShooting":         {"s2": "chnc_crtn_shtg",     "s3": "chance_creation_shooting"},
        "chanceCreationShootingClass":    {"s2": "chnc_crtn_shtg_cls", "s3": "chance_creation_shooting_class"},
        "chanceCreationPositioningClass": {"s2": "chnc_crtn_pos_cls",  "s3": "chance_creation_positioning_class"},
        "defencePressure":                {"s2": "def_prss",           "s3": "defence_pressure"},
        "defencePressureClass":           {"s2": "def_prss_cls",       "s3": "defence_pressure_class"},
        "defenceAggression":              {"s2": "def_aggr",           "s3": "defence_aggression"},
        "defenceAggressionClass":         {"s2": "def_aggr_cls",       "s3": "defence_aggression_class"},
        "defenceTeamWidth":               {"s2": "def_tm_wdth",        "s3": "defence_team_width"},
        "defenceTeamWidthClass":          {"s2": "def_tm_wdth_cls",    "s3": "defence_team_width_class"},
        "defenceDefenderLineClass":       {"s2": "def_dfndr_lin_cls",  "s3": "defence_defender_line_class"},
        # ----- Match -----
        "league_id":                      {"s2": "lg_id",              "s3": "league_id"},
        "season":                         {"s2": "ssn",                "s3": "season"},
        "stage":                          {"s2": "stg",                "s3": "stage"},
        "match_api_id":                   {"s2": "mtch_api_id",        "s3": "match_api_id"},
        "home_team_api_id":               {"s2": "hm_tm_api_id",       "s3": "home_team_api_id"},
        "away_team_api_id":               {"s2": "aw_tm_api_id",       "s3": "away_team_api_id"},
        "home_team_goal":                 {"s2": "hm_tm_gl",           "s3": "home_team_goal"},
        "away_team_goal":                 {"s2": "aw_tm_gl",           "s3": "away_team_goal"},
        "home_player_X1":                 {"s2": "hm_plyr_x1",         "s3": "home_player_x1"},
        "home_player_X2":                 {"s2": "hm_plyr_x2",         "s3": "home_player_x2"},
        "home_player_X3":                 {"s2": "hm_plyr_x3",         "s3": "home_player_x3"},
        "home_player_X4":                 {"s2": "hm_plyr_x4",         "s3": "home_player_x4"},
        "home_player_X5":                 {"s2": "hm_plyr_x5",         "s3": "home_player_x5"},
        "home_player_X6":                 {"s2": "hm_plyr_x6",         "s3": "home_player_x6"},
        "home_player_X7":                 {"s2": "hm_plyr_x7",         "s3": "home_player_x7"},
        "home_player_X8":                 {"s2": "hm_plyr_x8",         "s3": "home_player_x8"},
        "home_player_X9":                 {"s2": "hm_plyr_x9",         "s3": "home_player_x9"},
        "home_player_X10":                {"s2": "hm_plyr_x10",        "s3": "home_player_x10"},
        "home_player_X11":                {"s2": "hm_plyr_x11",        "s3": "home_player_x11"},
        "away_player_X1":                 {"s2": "aw_plyr_x1",         "s3": "away_player_x1"},
        "away_player_X2":                 {"s2": "aw_plyr_x2",         "s3": "away_player_x2"},
        "away_player_X3":                 {"s2": "aw_plyr_x3",         "s3": "away_player_x3"},
        "away_player_X4":                 {"s2": "aw_plyr_x4",         "s3": "away_player_x4"},
        "away_player_X5":                 {"s2": "aw_plyr_x5",         "s3": "away_player_x5"},
        "away_player_X6":                 {"s2": "aw_plyr_x6",         "s3": "away_player_x6"},
        "away_player_X7":                 {"s2": "aw_plyr_x7",         "s3": "away_player_x7"},
        "away_player_X8":                 {"s2": "aw_plyr_x8",         "s3": "away_player_x8"},
        "away_player_X9":                 {"s2": "aw_plyr_x9",         "s3": "away_player_x9"},
        "away_player_X10":                {"s2": "aw_plyr_x10",        "s3": "away_player_x10"},
        "away_player_X11":                {"s2": "aw_plyr_x11",        "s3": "away_player_x11"},
        "home_player_Y1":                 {"s2": "hm_plyr_y1",         "s3": "home_player_y1"},
        "home_player_Y2":                 {"s2": "hm_plyr_y2",         "s3": "home_player_y2"},
        "home_player_Y3":                 {"s2": "hm_plyr_y3",         "s3": "home_player_y3"},
        "home_player_Y4":                 {"s2": "hm_plyr_y4",         "s3": "home_player_y4"},
        "home_player_Y5":                 {"s2": "hm_plyr_y5",         "s3": "home_player_y5"},
        "home_player_Y6":                 {"s2": "hm_plyr_y6",         "s3": "home_player_y6"},
        "home_player_Y7":                 {"s2": "hm_plyr_y7",         "s3": "home_player_y7"},
        "home_player_Y8":                 {"s2": "hm_plyr_y8",         "s3": "home_player_y8"},
        "home_player_Y9":                 {"s2": "hm_plyr_y9",         "s3": "home_player_y9"},
        "home_player_Y10":                {"s2": "hm_plyr_y10",        "s3": "home_player_y10"},
        "home_player_Y11":                {"s2": "hm_plyr_y11",        "s3": "home_player_y11"},
        "away_player_Y1":                 {"s2": "aw_plyr_y1",         "s3": "away_player_y1"},
        "away_player_Y2":                 {"s2": "aw_plyr_y2",         "s3": "away_player_y2"},
        "away_player_Y3":                 {"s2": "aw_plyr_y3",         "s3": "away_player_y3"},
        "away_player_Y4":                 {"s2": "aw_plyr_y4",         "s3": "away_player_y4"},
        "away_player_Y5":                 {"s2": "aw_plyr_y5",         "s3": "away_player_y5"},
        "away_player_Y6":                 {"s2": "aw_plyr_y6",         "s3": "away_player_y6"},
        "away_player_Y7":                 {"s2": "aw_plyr_y7",         "s3": "away_player_y7"},
        "away_player_Y8":                 {"s2": "aw_plyr_y8",         "s3": "away_player_y8"},
        "away_player_Y9":                 {"s2": "aw_plyr_y9",         "s3": "away_player_y9"},
        "away_player_Y10":                {"s2": "aw_plyr_y10",        "s3": "away_player_y10"},
        "away_player_Y11":                {"s2": "aw_plyr_y11",        "s3": "away_player_y11"},
        "home_player_1":                  {"s2": "hm_plyr_1",          "s3": "home_player_1"},
        "home_player_2":                  {"s2": "hm_plyr_2",          "s3": "home_player_2"},
        "home_player_3":                  {"s2": "hm_plyr_3",          "s3": "home_player_3"},
        "home_player_4":                  {"s2": "hm_plyr_4",          "s3": "home_player_4"},
        "home_player_5":                  {"s2": "hm_plyr_5",          "s3": "home_player_5"},
        "home_player_6":                  {"s2": "hm_plyr_6",          "s3": "home_player_6"},
        "home_player_7":                  {"s2": "hm_plyr_7",          "s3": "home_player_7"},
        "home_player_8":                  {"s2": "hm_plyr_8",          "s3": "home_player_8"},
        "home_player_9":                  {"s2": "hm_plyr_9",          "s3": "home_player_9"},
        "home_player_10":                 {"s2": "hm_plyr_10",         "s3": "home_player_10"},
        "home_player_11":                 {"s2": "hm_plyr_11",         "s3": "home_player_11"},
        "away_player_1":                  {"s2": "aw_plyr_1",          "s3": "away_player_1"},
        "away_player_2":                  {"s2": "aw_plyr_2",          "s3": "away_player_2"},
        "away_player_3":                  {"s2": "aw_plyr_3",          "s3": "away_player_3"},
        "away_player_4":                  {"s2": "aw_plyr_4",          "s3": "away_player_4"},
        "away_player_5":                  {"s2": "aw_plyr_5",          "s3": "away_player_5"},
        "away_player_6":                  {"s2": "aw_plyr_6",          "s3": "away_player_6"},
        "away_player_7":                  {"s2": "aw_plyr_7",          "s3": "away_player_7"},
        "away_player_8":                  {"s2": "aw_plyr_8",          "s3": "away_player_8"},
        "away_player_9":                  {"s2": "aw_plyr_9",          "s3": "away_player_9"},
        "away_player_10":                 {"s2": "aw_plyr_10",         "s3": "away_player_10"},
        "away_player_11":                 {"s2": "aw_plyr_11",         "s3": "away_player_11"},
        "goal":                           {"s2": "gl",                 "s3": "goal"},
        "shoton":                         {"s2": "shoton",             "s3": "shot_on"},
        "shotoff":                        {"s2": "shotoff",            "s3": "shot_off"},
        "foulcommit":                     {"s2": "foulcommit",         "s3": "foul_commit"},
        "card":                           {"s2": "crd",                "s3": "card"},
        "cross":                          {"s2": "crs",                "s3": "cross"},
        "corner":                         {"s2": "cnr",                "s3": "corner"},
        "possession":                     {"s2": "poss",               "s3": "possession"},
        "B365H":                          {"s2": "b_365_h",            "s3": "bet365_home_odds"},
        "B365D":                          {"s2": "b_365_d",            "s3": "bet365_draw_odds"},
        "B365A":                          {"s2": "b_365_a",            "s3": "bet365_away_odds"},
        "BWH":                            {"s2": "bwh",                "s3": "bwin_home_odds"},
        "BWD":                            {"s2": "bwd",                "s3": "bwin_draw_odds"},
        "BWA":                            {"s2": "bwa",                "s3": "bwin_away_odds"},
        "IWH":                            {"s2": "iwh",                "s3": "interwetten_home_odds"},
        "IWD":                            {"s2": "iwd",                "s3": "interwetten_draw_odds"},
        "IWA":                            {"s2": "iwa",                "s3": "interwetten_away_odds"},
        "LBH":                            {"s2": "lbh",                "s3": "ladbrokes_home_odds"},
        "LBD":                            {"s2": "lbd",                "s3": "ladbrokes_draw_odds"},
        "LBA":                            {"s2": "lba",                "s3": "ladbrokes_away_odds"},
        "PSH":                            {"s2": "psh",                "s3": "pinnacle_sports_home_odds"},
        "PSD":                            {"s2": "psd",                "s3": "pinnacle_sports_draw_odds"},
        "PSA":                            {"s2": "psa",                "s3": "pinnacle_sports_away_odds"},
        "WHH":                            {"s2": "whh",                "s3": "william_hill_home_odds"},
        "WHD":                            {"s2": "whd",                "s3": "william_hill_draw_odds"},
        "WHA":                            {"s2": "wha",                "s3": "william_hill_away_odds"},
        "SJH":                            {"s2": "sjh",                "s3": "stan_james_home_odds"},
        "SJD":                            {"s2": "sjd",                "s3": "stan_james_draw_odds"},
        "SJA":                            {"s2": "sja",                "s3": "stan_james_away_odds"},
        "VCH":                            {"s2": "vch",                "s3": "victor_chandler_home_odds"},
        "VCD":                            {"s2": "vcd",                "s3": "victor_chandler_draw_odds"},
        "VCA":                            {"s2": "vca",                "s3": "victor_chandler_away_odds"},
        "GBH":                            {"s2": "gbh",                "s3": "gamebookers_home_odds"},
        "GBD":                            {"s2": "gbd",                "s3": "gamebookers_draw_odds"},
        "GBA":                            {"s2": "gba",                "s3": "gamebookers_away_odds"},
        "BSH":                            {"s2": "bsh",                "s3": "blue_square_home_odds"},
        "BSD":                            {"s2": "bsd",                "s3": "blue_square_draw_odds"},
        "BSA":                            {"s2": "bsa",                "s3": "blue_square_away_odds"},
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
    # student_club
    # =========================================================================
    "student_club": {
        # ----- event -----
        "event_id":                       {"s2": "evt_id",             "s3": "event_id"},
        "event_name":                     {"s2": "evt_nm",             "s3": "event_name"},
        "event_date":                     {"s2": "evt_dt",             "s3": "event_date"},
        "type":                           {"s2": "typ",                "s3": "type"},  # also in zip_code
        "notes":                          {"s2": "nts",                "s3": "notes"},  # also in income
        "location":                       {"s2": "loc",                "s3": "location"},
        "status":                         {"s2": "stat",               "s3": "status"},
        # ----- major -----
        "major_id":                       {"s2": "maj_id",             "s3": "major_id"},
        "major_name":                     {"s2": "maj_nm",             "s3": "major_name"},
        "department":                     {"s2": "dept",               "s3": "department"},
        "college":                        {"s2": "coll",               "s3": "college"},
        # ----- zip_code -----
        "zip_code":                       {"s2": "zip_cd",             "s3": "zip_code"},
        "city":                           {"s2": "cty",                "s3": "city"},
        "county":                         {"s2": "cnty",               "s3": "county"},
        "state":                          {"s2": "st",                 "s3": "state"},
        "short_state":                    {"s2": "sht_st",             "s3": "short_state"},
        # ----- attendance -----
        "link_to_event":                  {"s2": "lnk_to_evt",         "s3": "link_to_event"},  # also in budget
        "link_to_member":                 {"s2": "lnk_to_mbr",         "s3": "link_to_member"},  # also in expense, income
        # ----- budget -----
        "budget_id":                      {"s2": "bdgt_id",            "s3": "budget_id"},
        "category":                       {"s2": "cat",                "s3": "category"},
        "spent":                          {"s2": "spnt",               "s3": "spent"},
        "remaining":                      {"s2": "rmn",                "s3": "remaining"},
        "amount":                         {"s2": "amt",                "s3": "amount"},  # also in income
        "event_status":                   {"s2": "evt_stat",           "s3": "event_status"},
        # ----- expense -----
        "expense_id":                     {"s2": "exp_id",             "s3": "expense_id"},
        "expense_description":            {"s2": "exp_descr",          "s3": "expense_description"},
        "expense_date":                   {"s2": "exp_dt",             "s3": "expense_date"},
        "cost":                           {"s2": "cst",                "s3": "cost"},
        "approved":                       {"s2": "apprv",              "s3": "approved"},
        "link_to_budget":                 {"s2": "lnk_to_bdgt",        "s3": "link_to_budget"},
        # ----- income -----
        "income_id":                      {"s2": "inc_id",             "s3": "income_id"},
        "date_received":                  {"s2": "dt_rcvd",            "s3": "date_received"},
        "source":                         {"s2": "src",                "s3": "source"},
        # ----- member -----
        "member_id":                      {"s2": "mbr_id",             "s3": "member_id"},
        "first_name":                     {"s2": "fst_nm",             "s3": "first_name"},
        "last_name":                      {"s2": "lst_nm",             "s3": "last_name"},
        "email":                          {"s2": "eml",                "s3": "email"},
        "position":                       {"s2": "pos",                "s3": "position"},
        "t_shirt_size":                   {"s2": "t_shrt_sz",          "s3": "t_shirt_size"},
        "phone":                          {"s2": "ph",                 "s3": "phone"},
        "zip":                            {"s2": "zip",                "s3": "zip"},
        "link_to_major":                  {"s2": "lnk_to_maj",         "s3": "link_to_major"},
    },

    # =========================================================================
    # superhero
    # =========================================================================
    "superhero": {
        # ----- alignment -----
        "alignment":                      {"s2": "algn",               "s3": "alignment"},
        # ----- attribute -----
        "attribute_name":                 {"s2": "attr_nm",            "s3": "attribute_name"},
        # ----- colour -----
        "colour":                         {"s2": "clr",                "s3": "colour"},
        # ----- gender -----
        "gender":                         {"s2": "gndr",               "s3": "gender"},
        # ----- publisher -----
        "publisher_name":                 {"s2": "pub_nm",             "s3": "publisher_name"},
        # ----- race -----
        "race":                           {"s2": "rc",                 "s3": "race"},
        # ----- superhero -----
        "superhero_name":                 {"s2": "sphro_nm",           "s3": "superhero_name"},
        "full_name":                      {"s2": "fl_nm",              "s3": "full_name"},
        "gender_id":                      {"s2": "gndr_id",            "s3": "gender_id"},
        "eye_colour_id":                  {"s2": "eye_clr_id",         "s3": "eye_colour_id"},
        "hair_colour_id":                 {"s2": "hr_clr_id",          "s3": "hair_colour_id"},
        "skin_colour_id":                 {"s2": "skn_clr_id",         "s3": "skin_colour_id"},
        "race_id":                        {"s2": "rc_id",              "s3": "race_id"},
        "publisher_id":                   {"s2": "pub_id",             "s3": "publisher_id"},
        "alignment_id":                   {"s2": "algn_id",            "s3": "alignment_id"},
        "height_cm":                      {"s2": "ht_cm",              "s3": "height_centimeter"},
        "weight_kg":                      {"s2": "wt_kg",              "s3": "weight_kilogram"},
        # ----- hero_attribute -----
        "hero_id":                        {"s2": "hro_id",             "s3": "hero_id"},  # also in hero_power
        "attribute_id":                   {"s2": "attr_id",            "s3": "attribute_id"},
        "attribute_value":                {"s2": "attr_val",           "s3": "attribute_value"},
        # ----- superpower -----
        "power_name":                     {"s2": "pwr_nm",             "s3": "power_name"},
        # ----- hero_power -----
        "power_id":                       {"s2": "pwr_id",             "s3": "power_id"},
    },

    # =========================================================================
    # toxicology
    # =========================================================================
    "toxicology": {
        # ----- atom -----
        "atom_id":                        {"s2": "atm_id",             "s3": "atom_id"},  # also in connected
        "molecule_id":                    {"s2": "mol_id",             "s3": "molecule_id"},  # also in bond, molecule
        "element":                        {"s2": "elem",               "s3": "element"},
        # ----- bond -----
        "bond_id":                        {"s2": "bnd_id",             "s3": "bond_id"},  # also in connected
        "bond_type":                      {"s2": "bnd_typ",            "s3": "bond_type"},
        # ----- connected -----
        "atom_id2":                       {"s2": "atm_id2",            "s3": "atom_id2"},
        # ----- molecule -----
        "label":                          {"s2": "lbl",                "s3": "label"},
    },

    # =========================================================================
    # debit_card_specializing  (PascalCase originals)
    # =========================================================================
    "debit_card_specializing": {
        # ----- customers -----
        "CustomerID":                     {"s2": "cust_id",            "s3": "customer_id"},  # also in transactions_1k, yearmonth
        "Segment":                        {"s2": "seg",                "s3": "segment"},  # also in gasstations
        "Currency":                       {"s2": "curr",               "s3": "currency"},
        # ----- gasstations -----
        "GasStationID":                   {"s2": "gs_stn_id",          "s3": "gas_station_id"},  # also in transactions_1k
        "ChainID":                        {"s2": "chn_id",             "s3": "chain_id"},
        "Country":                        {"s2": "ctry",               "s3": "country"},
        # ----- products -----
        "ProductID":                      {"s2": "prod_id",            "s3": "product_id"},  # also in transactions_1k
        "Description":                    {"s2": "descr",              "s3": "description"},
        # ----- transactions_1k -----
        "TransactionID":                  {"s2": "txn_id",             "s3": "transaction_id"},
        "Date":                           {"s2": "dt",                 "s3": "date"},  # also in yearmonth
        "Time":                           {"s2": "tm",                 "s3": "time"},
        "CardID":                         {"s2": "crd_id",             "s3": "card_id"},
        "Amount":                         {"s2": "amt",                "s3": "amount"},
        "Price":                          {"s2": "prc",                "s3": "price"},
        # ----- yearmonth -----
        "Consumption":                    {"s2": "cons",               "s3": "consumption"},
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

    # =========================================================================
    # car_1 (Spider) — continents → countries → makers → models → specs
    # Flat key per column name; wide-table prefixes (L1/L2) disambiguate tables.
    # =========================================================================
    "car_1": {
        # ----- continents -----
        "ContId":                         {"s2": "cont_id",            "s3": "continent_id"},
        "Continent":                      {"s2": "cont",               "s3": "continent"},  # also in countries
        # ----- countries -----
        "CountryId":                      {"s2": "ctry_id",            "s3": "country_id"},
        "CountryName":                    {"s2": "ctry_nm",            "s3": "country_name"},
        # ----- car_makers -----
        "Id":                             {"s2": "id",                 "s3": "id"},  # also in cars_data
        "Maker":                          {"s2": "mkr",                "s3": "maker"},  # also in model_list
        "FullName":                       {"s2": "fl_nm",              "s3": "full_name"},
        "Country":                        {"s2": "ctry",               "s3": "country"},
        # ----- model_list -----
        "ModelId":                        {"s2": "mdl_id",             "s3": "model_id"},
        "Model":                          {"s2": "mdl",                "s3": "model"},  # also in car_names
        # ----- car_names -----
        "MakeId":                         {"s2": "mk_id",              "s3": "make_id"},
        "Make":                           {"s2": "mk",                 "s3": "make"},
        # ----- cars_data -----
        "MPG":                            {"s2": "mpg",                "s3": "miles_per_gallon"},
        "Cylinders":                      {"s2": "cyl",                "s3": "cylinders"},
        "Edispl":                         {"s2": "edispl",             "s3": "engine_displacement"},
        "Horsepower":                     {"s2": "hp",                 "s3": "horsepower"},
        "Weight":                         {"s2": "wt",                 "s3": "weight"},
        "Accelerate":                     {"s2": "accel",              "s3": "accelerate"},
        "Year":                           {"s2": "yr",                 "s3": "year"},
    },

    # =========================================================================
    # tvshow (Spider) — TV_Channel hub; TV_series and Cartoon sibling facts
    # =========================================================================
    "tvshow": {
        # ----- TV_Channel -----
        "id":                             {"s2": "id",                 "s3": "id"},  # also in TV_series, Cartoon
        "series_name":                    {"s2": "ser_nm",             "s3": "series_name"},
        "Country":                        {"s2": "ctry",               "s3": "country"},
        "Language":                       {"s2": "lang",               "s3": "language"},
        "Content":                        {"s2": "cntnt",              "s3": "content"},
        "Pixel_aspect_ratio_PAR":         {"s2": "pixel_aspt_rto_par", "s3": "pixel_aspect_ratio_pixel_aspect_ratio"},
        "Hight_definition_TV":            {"s2": "hght_def_tv",        "s3": "hight_definition_television"},
        "Pay_per_view_PPV":               {"s2": "pay_per_vw_ppv",     "s3": "pay_per_view_pay_per_view"},
        "Package_Option":                 {"s2": "pkg_opt",            "s3": "package_option"},
        # ----- TV_series -----
        "Episode":                        {"s2": "ep",                 "s3": "episode"},
        "Air_Date":                       {"s2": "air_dt",             "s3": "air_date"},
        "Rating":                         {"s2": "rtg",                "s3": "rating"},
        "Share":                          {"s2": "shr",                "s3": "share"},
        "18_49_Rating_Share":             {"s2": "18_49_rtg_shr",      "s3": "18_49_rating_share"},
        "Viewers_m":                      {"s2": "vwrs_m",             "s3": "viewers_millions"},
        "Weekly_Rank":                    {"s2": "wkly_rnk",           "s3": "weekly_rank"},
        "Channel":                        {"s2": "ch",                 "s3": "channel"},  # also in Cartoon
        # ----- Cartoon -----
        "Title":                          {"s2": "ttl",                "s3": "title"},
        "Directed_by":                    {"s2": "dir_by",             "s3": "directed_by"},
        "Written_by":                     {"s2": "wrtn_by",            "s3": "written_by"},
        "Original_air_date":              {"s2": "orig_air_dt",        "s3": "original_air_date"},
        "Production_code":                {"s2": "prod_cd",            "s3": "production_code"},
    },

    # =========================================================================
    # wamex (Acuity held-out) — wamex_reports hub; satellites keyed on anumber
    # =========================================================================
    # original names are full words run together (≈ S3 without separators);
    # S3 adds word breaks and disambiguates bare storages columns. "id" falls back.
    # =========================================================================
    "wamex": {
        # shared across tables
        "anumber":                  {"s2": "a_no",          "s3": "report_number"},
        # wamex_reports
        "reporttitle":              {"s2": "rpt_title",     "s3": "report_title"},
        "reportdate":               {"s2": "rpt_dt",        "s3": "report_date"},
        "authorids":                {"s2": "auth_ids",      "s3": "author_ids"},
        "authornames":              {"s2": "auth_nms",      "s3": "author_names"},
        "operatorids":              {"s2": "oper_ids",      "s3": "operator_ids"},
        "operators":                {"s2": "oper_nms",      "s3": "operator_names"},
        "projectname":              {"s2": "proj_nm",       "s3": "project_name"},
        "targetcommoditiesids":     {"s2": "tgt_cmdty_ids", "s3": "target_commodity_ids"},
        "targetcommoditiesnames":   {"s2": "tgt_cmdty_nms", "s3": "target_commodity_names"},
        "keywords":                 {"s2": "kwds",          "s3": "keywords"},
        "confidentiality":          {"s2": "conf",          "s3": "confidentiality_status"},
        # abstracts
        "abstract":                 {"s2": "abstr",         "s3": "abstract_text"},
        # storages
        "volume":                   {"s2": "vol",           "s3": "volume_number"},
        "storage":                  {"s2": "stor_type",     "s3": "storage_type"},
        "number":                   {"s2": "stor_no",       "s3": "storage_location_number"},
        "description":              {"s2": "descr",         "s3": "storage_description"},
        # drilling_summaries
        "holetype":                 {"s2": "hole_type",     "s3": "drill_hole_type"},
        "numberofholes":            {"s2": "num_holes",     "s3": "number_of_holes"},
        "totaldrilled":             {"s2": "tot_drld",      "s3": "total_metres_drilled"},
        # geo_chemistry
        "sampletype":               {"s2": "smpl_type",     "s3": "sample_type"},
        "numberofsamples":          {"s2": "num_smpls",     "s3": "number_of_samples"},
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
