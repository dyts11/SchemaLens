# Primary keys by table (nine databases, 3NF SQLite)

Source: `dev_20240627/dev_databases/{db_id}/{db_id}.sqlite`, via `PRAGMA table_info` (`pk` column > 0). Composite keys are listed in SQLite declaration order.

## `california_schools`

| Table | Primary key(s) |
|-------|----------------|
| `frpm` | `CDSCode` |
| `satscores` | `cds` |
| `schools` | `CDSCode` |

## `debit_card_specializing`

| Table | Primary key(s) |
|-------|----------------|
| `customers` | `CustomerID` |
| `gasstations` | `GasStationID` |
| `products` | `ProductID` |
| `transactions_1k` | `TransactionID` |
| `yearmonth` | `Date`, `CustomerID` |

## `european_football_2`

| Table | Primary key(s) |
|-------|----------------|
| `Country` | `id` |
| `League` | `id` |
| `Match` | `id` |
| `Player` | `id` |
| `Player_Attributes` | `id` |
| `Team` | `id` |
| `Team_Attributes` | `id` |

## `financial`

| Table | Primary key(s) |
|-------|----------------|
| `account` | `account_id` |
| `card` | `card_id` |
| `client` | `client_id` |
| `disp` | `disp_id` |
| `district` | `district_id` |
| `loan` | `loan_id` |
| `order` | `order_id` |
| `trans` | `trans_id` |

## `formula_1`

| Table | Primary key(s) |
|-------|----------------|
| `circuits` | `circuitId` |
| `constructorResults` | `constructorResultsId` |
| `constructorStandings` | `constructorStandingsId` |
| `constructors` | `constructorId` |
| `driverStandings` | `driverStandingsId` |
| `drivers` | `driverId` |
| `lapTimes` | `raceId`, `driverId`, `lap` |
| `pitStops` | `raceId`, `driverId`, `stop` |
| `qualifying` | `qualifyId` |
| `races` | `raceId` |
| `results` | `resultId` |
| `seasons` | `year` |
| `status` | `statusId` |

## `student_club`

| Table | Primary key(s) |
|-------|----------------|
| `attendance` | `link_to_event`, `link_to_member` |
| `budget` | `budget_id` |
| `event` | `event_id` |
| `expense` | `expense_id` |
| `income` | `income_id` |
| `major` | `major_id` |
| `member` | `member_id` |
| `zip_code` | `zip_code` |

## `superhero`

| Table | Primary key(s) |
|-------|----------------|
| `alignment` | `id` |
| `attribute` | `id` |
| `colour` | `id` |
| `gender` | `id` |
| `hero_attribute` | (none declared in SQLite) |
| `hero_power` | (none declared in SQLite) |
| `publisher` | `id` |
| `race` | `id` |
| `superhero` | `id` |
| `superpower` | `id` |

## `thrombosis_prediction`

| Table | Primary key(s) |
|-------|----------------|
| `Examination` | (none declared in SQLite) |
| `Laboratory` | `ID`, `Date` |
| `Patient` | `ID` |

## `toxicology`

| Table | Primary key(s) |
|-------|----------------|
| `atom` | `atom_id` |
| `bond` | `bond_id` |
| `connected` | `atom_id`, `atom_id2` |
| `molecule` | `molecule_id` |

---

Regenerate: `python3 analysis/list_table_primary_keys.py`
