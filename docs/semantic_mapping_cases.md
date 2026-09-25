# S2/S3 mapping 情况分类清单

比较均在归一化后进行（忽略大小写、空格、下划线、标点；camelCase/PascalCase 与 snake_case 视为同名），所以 `Academic Year`→`academic_year`、`CustomerID`→`customer_id` 都视为“原名”。格式：`表.原名` → S2 / S3。

## A1. S2 = 原名, S3 = BIRD column_name（官方展开名）

**california_schools**

- `satscores.sname` → `sname` / `school_name`
- `satscores.dname` → `dname` / `district_name`
- `satscores.cname` → `cname` / `county_name`
- `schools.MailCity` → `mail_city` / `mailing_city`
- `schools.MailState` → `mail_state` / `mailing_state`
- `schools.DOC` → `doc` / `district_ownership_code`
- `schools.SOC` → `soc` / `school_ownership_code`
- `schools.GSoffered` → `gs_offered` / `grade_span_offered`
- `schools.GSserved` → `gs_served` / `grade_span_served`

**financial**

- `card.disp_id` → `disp_id` / `disposition_id`
- `disp.disp_id` → `disp_id` / `disposition_id`

**formula_1**

- `circuits.lat` → `lat` / `latitude`
- `circuits.lng` → `lng` / `longitude`
- `drivers.dob` → `dob` / `date_of_birth`

**thrombosis_prediction**

- `Laboratory.LDH` → `ldh` / `lactate_dehydrogenase`
- `Laboratory.TP` → `tp` / `total_protein`
- `Laboratory.ALB` → `alb` / `albumin`
- `Laboratory.UA` → `ua` / `uric_acid`
- `Laboratory.UN` → `un` / `urea_nitrogen`
- `Laboratory.CRE` → `cre` / `creatinine`
- `Laboratory.T-BIL` → `t_bil` / `total_bilirubin`
- `Laboratory.T-CHO` → `t_cho` / `total_cholesterol`
- `Laboratory.TG` → `tg` / `triglyceride`
- `Laboratory.CPK` → `cpk` / `creatinine_phosphokinase`
- `Laboratory.GLU` → `glu` / `blood_glucose`
- `Laboratory.HGB` → `hgb` / `hemoglobin`
- `Laboratory.PT` → `pt` / `prothrombin_time`
- `Laboratory.FG` → `fg` / `fibrinogen`
- `Laboratory.U-PRO` → `u_pro` / `proteinuria`
- `Laboratory.CRP` → `crp` / `c_reactive_protein`
- `Laboratory.RNP` → `rnp` / `anti_ribonuclear_protein`
- `Laboratory.SM` → `sm` / `anti_sm`
- `Laboratory.SC170` → `sc170` / `anti_scl70`
- `Laboratory.SSA` → `ssa` / `anti_ssa`
- `Laboratory.SSB` → `ssb` / `anti_ssb`
- `Laboratory.CENTROMEA` → `centromea` / `anti_centromere`
- `Laboratory.DNA` → `dna` / `anti_dna`

## A2. S2 = 原名, S3 = 自拟展开（与 BIRD column_name 不同/无）

**california_schools**

- `satscores.cds` → `cds` / `county_district_school_code`
- `satscores.rtype` → `rtype` / `record_type`
- `satscores.enroll12` → `enroll12` / `enrollment_grade_12`  (BIRD column_name: `enrollment (1st-12nd grade)`)
- `satscores.NumTstTakr` → `num_tst_takr` / `number_test_takers`  (BIRD column_name: `Number of Test Takers`)
- `satscores.AvgScrRead` → `avg_scr_read` / `average_score_reading`  (BIRD column_name: `average scores in Reading`)
- `satscores.AvgScrMath` → `avg_scr_math` / `average_score_math`  (BIRD column_name: `average scores in Math`)
- `satscores.AvgScrWrite` → `avg_scr_write` / `average_score_writing`  (BIRD column_name: `average scores in writing`)
- `satscores.NumGE1500` → `num_ge_1500` / `number_scores_1500_or_above`  (BIRD column_name: `Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500`)
- `schools.NCESDist` → `nces_dist` / `national_center_for_education_statistics_district_id`  (BIRD column_name: `National Center for Educational Statistics school district identification number`)
- `schools.StreetAbr` → `street_abr` / `street_abbreviated`  (BIRD column_name: `street address`)
- `schools.MailStreet` → `mail_street` / `mailing_street`
- `schools.MailStrAbr` → `mail_str_abr` / `mailing_street_abbreviated`  (BIRD column_name: `mailing street address`)
- `schools.MailZip` → `mail_zip` / `mailing_zip_code`  (BIRD column_name: `mailing zip`)
- `schools.Ext` → `ext` / `phone_extension`  (BIRD column_name: `extension`)
- `schools.CharterNum` → `charter_num` / `charter_number`
- `schools.DOCType` → `doc_type` / `district_ownership_type`  (BIRD column_name: `The District Ownership Code Type`)
- `schools.SOCType` → `soc_type` / `school_ownership_type`  (BIRD column_name: `School Ownership Code Type`)
- `schools.AdmFName1` → `adm_fname1` / `admin_first_name_1`  (BIRD column_name: `administrator's first name`)
- `schools.AdmLName1` → `adm_lname1` / `admin_last_name_1`  (BIRD column_name: `administrator's last name`)
- `schools.AdmEmail1` → `adm_email1` / `admin_email_1`  (BIRD column_name: `administrator's email address`)
- `schools.AdmFName2` → `adm_fname2` / `admin_first_name_2`
- `schools.AdmLName2` → `adm_lname2` / `admin_last_name_2`
- `schools.AdmEmail2` → `adm_email2` / `admin_email_2`
- `schools.AdmFName3` → `adm_fname3` / `admin_first_name_3`
- `schools.AdmLName3` → `adm_lname3` / `admin_last_name_3`
- `schools.AdmEmail3` → `adm_email3` / `admin_email_3`

**european_football_2**

- `Match.B365H` → `b365h` / `bet365_home_odds`
- `Match.B365D` → `b365d` / `bet365_draw_odds`
- `Match.B365A` → `b365a` / `bet365_away_odds`
- `Match.BWH` → `bwh` / `bwin_home_odds`
- `Match.BWD` → `bwd` / `bwin_draw_odds`
- `Match.BWA` → `bwa` / `bwin_away_odds`
- `Match.IWH` → `iwh` / `interwetten_home_odds`
- `Match.IWD` → `iwd` / `interwetten_draw_odds`
- `Match.IWA` → `iwa` / `interwetten_away_odds`
- `Match.LBH` → `lbh` / `ladbrokes_home_odds`
- `Match.LBD` → `lbd` / `ladbrokes_draw_odds`
- `Match.LBA` → `lba` / `ladbrokes_away_odds`
- `Match.PSH` → `psh` / `pinnacle_home_odds`
- `Match.PSD` → `psd` / `pinnacle_draw_odds`
- `Match.PSA` → `psa` / `pinnacle_away_odds`
- `Match.WHH` → `whh` / `william_hill_home_odds`
- `Match.WHD` → `whd` / `william_hill_draw_odds`
- `Match.WHA` → `wha` / `william_hill_away_odds`
- `Match.SJH` → `sjh` / `stan_james_home_odds`
- `Match.SJD` → `sjd` / `stan_james_draw_odds`
- `Match.SJA` → `sja` / `stan_james_away_odds`
- `Match.VCH` → `vch` / `vcbet_home_odds`
- `Match.VCD` → `vcd` / `vcbet_draw_odds`
- `Match.VCA` → `vca` / `vcbet_away_odds`
- `Match.GBH` → `gbh` / `gamebookers_home_odds`
- `Match.GBD` → `gbd` / `gamebookers_draw_odds`
- `Match.GBA` → `gba` / `gamebookers_away_odds`
- `Match.BSH` → `bsh` / `bluesquare_home_odds`
- `Match.BSD` → `bsd` / `bluesquare_draw_odds`
- `Match.BSA` → `bsa` / `bluesquare_away_odds`

**financial**

- `order.bank_to` → `bank_to` / `recipient_bank`  (BIRD column_name: `bank of the recipient`)

**formula_1**

- `circuits.alt` → `alt` / `altitude`
- `drivers.code` → `code` / `driver_code`
- `qualifying.q1` → `q1` / `qualifying_1_time`  (BIRD column_name: `qualifying 1`)
- `qualifying.q2` → `q2` / `qualifying_2_time`  (BIRD column_name: `qualifying 2`)
- `qualifying.q3` → `q3` / `qualifying_3_time`  (BIRD column_name: `qualifying 3`)
- `results.grid` → `grid` / `grid_position`

**student_club**

- `budget.spent` → `spent` / `amount_spent`
- `member.zip` → `zip` / `zip_code`

**thrombosis_prediction**

- `Examination.aCL IgG` → `acl_igg` / `anticardiolipin_igg`  (BIRD column_name: `anti-Cardiolipin antibody (IgG)`)
- `Examination.aCL IgM` → `acl_igm` / `anticardiolipin_igm`  (BIRD column_name: `anti-Cardiolipin antibody (IgM)`)
- `Examination.ANA` → `ana` / `antinuclear_antibody`  (BIRD column_name: `anti-nucleus antibody`)
- `Examination.ANA Pattern` → `ana_pattern` / `antinuclear_antibody_pattern`  (BIRD column_name: `pattern observed in the sheet of ANA examination`)
- `Examination.aCL IgA` → `acl_iga` / `anticardiolipin_iga`  (BIRD column_name: `anti-Cardiolipin antibody (IgA) concentration`)
- `Examination.KCT` → `kct` / `kaolin_clotting_time`  (BIRD column_name: `measure of degree of coagulation`)
- `Examination.RVVT` → `rvvt` / `russell_viper_venom_time`  (BIRD column_name: `measure of degree of coagulation`)
- `Examination.LAC` → `lac` / `lupus_anticoagulant`  (BIRD column_name: `measure of degree of coagulation`)
- `Examination.Thrombosis` → `thrombosis` / `thrombosis_degree`
- `Patient.Admission` → `admission` / `admission_type`
- `Laboratory.GOT` → `got` / `aspartate_aminotransferase`  (BIRD column_name: `AST glutamic oxaloacetic transaminase`)
- `Laboratory.GPT` → `gpt` / `alanine_aminotransferase`  (BIRD column_name: `ALT glutamic pyruvic transaminase`)
- `Laboratory.ALP` → `alp` / `alkaline_phosphatase`  (BIRD column_name: `alkaliphophatase`)
- `Laboratory.WBC` → `wbc` / `white_blood_cell_count`  (BIRD column_name: `White blood cell`)
- `Laboratory.RBC` → `rbc` / `red_blood_cell_count`  (BIRD column_name: `Red blood cell`)
- `Laboratory.HCT` → `hct` / `hematocrit`  (BIRD column_name: `Hematoclit`)
- `Laboratory.PLT` → `plt` / `platelet_count`  (BIRD column_name: `platelet`)
- `Laboratory.APTT` → `aptt` / `activated_partial_thromboplastin_time`  (BIRD column_name: `activated partial prothrombin time`)
- `Laboratory.IGG` → `igg` / `immunoglobulin_g`
- `Laboratory.IGA` → `iga` / `immunoglobulin_a`
- `Laboratory.IGM` → `igm` / `immunoglobulin_m`
- `Laboratory.RA` → `ra` / `rheumatoid_factor_ra`  (BIRD column_name: `Rhuematoid Factor`)
- `Laboratory.RF` → `rf` / `raha_titer`  (BIRD column_name: `RAHA`)
- `Laboratory.C3` → `c3` / `complement_component_3`  (BIRD column_name: `complement 3`)
- `Laboratory.C4` → `c4` / `complement_component_4`  (BIRD column_name: `complement 4`)
- `Laboratory.DNA-II` → `dna_ii` / `anti_dna_ii`  (BIRD column_name: `anti-DNA`)

**car_1**

- `continents.ContId` → `cont_id` / `continent_id`
- `cars_data.MPG` → `mpg` / `miles_per_gallon`

**tvshow**

- `TV_Channel.Content` → `content` / `content_type`
- `TV_series.Episode` → `episode` / `episode_title`
- `TV_series.Share` → `share` / `audience_share`
- `TV_series.Viewers_m` → `viewers_m` / `viewers_millions`
- `Cartoon.Title` → `title` / `cartoon_title`

## B. S2 = 新缩写, S3 = 原名

**california_schools**

- `frpm.Academic Year` → `acad_yr` / `academic_year`
- `frpm.County Code` → `cnty_cd` / `county_code`
- `frpm.District Code` → `dist_cd` / `district_code`
- `frpm.School Code` → `sch_cd` / `school_code`
- `frpm.County Name` → `cnty_nm` / `county_name`
- `frpm.District Name` → `dist_nm` / `district_name`
- `frpm.School Name` → `sch_nm` / `school_name`
- `frpm.District Type` → `dist_type` / `district_type`
- `frpm.School Type` → `sch_type` / `school_type`
- `frpm.Educational Option Type` → `edu_opt_type` / `educational_option_type`
- `frpm.Charter School Number` → `charter_num` / `charter_school_number`
- `frpm.Charter Funding Type` → `charter_fund` / `charter_funding_type`
- `frpm.Low Grade` → `low_grd` / `low_grade`
- `frpm.High Grade` → `high_grd` / `high_grade`
- `frpm.Enrollment (K-12)` → `enroll_k12` / `enrollment_k12`
- `frpm.Free Meal Count (K-12)` → `free_meal_k12` / `free_meal_count_k12`
- `frpm.Percent (%) Eligible Free (K-12)` → `pct_free_k12` / `percent_eligible_free_k12`
- `frpm.Enrollment (Ages 5-17)` → `enroll_5_17` / `enrollment_ages_5_17`
- `frpm.Free Meal Count (Ages 5-17)` → `free_meal_5_17` / `free_meal_count_ages_5_17`
- `frpm.Percent (%) Eligible Free (Ages 5-17)` → `pct_free_5_17` / `percent_eligible_free_ages_5_17`
- `schools.OpenDate` → `open_dt` / `open_date`
- `schools.ClosedDate` → `close_dt` / `closed_date`
- `schools.FundingType` → `fund_type` / `funding_type`
- `schools.LastUpdate` → `last_upd` / `last_update`

**debit_card_specializing**

- `customers.CustomerID` → `cust_id` / `customer_id`
- `customers.Segment` → `seg` / `segment`
- `customers.Currency` → `curr` / `currency`
- `gasstations.GasStationID` → `gs_id` / `gas_station_id`
- `gasstations.Country` → `ctry` / `country`
- `gasstations.Segment` → `seg` / `segment`
- `products.ProductID` → `prod_id` / `product_id`
- `products.Description` → `descr` / `description`
- `transactions_1k.TransactionID` → `txn_id` / `transaction_id`
- `transactions_1k.CustomerID` → `cust_id` / `customer_id`
- `transactions_1k.GasStationID` → `gs_id` / `gas_station_id`
- `transactions_1k.ProductID` → `prod_id` / `product_id`
- `transactions_1k.Amount` → `amt` / `amount`
- `yearmonth.CustomerID` → `cust_id` / `customer_id`
- `yearmonth.Consumption` → `consump` / `consumption`

**european_football_2**

- `Player_Attributes.player_fifa_api_id` → `fifa_api_id` / `player_fifa_api_id`
- `Player_Attributes.player_api_id` → `plr_api_id` / `player_api_id`
- `Player_Attributes.overall_rating` → `ovr_rtg` / `overall_rating`
- `Player_Attributes.preferred_foot` → `pref_foot` / `preferred_foot`
- `Player_Attributes.attacking_work_rate` → `atk_wr` / `attacking_work_rate`
- `Player_Attributes.defensive_work_rate` → `def_wr` / `defensive_work_rate`
- `Player_Attributes.crossing` → `cross` / `crossing`
- `Player_Attributes.finishing` → `finish` / `finishing`
- `Player_Attributes.heading_accuracy` → `head_acc` / `heading_accuracy`
- `Player_Attributes.short_passing` → `sh_pass` / `short_passing`
- `Player_Attributes.dribbling` → `dribble` / `dribbling`
- `Player_Attributes.free_kick_accuracy` → `fk_acc` / `free_kick_accuracy`
- `Player_Attributes.long_passing` → `lng_pass` / `long_passing`
- `Player_Attributes.ball_control` → `ball_ctrl` / `ball_control`
- `Player_Attributes.acceleration` → `accel` / `acceleration`
- `Player_Attributes.sprint_speed` → `sprt_spd` / `sprint_speed`
- `Player_Attributes.reactions` → `react` / `reactions`
- `Player_Attributes.shot_power` → `shot_pwr` / `shot_power`
- `Player_Attributes.jumping` → `jump` / `jumping`
- `Player_Attributes.long_shots` → `lng_shots` / `long_shots`
- `Player_Attributes.aggression` → `aggr` / `aggression`
- `Player_Attributes.interceptions` → `interc` / `interceptions`
- `Player_Attributes.positioning` → `pos` / `positioning`
- `Player_Attributes.penalties` → `pens` / `penalties`
- `Player_Attributes.standing_tackle` → `std_tackle` / `standing_tackle`
- `Player_Attributes.sliding_tackle` → `sld_tackle` / `sliding_tackle`
- `Player.player_api_id` → `plr_api_id` / `player_api_id`
- `Player.player_name` → `plr_nm` / `player_name`
- `Player.player_fifa_api_id` → `fifa_api_id` / `player_fifa_api_id`
- `Player.birthday` → `bday` / `birthday`
- `Player.height` → `ht` / `height`
- `Player.weight` → `wt` / `weight`
- `Team.team_fifa_api_id` → `fifa_team_id` / `team_fifa_api_id`
- `Team.team_long_name` → `team_nm` / `team_long_name`
- `Team.team_short_name` → `team_abbr` / `team_short_name`
- `Team_Attributes.team_fifa_api_id` → `fifa_team_id` / `team_fifa_api_id`
- `Team_Attributes.buildUpPlaySpeed` → `bu_spd` / `buildup_play_speed`
- `Team_Attributes.buildUpPlaySpeedClass` → `bu_spd_cls` / `buildup_play_speed_class`
- `Team_Attributes.buildUpPlayDribbling` → `bu_drib` / `buildup_play_dribbling`
- `Team_Attributes.buildUpPlayDribblingClass` → `bu_drib_cls` / `buildup_play_dribbling_class`
- `Team_Attributes.buildUpPlayPassing` → `bu_pass` / `buildup_play_passing`
- `Team_Attributes.buildUpPlayPassingClass` → `bu_pass_cls` / `buildup_play_passing_class`
- `Team_Attributes.buildUpPlayPositioningClass` → `bu_pos_cls` / `buildup_play_positioning_class`
- `Team_Attributes.chanceCreationPassing` → `cc_pass` / `chance_creation_passing`
- `Team_Attributes.chanceCreationPassingClass` → `cc_pass_cls` / `chance_creation_passing_class`
- `Team_Attributes.chanceCreationCrossing` → `cc_cross` / `chance_creation_crossing`
- `Team_Attributes.chanceCreationCrossingClass` → `cc_cross_cls` / `chance_creation_crossing_class`
- `Team_Attributes.chanceCreationShooting` → `cc_shoot` / `chance_creation_shooting`
- `Team_Attributes.chanceCreationShootingClass` → `cc_shoot_cls` / `chance_creation_shooting_class`
- `Team_Attributes.chanceCreationPositioningClass` → `cc_pos_cls` / `chance_creation_positioning_class`
- `Team_Attributes.defencePressure` → `def_press` / `defence_pressure`
- `Team_Attributes.defencePressureClass` → `def_press_cls` / `defence_pressure_class`
- `Team_Attributes.defenceAggression` → `def_aggr` / `defence_aggression`
- `Team_Attributes.defenceAggressionClass` → `def_aggr_cls` / `defence_aggression_class`
- `Team_Attributes.defenceTeamWidth` → `def_width` / `defence_team_width`
- `Team_Attributes.defenceTeamWidthClass` → `def_width_cls` / `defence_team_width_class`
- `Team_Attributes.defenceDefenderLineClass` → `def_line_cls` / `defence_defender_line_class`
- `Match.home_team_api_id` → `home_team_id` / `home_team_api_id`
- `Match.away_team_api_id` → `away_team_id` / `away_team_api_id`
- `Match.possession` → `poss` / `possession`

**financial**

- `account.account_id` → `acct_id` / `account_id`
- `account.district_id` → `dist_id` / `district_id`
- `client.birth_date` → `birth_dt` / `birth_date`
- `client.district_id` → `dist_id` / `district_id`
- `disp.account_id` → `acct_id` / `account_id`
- `district.district_id` → `dist_id` / `district_id`
- `loan.account_id` → `acct_id` / `account_id`
- `order.account_id` → `acct_id` / `account_id`
- `trans.account_id` → `acct_id` / `account_id`

**formula_1**

- `circuits.circuitId` → `cir_id` / `circuit_id`
- `constructors.constructorId` → `ctor_id` / `constructor_id`
- `constructors.nationality` → `nation` / `nationality`
- `drivers.driverId` → `drv_id` / `driver_id`
- `drivers.nationality` → `nation` / `nationality`
- `races.circuitId` → `cir_id` / `circuit_id`
- `constructorResults.constructorResultsId` → `ctor_res_id` / `constructor_results_id`
- `constructorResults.constructorId` → `ctor_id` / `constructor_id`
- `constructorStandings.constructorStandingsId` → `ctor_std_id` / `constructor_standings_id`
- `constructorStandings.constructorId` → `ctor_id` / `constructor_id`
- `constructorStandings.positionText` → `pos_txt` / `position_text`
- `driverStandings.driverStandingsId` → `drv_std_id` / `driver_standings_id`
- `driverStandings.driverId` → `drv_id` / `driver_id`
- `driverStandings.positionText` → `pos_txt` / `position_text`
- `lapTimes.driverId` → `drv_id` / `driver_id`
- `lapTimes.milliseconds` → `ms` / `milliseconds`
- `pitStops.driverId` → `drv_id` / `driver_id`
- `pitStops.milliseconds` → `ms` / `milliseconds`
- `qualifying.qualifyId` → `qual_id` / `qualify_id`
- `qualifying.driverId` → `drv_id` / `driver_id`
- `qualifying.constructorId` → `ctor_id` / `constructor_id`
- `results.resultId` → `res_id` / `result_id`
- `results.driverId` → `drv_id` / `driver_id`
- `results.constructorId` → `ctor_id` / `constructor_id`
- `results.positionText` → `pos_txt` / `position_text`
- `results.positionOrder` → `pos_order` / `position_order`
- `results.milliseconds` → `ms` / `milliseconds`
- `results.fastestLapTime` → `fast_lap_tm` / `fastest_lap_time`
- `results.fastestLapSpeed` → `fast_lap_spd` / `fastest_lap_speed`

**student_club**

- `event.event_id` → `evt_id` / `event_id`
- `event.event_name` → `evt_nm` / `event_name`
- `event.event_date` → `evt_dt` / `event_date`
- `event.location` → `loc` / `location`
- `major.major_id` → `maj_id` / `major_id`
- `major.major_name` → `maj_nm` / `major_name`
- `major.department` → `dept` / `department`
- `major.college` → `coll` / `college`
- `zip_code.zip_code` → `zip_cd` / `zip_code`
- `zip_code.county` → `cnty` / `county`
- `budget.budget_id` → `bgt_id` / `budget_id`
- `budget.category` → `cat` / `category`
- `budget.amount` → `amt` / `amount`
- `budget.event_status` → `evt_status` / `event_status`
- `expense.expense_id` → `exp_id` / `expense_id`
- `expense.expense_description` → `exp_desc` / `expense_description`
- `expense.expense_date` → `exp_dt` / `expense_date`
- `income.income_id` → `inc_id` / `income_id`
- `income.date_received` → `rcvd_dt` / `date_received`
- `income.amount` → `amt` / `amount`
- `member.member_id` → `mbr_id` / `member_id`
- `member.first_name` → `fname` / `first_name`
- `member.last_name` → `lname` / `last_name`
- `member.position` → `pos` / `position`
- `member.t_shirt_size` → `shirt_sz` / `t_shirt_size`

**superhero**

- `alignment.alignment` → `align` / `alignment`
- `attribute.attribute_name` → `attr_nm` / `attribute_name`
- `colour.colour` → `color` / `colour`
- `publisher.publisher_name` → `pub_nm` / `publisher_name`
- `superhero.superhero_name` → `hero_nm` / `superhero_name`
- `superhero.full_name` → `full_nm` / `full_name`
- `superhero.eye_colour_id` → `eye_clr_id` / `eye_colour_id`
- `superhero.hair_colour_id` → `hair_clr_id` / `hair_colour_id`
- `superhero.skin_colour_id` → `skin_clr_id` / `skin_colour_id`
- `superhero.publisher_id` → `pub_id` / `publisher_id`
- `superhero.alignment_id` → `align_id` / `alignment_id`
- `superhero.height_cm` → `ht_cm` / `height_cm`
- `superhero.weight_kg` → `wt_kg` / `weight_kg`
- `hero_attribute.attribute_id` → `attr_id` / `attribute_id`
- `hero_attribute.attribute_value` → `attr_val` / `attribute_value`
- `superpower.power_name` → `pwr_nm` / `power_name`
- `hero_power.power_id` → `pwr_id` / `power_id`

**thrombosis_prediction**

- `Examination.Examination Date` → `exam_dt` / `examination_date`
- `Examination.Diagnosis` → `diag` / `diagnosis`
- `Patient.Birthday` → `bday` / `birthday`
- `Patient.Diagnosis` → `diag` / `diagnosis`

**toxicology**

- `atom.atom_id` → `atm_id` / `atom_id`
- `atom.molecule_id` → `mol_id` / `molecule_id`
- `atom.element` → `elem` / `element`
- `bond.bond_id` → `bnd_id` / `bond_id`
- `bond.molecule_id` → `mol_id` / `molecule_id`
- `bond.bond_type` → `bnd_type` / `bond_type`
- `connected.atom_id` → `atm_id` / `atom_id`
- `connected.atom_id2` → `atm_id2` / `atom_id2`
- `connected.bond_id` → `bnd_id` / `bond_id`
- `molecule.molecule_id` → `mol_id` / `molecule_id`
- `molecule.label` → `lbl` / `label`

**car_1**

- `countries.CountryId` → `ctry_id` / `country_id`
- `countries.CountryName` → `ctry_nm` / `country_name`
- `cars_data.Horsepower` → `hp` / `horsepower`

**tvshow**

- `TV_Channel.series_name` → `series_nm` / `series_name`
- `TV_Channel.Country` → `ctry` / `country`
- `TV_Channel.Language` → `lang` / `language`
- `TV_Channel.Package_Option` → `pkg_opt` / `package_option`
- `TV_series.Air_Date` → `air_dt` / `air_date`
- `TV_series.Weekly_Rank` → `wk_rank` / `weekly_rank`
- `Cartoon.Directed_by` → `director` / `directed_by`
- `Cartoon.Written_by` → `writer` / `written_by`
- `Cartoon.Original_air_date` → `orig_air` / `original_air_date`
- `Cartoon.Production_code` → `prod_cd` / `production_code`

## C1. S2 = 新缩写, S3 = BIRD column_name

**california_schools**

- `schools.EdOpsName` → `ed_ops_nm` / `educational_option_name`

**financial**

- `district.A2` → `dist_nm` / `district_name`
- `district.A11` → `avg_sal` / `average_salary`
- `district.A12` → `unemp_95` / `unemployment_rate_1995`
- `district.A13` → `unemp_96` / `unemployment_rate_1996`
- `trans.trans_id` → `txn_id` / `transaction_id`
- `trans.balance` → `bal` / `balance_after_transaction`

## C2. S2 = 新缩写, S3 = 自拟展开

**california_schools**

- `frpm.CDSCode` → `cds_cd` / `county_district_school_code`
- `frpm.NSLP Provision Status` → `nslp_status` / `national_school_lunch_program_provision_status`
- `frpm.Charter School (Y/N)` → `is_charter` / `is_charter_school`
- `frpm.FRPM Count (K-12)` → `frpm_k12` / `free_or_reduced_price_meal_count_k12`
- `frpm.Percent (%) Eligible FRPM (K-12)` → `pct_frpm_k12` / `percent_eligible_free_or_reduced_price_meal_k12`
- `frpm.FRPM Count (Ages 5-17)` → `frpm_5_17` / `free_or_reduced_price_meal_count_ages_5_17`
- `frpm.Percent (%) Eligible FRPM (Ages 5-17)` → `pct_frpm_5_17` / `percent_eligible_free_or_reduced_price_meal_ages_5_17`
- `frpm.2013-14 CALPADS Fall 1 Certification Status` → `calpads_cert` / `california_longitudinal_pupil_achievement_data_system_fall_1_certification_status`
- `schools.CDSCode` → `cds_cd` / `county_district_school_code`
- `schools.NCESSchool` → `nces_sch` / `national_center_for_education_statistics_school_id`  (BIRD column_name: `National Center for Educational Statistics school identification number`)
- `schools.EdOpsCode` → `ed_ops_cd` / `educational_option_code`  (BIRD column_name: `Education Option Code`)
- `schools.EILCode` → `eil_cd` / `instruction_level_code`  (BIRD column_name: `Educational Instruction Level Code`)
- `schools.EILName` → `eil_nm` / `instruction_level_name`  (BIRD column_name: `Educational Instruction Level Name`)

**european_football_2**

- `Player_Attributes.gk_diving` → `gk_div` / `goalkeeper_diving`  (BIRD column_name: `goalkeep diving`)
- `Player_Attributes.gk_handling` → `gk_hand` / `goalkeeper_handling`  (BIRD column_name: `goalkeep handling`)
- `Player_Attributes.gk_kicking` → `gk_kick` / `goalkeeper_kicking`  (BIRD column_name: `goalkeep kicking`)
- `Player_Attributes.gk_positioning` → `gk_pos` / `goalkeeper_positioning`  (BIRD column_name: `goalkeep positioning`)
- `Player_Attributes.gk_reflexes` → `gk_ref` / `goalkeeper_reflexes`  (BIRD column_name: `goalkeep reflexes`)
- `Match.home_team_goal` → `home_goals` / `home_team_goals`
- `Match.away_team_goal` → `away_goals` / `away_team_goals`
- `Match.home_player_X1` → `hp1_x` / `home_player_1_x_position`
- `Match.home_player_X2` → `hp2_x` / `home_player_2_x_position`
- `Match.home_player_X3` → `hp3_x` / `home_player_3_x_position`
- `Match.home_player_X4` → `hp4_x` / `home_player_4_x_position`
- `Match.home_player_X5` → `hp5_x` / `home_player_5_x_position`
- `Match.home_player_X6` → `hp6_x` / `home_player_6_x_position`
- `Match.home_player_X7` → `hp7_x` / `home_player_7_x_position`
- `Match.home_player_X8` → `hp8_x` / `home_player_8_x_position`
- `Match.home_player_X9` → `hp9_x` / `home_player_9_x_position`
- `Match.home_player_X10` → `hp10_x` / `home_player_10_x_position`
- `Match.home_player_X11` → `hp11_x` / `home_player_11_x_position`
- `Match.away_player_X1` → `ap1_x` / `away_player_1_x_position`
- `Match.away_player_X2` → `ap2_x` / `away_player_2_x_position`
- `Match.away_player_X3` → `ap3_x` / `away_player_3_x_position`
- `Match.away_player_X4` → `ap4_x` / `away_player_4_x_position`
- `Match.away_player_X5` → `ap5_x` / `away_player_5_x_position`
- `Match.away_player_X6` → `ap6_x` / `away_player_6_x_position`
- `Match.away_player_X7` → `ap7_x` / `away_player_7_x_position`
- `Match.away_player_X8` → `ap8_x` / `away_player_8_x_position`
- `Match.away_player_X9` → `ap9_x` / `away_player_9_x_position`
- `Match.away_player_X10` → `ap10_x` / `away_player_10_x_position`
- `Match.away_player_X11` → `ap11_x` / `away_player_11_x_position`
- `Match.home_player_Y1` → `hp1_y` / `home_player_1_y_position`
- `Match.home_player_Y2` → `hp2_y` / `home_player_2_y_position`
- `Match.home_player_Y3` → `hp3_y` / `home_player_3_y_position`
- `Match.home_player_Y4` → `hp4_y` / `home_player_4_y_position`
- `Match.home_player_Y5` → `hp5_y` / `home_player_5_y_position`
- `Match.home_player_Y6` → `hp6_y` / `home_player_6_y_position`
- `Match.home_player_Y7` → `hp7_y` / `home_player_7_y_position`
- `Match.home_player_Y8` → `hp8_y` / `home_player_8_y_position`
- `Match.home_player_Y9` → `hp9_y` / `home_player_9_y_position`
- `Match.home_player_Y10` → `hp10_y` / `home_player_10_y_position`
- `Match.home_player_Y11` → `hp11_y` / `home_player_11_y_position`
- `Match.away_player_Y1` → `ap1_y` / `away_player_1_y_position`
- `Match.away_player_Y2` → `ap2_y` / `away_player_2_y_position`
- `Match.away_player_Y3` → `ap3_y` / `away_player_3_y_position`
- `Match.away_player_Y4` → `ap4_y` / `away_player_4_y_position`
- `Match.away_player_Y5` → `ap5_y` / `away_player_5_y_position`
- `Match.away_player_Y6` → `ap6_y` / `away_player_6_y_position`
- `Match.away_player_Y7` → `ap7_y` / `away_player_7_y_position`
- `Match.away_player_Y8` → `ap8_y` / `away_player_8_y_position`
- `Match.away_player_Y9` → `ap9_y` / `away_player_9_y_position`
- `Match.away_player_Y10` → `ap10_y` / `away_player_10_y_position`
- `Match.away_player_Y11` → `ap11_y` / `away_player_11_y_position`
- `Match.home_player_1` → `hp1_id` / `home_player_1_api_id`
- `Match.home_player_2` → `hp2_id` / `home_player_2_api_id`
- `Match.home_player_3` → `hp3_id` / `home_player_3_api_id`
- `Match.home_player_4` → `hp4_id` / `home_player_4_api_id`
- `Match.home_player_5` → `hp5_id` / `home_player_5_api_id`
- `Match.home_player_6` → `hp6_id` / `home_player_6_api_id`
- `Match.home_player_7` → `hp7_id` / `home_player_7_api_id`
- `Match.home_player_8` → `hp8_id` / `home_player_8_api_id`
- `Match.home_player_9` → `hp9_id` / `home_player_9_api_id`
- `Match.home_player_10` → `hp10_id` / `home_player_10_api_id`
- `Match.home_player_11` → `hp11_id` / `home_player_11_api_id`
- `Match.away_player_1` → `ap1_id` / `away_player_1_api_id`
- `Match.away_player_2` → `ap2_id` / `away_player_2_api_id`
- `Match.away_player_3` → `ap3_id` / `away_player_3_api_id`
- `Match.away_player_4` → `ap4_id` / `away_player_4_api_id`
- `Match.away_player_5` → `ap5_id` / `away_player_5_api_id`
- `Match.away_player_6` → `ap6_id` / `away_player_6_api_id`
- `Match.away_player_7` → `ap7_id` / `away_player_7_api_id`
- `Match.away_player_8` → `ap8_id` / `away_player_8_api_id`
- `Match.away_player_9` → `ap9_id` / `away_player_9_api_id`
- `Match.away_player_10` → `ap10_id` / `away_player_10_api_id`
- `Match.away_player_11` → `ap11_id` / `away_player_11_api_id`
- `Match.shoton` → `shots_on` / `shots_on_target`
- `Match.shotoff` → `shots_off` / `shots_off_target`
- `Match.foulcommit` → `fouls` / `fouls_committed`

**financial**

- `account.frequency` → `freq` / `statement_frequency`
- `card.issued` → `issued_dt` / `issued_date`
- `district.A4` → `num_inhab` / `number_inhabitants`  (BIRD column_name: `number of inhabitants`)
- `district.A5` → `num_mun_lt499` / `number_municipalities_below_499`  (BIRD column_name: `no. of municipalities with inhabitants < 499`)
- `district.A6` → `num_mun_500` / `number_municipalities_500_to_1999`  (BIRD column_name: `no. of municipalities with inhabitants 500-1999`)
- `district.A7` → `num_mun_2000` / `number_municipalities_2000_to_9999`  (BIRD column_name: `no. of municipalities with inhabitants 2000-9999`)
- `district.A8` → `num_mun_gt10k` / `number_municipalities_above_10000`  (BIRD column_name: `no. of municipalities with inhabitants > 10000`)
- `district.A9` → `num_cities` / `number_cities`
- `district.A10` → `urban_ratio` / `urban_inhabitant_ratio`  (BIRD column_name: `ratio of urban inhabitants`)
- `district.A14` → `entre_per_1k` / `entrepreneurs_per_1000`  (BIRD column_name: `no. of entrepreneurs per 1000 inhabitants`)
- `district.A15` → `crimes_95` / `number_crimes_1995`  (BIRD column_name: `no. of committed crimes 1995`)
- `district.A16` → `crimes_96` / `number_crimes_1996`  (BIRD column_name: `no. of committed crimes 1996`)
- `loan.duration` → `dur_months` / `duration_months`
- `loan.payments` → `payment_amt` / `monthly_payment_amount`  (BIRD column_name: `monthly payments`)
- `order.account_to` → `acct_to` / `recipient_account`  (BIRD column_name: `account of the recipient`)
- `order.k_symbol` → `k_sym` / `transaction_type_code`  (BIRD column_name: `characterization of the payment`)
- `trans.operation` → `op` / `transaction_operation`  (BIRD column_name: `mode of transaction`)
- `trans.k_symbol` → `k_sym` / `transaction_type_code`  (BIRD column_name: `characterization of the transaction`)

**formula_1**

- `circuits.circuitRef` → `cir_ref` / `circuit_ref_name`  (BIRD column_name: `circuit reference name`)
- `constructors.constructorRef` → `ctor_ref` / `constructor_ref_name`  (BIRD column_name: `Constructor Reference name`)
- `drivers.driverRef` → `drv_ref` / `driver_ref_name`  (BIRD column_name: `driver reference name`)
- `drivers.forename` → `fname` / `first_name`
- `drivers.surname` → `lname` / `last_name`
- `pitStops.stop` → `stop_num` / `stop_number`
- `results.fastestLap` → `fast_lap` / `fastest_lap_number`

**student_club**

- `zip_code.short_state` → `st` / `state_abbr`
- `attendance.link_to_event` → `evt_id` / `event_id`
- `attendance.link_to_member` → `mbr_id` / `member_id`
- `budget.remaining` → `remain` / `amount_remaining`
- `budget.link_to_event` → `evt_id` / `event_id`
- `expense.approved` → `aprvd` / `is_approved`
- `expense.link_to_member` → `mbr_id` / `member_id`
- `expense.link_to_budget` → `bgt_id` / `budget_id`
- `income.source` → `src` / `income_source`
- `income.link_to_member` → `mbr_id` / `member_id`
- `member.link_to_major` → `maj_id` / `major_id`

**thrombosis_prediction**

- `Patient.Description` → `first_rec_dt` / `first_record_date`
- `Patient.First Date` → `admit_dt` / `first_hospital_visit_date`

**car_1**

- `continents.Continent` → `cont_nm` / `continent_name`
- `countries.Continent` → `cont_nm` / `continent_name`
- `car_makers.Id` → `rec_id` / `record_id`
- `car_makers.Maker` → `mkr_cd` / `maker_code`
- `car_makers.FullName` → `full_nm` / `manufacturer_full_name`
- `car_makers.Country` → `ctry_id` / `country_id`
- `model_list.Maker` → `mkr_cd` / `maker_code`
- `model_list.Model` → `model_nm` / `model_name`
- `car_names.Model` → `model_nm` / `model_name`
- `car_names.Make` → `make_lbl` / `make_label`
- `cars_data.Id` → `rec_id` / `record_id`
- `cars_data.Cylinders` → `cyl` / `cylinder_count`
- `cars_data.Edispl` → `displ` / `engine_displacement`
- `cars_data.Weight` → `wt` / `vehicle_weight`
- `cars_data.Accelerate` → `accel` / `acceleration`
- `cars_data.Year` → `model_yr` / `model_year`

**tvshow**

- `TV_Channel.id` → `rec_id` / `record_id`
- `TV_Channel.Pixel_aspect_ratio_PAR` → `par` / `pixel_aspect_ratio`
- `TV_Channel.Hight_definition_TV` → `hdtv` / `high_definition_tv`
- `TV_Channel.Pay_per_view_PPV` → `ppv` / `pay_per_view`
- `TV_series.id` → `rec_id` / `record_id`
- `TV_series.18_49_Rating_Share` → `rtg_18_49` / `age_18_49_rating_share`
- `TV_series.Channel` → `ch_id` / `channel_id`
- `Cartoon.id` → `rec_id` / `record_id`
- `Cartoon.Channel` → `ch_id` / `channel_id`

## E. S2 = S3 = 同一个新名（≠原名）

**financial**

- `district.A3` → `region` / `region`

## D1. S2 = S3 = 原名（ALIASES 中显式写成相同）

**california_schools**

- `frpm.IRC` → `irc` / `irc`
- `schools.StatusType` → `status_type` / `status_type`

**debit_card_specializing**

- `gasstations.ChainID` → `chain_id` / `chain_id`
- `transactions_1k.Date` → `date` / `date`
- `transactions_1k.Time` → `time` / `time`
- `transactions_1k.CardID` → `card_id` / `card_id`
- `transactions_1k.Price` → `price` / `price`
- `yearmonth.Date` → `date` / `date`

**european_football_2**

- `Player_Attributes.potential` → `potential` / `potential`
- `Player_Attributes.volleys` → `volleys` / `volleys`
- `Player_Attributes.curve` → `curve` / `curve`
- `Player_Attributes.agility` → `agility` / `agility`
- `Player_Attributes.balance` → `balance` / `balance`
- `Player_Attributes.stamina` → `stamina` / `stamina`
- `Player_Attributes.strength` → `strength` / `strength`
- `Player_Attributes.vision` → `vision` / `vision`
- `Player_Attributes.marking` → `marking` / `marking`
- `Team.team_api_id` → `team_api_id` / `team_api_id`
- `Team_Attributes.team_api_id` → `team_api_id` / `team_api_id`
- `Match.match_api_id` → `match_api_id` / `match_api_id`

**financial**

- `card.card_id` → `card_id` / `card_id`
- `client.client_id` → `client_id` / `client_id`
- `disp.client_id` → `client_id` / `client_id`
- `loan.loan_id` → `loan_id` / `loan_id`
- `order.order_id` → `order_id` / `order_id`

**formula_1**

- `races.raceId` → `race_id` / `race_id`
- `constructorResults.raceId` → `race_id` / `race_id`
- `constructorStandings.raceId` → `race_id` / `race_id`
- `driverStandings.raceId` → `race_id` / `race_id`
- `lapTimes.raceId` → `race_id` / `race_id`
- `pitStops.raceId` → `race_id` / `race_id`
- `qualifying.raceId` → `race_id` / `race_id`
- `status.statusId` → `status_id` / `status_id`
- `results.raceId` → `race_id` / `race_id`
- `results.statusId` → `status_id` / `status_id`

**student_club**

- `event.notes` → `notes` / `notes`
- `income.notes` → `notes` / `notes`
- `member.email` → `email` / `email`
- `member.phone` → `phone` / `phone`

**superhero**

- `superhero.gender_id` → `gender_id` / `gender_id`
- `superhero.race_id` → `race_id` / `race_id`
- `hero_attribute.hero_id` → `hero_id` / `hero_id`
- `hero_power.hero_id` → `hero_id` / `hero_id`

**thrombosis_prediction**

- `Examination.Symptoms` → `symptoms` / `symptoms`
- `Patient.SEX` → `sex` / `sex`
- `Laboratory.PIC` → `pic` / `pic`
- `Laboratory.TAT` → `tat` / `tat`
- `Laboratory.TAT2` → `tat2` / `tat2`

**car_1**

- `model_list.ModelId` → `model_id` / `model_id`
- `car_names.MakeId` → `make_id` / `make_id`

**tvshow**

- `TV_series.Rating` → `rating` / `rating`

## D2. S2 = S3 = 原名（不在 ALIASES 中，fallback）

**california_schools**

- `schools.County` → `County` / `County`
- `schools.District` → `District` / `District`
- `schools.School` → `School` / `School`
- `schools.Street` → `Street` / `Street`
- `schools.City` → `City` / `City`
- `schools.Zip` → `Zip` / `Zip`
- `schools.State` → `State` / `State`
- `schools.Phone` → `Phone` / `Phone`
- `schools.Website` → `Website` / `Website`
- `schools.Charter` → `Charter` / `Charter`
- `schools.Virtual` → `Virtual` / `Virtual`
- `schools.Magnet` → `Magnet` / `Magnet`
- `schools.Latitude` → `Latitude` / `Latitude`
- `schools.Longitude` → `Longitude` / `Longitude`

**european_football_2**

- `Player_Attributes.id` → `id` / `id`
- `Player_Attributes.date` → `date` / `date`
- `Player.id` → `id` / `id`
- `League.id` → `id` / `id`
- `League.country_id` → `country_id` / `country_id`
- `League.name` → `name` / `name`
- `Country.id` → `id` / `id`
- `Country.name` → `name` / `name`
- `Team.id` → `id` / `id`
- `Team_Attributes.id` → `id` / `id`
- `Team_Attributes.date` → `date` / `date`
- `Match.id` → `id` / `id`
- `Match.country_id` → `country_id` / `country_id`
- `Match.league_id` → `league_id` / `league_id`
- `Match.season` → `season` / `season`
- `Match.stage` → `stage` / `stage`
- `Match.date` → `date` / `date`
- `Match.goal` → `goal` / `goal`
- `Match.card` → `card` / `card`
- `Match.cross` → `cross` / `cross`
- `Match.corner` → `corner` / `corner`

**financial**

- `account.date` → `date` / `date`
- `card.type` → `type` / `type`
- `client.gender` → `gender` / `gender`
- `disp.type` → `type` / `type`
- `loan.date` → `date` / `date`
- `loan.amount` → `amount` / `amount`
- `loan.status` → `status` / `status`
- `order.amount` → `amount` / `amount`
- `trans.date` → `date` / `date`
- `trans.type` → `type` / `type`
- `trans.amount` → `amount` / `amount`
- `trans.bank` → `bank` / `bank`
- `trans.account` → `account` / `account`

**formula_1**

- `circuits.name` → `name` / `name`
- `circuits.location` → `location` / `location`
- `circuits.country` → `country` / `country`
- `circuits.url` → `url` / `url`
- `constructors.name` → `name` / `name`
- `constructors.url` → `url` / `url`
- `drivers.number` → `number` / `number`
- `drivers.url` → `url` / `url`
- `seasons.year` → `year` / `year`
- `seasons.url` → `url` / `url`
- `races.year` → `year` / `year`
- `races.round` → `round` / `round`
- `races.name` → `name` / `name`
- `races.date` → `date` / `date`
- `races.time` → `time` / `time`
- `races.url` → `url` / `url`
- `constructorResults.points` → `points` / `points`
- `constructorResults.status` → `status` / `status`
- `constructorStandings.points` → `points` / `points`
- `constructorStandings.position` → `position` / `position`
- `constructorStandings.wins` → `wins` / `wins`
- `driverStandings.points` → `points` / `points`
- `driverStandings.position` → `position` / `position`
- `driverStandings.wins` → `wins` / `wins`
- `lapTimes.lap` → `lap` / `lap`
- `lapTimes.position` → `position` / `position`
- `lapTimes.time` → `time` / `time`
- `pitStops.lap` → `lap` / `lap`
- `pitStops.time` → `time` / `time`
- `pitStops.duration` → `duration` / `duration`
- `qualifying.number` → `number` / `number`
- `qualifying.position` → `position` / `position`
- `status.status` → `status` / `status`
- `results.number` → `number` / `number`
- `results.position` → `position` / `position`
- `results.points` → `points` / `points`
- `results.laps` → `laps` / `laps`
- `results.time` → `time` / `time`
- `results.rank` → `rank` / `rank`

**student_club**

- `event.type` → `type` / `type`
- `event.status` → `status` / `status`
- `zip_code.type` → `type` / `type`
- `zip_code.city` → `city` / `city`
- `zip_code.state` → `state` / `state`
- `expense.cost` → `cost` / `cost`

**superhero**

- `alignment.id` → `id` / `id`
- `attribute.id` → `id` / `id`
- `colour.id` → `id` / `id`
- `gender.id` → `id` / `id`
- `gender.gender` → `gender` / `gender`
- `publisher.id` → `id` / `id`
- `race.id` → `id` / `id`
- `race.race` → `race` / `race`
- `superhero.id` → `id` / `id`
- `superpower.id` → `id` / `id`

**thrombosis_prediction**

- `Examination.ID` → `ID` / `ID`
- `Patient.ID` → `ID` / `ID`
- `Laboratory.ID` → `ID` / `ID`
- `Laboratory.Date` → `Date` / `Date`

