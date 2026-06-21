# Entity and attribute analysis (nine 3NF databases)

Entity = a **distinct, uniquely identifiable** real-world object, person, place, concept, or event. Uses PK/FK from SQLite (`dev_20240627/dev_databases/`).

## What counts as an entity?


| Role          | Count as entity? | Rationale                                                                    |
| ------------- | ---------------- | ---------------------------------------------------------------------------- |
| **core**      | Yes              | Primary noun (Client, School, Molecule, ...)                                 |
| **lookup**    | Yes              | Identifiable reference concept (District, Race, Season, ...)                 |
| **fact**      | Yes              | Identifiable event/record (Match, Transaction, Race result, ...)             |
| **dependent** | **Yes**          | Own surrogate PK + names a thing (Loan, Card, Atom, Expense, ...)            |
| **extension** | **No**           | Same entity as parent; extra columns or observations (frpm, Laboratory, ...) |
| **bridge**    | **No** (default) | **Relationship** between entities (M:N link), not a third business object    |


### Bridge vs dependent (guidance)

**Dependent** tables usually **are entities**: a `loan` row is a Loan, an `atom` row is an Atom, even though FK ties them to Account or Molecule. They have their own identity (PK) and are not just duplicate keys of the parent.

**Bridge** tables usually **are not entities**: `disp` (client-account), `attendance` (event-member), `hero_power` (hero-power) primarily **link** two entities. Count them as **relationships**. Exception: if a bridge stores rich relationship-specific facts and you treat the link as a first-class object (e.g. enrollment with grade, contract with terms), you may reclassify as **fact** or **dependent**; none of the nine DB bridges here warrant that in the default reading.

**Extension** never adds an entity count: `california_schools` stays **1 school**, `thrombosis_prediction` stays **1 patient**.

**Counts:** **Entities** = distinct entity groups with role in {core, lookup, fact, dependent}. **Stored attrs** = all non-PK columns. **Entity attrs** = non-PK on entity groups only (includes extension cols merged into parent). **Attrs / entity** = entity attrs / entity count.

PK reference: `[table_primary_keys_nine_db.md](table_primary_keys_nine_db.md)`.

## Summary


| Database                   | Tables | **Entities** | Bridge tables | Extension tables | Entity attrs | Attrs / entity | All attrs |
| -------------------------- | ------ | ------------ | ------------- | ---------------- | ------------ | -------------- | --------- |
| `california_schools`       | 3      | 1            | 0             | 2                | 86           | 86.0           | 86        |
| `debit_card_specializings` | 5      | 4            | 0             | 1                | 15           | 3.8            | 15        |
| `european_football_2`      | 7      | 5            | 0             | 2                | 192          | 38.4           | 192       |
| `financial`                | 8      | 7            | 1             | 0                | 44           | 6.3            | 47        |
| `formula_1`                | 13     | 13           | 0             | 0                | 77           | 5.9            | 77        |
| `student_club`             | 8      | 7            | 1             | 0                | 39           | 5.6            | 39        |
| `superhero`                | 10     | 8            | 2             | 0                | 18           | 2.2            | 23        |
| `thrombosis_prediction`    | 3      | 1            | 0             | 2                | 61           | 61.0           | 61        |
| `toxicology`               | 4      | 3            | 1             | 0                | 5            | 1.7            | 6         |


---

## `california_schools`

**One school entity.** `schools` is the root; `frpm` and `satscores` are **vertical partitions** of school-related attributes. Their PKs (`CDSCode` / `cds`) are **foreign keys** to `schools.CDSCode`, not separate institutions.

### Tables


| Table       | PK        | Foreign keys                   | Role      | Entity group     | Non-PK attrs |
| ----------- | --------- | ------------------------------ | --------- | ---------------- | ------------ |
| `frpm`      | `CDSCode` | `CDSCode` -> `schools.CDSCode` | extension | School (CDSCode) | 28           |
| `satscores` | `cds`     | `cds` -> `schools.CDSCode`     | extension | School (CDSCode) | 10           |
| `schools`   | `CDSCode` | none                           | core      | School (CDSCode) | 48           |


### Entity groups


| Entity group     | Role | Tables                         | Non-PK attrs |
| ---------------- | ---- | ------------------------------ | ------------ |
| School (CDSCode) | core | `schools`, `frpm`, `satscores` | 86           |


**Entities (1):** **School (CDSCode)** (core).
**Extensions (merged into parent):** `frpm`, `satscores`.

**Totals:** 1 entities, 86 entity attributes (86.0 per entity), 86 attributes in schema.

---

## `debit_card_specializing`

**Four conceptual entities:** Customer, Gas station, Product, Transaction. `yearmonth` is **monthly consumption per customer** (composite PK includes `CustomerID`); merge under Customer, not a fifth business object. `transactions_1k` has no declared FK but is an independent fact table.

### Tables


| Table             | PK                   | Foreign keys                  | Role      | Entity group | Non-PK attrs |
| ----------------- | -------------------- | ----------------------------- | --------- | ------------ | ------------ |
| `customers`       | `CustomerID`         | none                          | core      | Customer     | 2            |
| `gasstations`     | `GasStationID`       | none                          | core      | Gas station  | 3            |
| `products`        | `ProductID`          | none                          | core      | Product      | 1            |
| `transactions_1k` | `TransactionID`      | none                          | fact      | Transaction  | 8            |
| `yearmonth`       | `Date`, `CustomerID` | `CustomerID` -> `customers.?` | extension | Customer     | 1            |


### Entity groups


| Entity group | Role | Tables                   | Non-PK attrs |
| ------------ | ---- | ------------------------ | ------------ |
| Customer     | core | `customers`, `yearmonth` | 3            |
| Gas station  | core | `gasstations`            | 3            |
| Product      | core | `products`               | 1            |
| Transaction  | fact | `transactions_1k`        | 8            |


**Entities (4):** **Customer** (core), **Gas station** (core), **Product** (core), **Transaction** (fact).
**Extensions (merged into parent):** `yearmonth`.

**Totals:** 4 entities, 15 entity attributes (3.8 per entity), 15 attributes in schema.

---

## `european_football_2`

**Country** (lookup), **League**, **Team**, **Player**, **Match** (fixture fact). `Player_Attributes` / `Team_Attributes` are **time-varying extensions**, not new players or teams. `Match` references many player slots via FKs.

### Tables


| Table               | PK   | Foreign keys                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Role      | Entity group    | Non-PK attrs |
| ------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | --------------- | ------------ |
| `Country`           | `id` | none                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | lookup    | Country         | 1            |
| `League`            | `id` | `country_id` -> `country.id`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | core      | League          | 2            |
| `Match`             | `id` | `away_player_11` -> `Player.player_api_id`; `away_player_10` -> `Player.player_api_id`; `away_player_9` -> `Player.player_api_id`; `away_player_8` -> `Player.player_api_id`; `away_player_7` -> `Player.player_api_id`; `away_player_6` -> `Player.player_api_id`; `away_player_5` -> `Player.player_api_id`; `away_player_4` -> `Player.player_api_id`; `away_player_3` -> `Player.player_api_id`; `away_player_2` -> `Player.player_api_id`; `away_player_1` -> `Player.player_api_id`; `home_player_11` -> `Player.player_api_id`; `home_player_10` -> `Player.player_api_id`; `home_player_9` -> `Player.player_api_id`; `home_player_8` -> `Player.player_api_id`; `home_player_7` -> `Player.player_api_id`; `home_player_6` -> `Player.player_api_id`; `home_player_5` -> `Player.player_api_id`; `home_player_4` -> `Player.player_api_id`; `home_player_3` -> `Player.player_api_id`; `home_player_2` -> `Player.player_api_id`; `home_player_1` -> `Player.player_api_id`; `away_team_api_id` -> `Team.team_api_id`; `home_team_api_id` -> `Team.team_api_id`; `league_id` -> `League.?`; `country_id` -> `Country.?` | fact      | Match (fixture) | 114          |
| `Player`            | `id` | none                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | core      | Player          | 6            |
| `Player_Attributes` | `id` | `player_api_id` -> `Player.player_api_id`; `player_fifa_api_id` -> `Player.player_fifa_api_id`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | extension | Player          | 41           |
| `Team`              | `id` | none                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | core      | Team            | 4            |
| `Team_Attributes`   | `id` | `team_api_id` -> `Team.team_api_id`; `team_fifa_api_id` -> `Team.team_fifa_api_id`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | extension | Team            | 24           |


### Entity groups


| Entity group    | Role   | Tables                        | Non-PK attrs |
| --------------- | ------ | ----------------------------- | ------------ |
| Country         | lookup | `Country`                     | 1            |
| League          | core   | `League`                      | 2            |
| Match (fixture) | fact   | `Match`                       | 114          |
| Player          | core   | `Player`, `Player_Attributes` | 47           |
| Team            | core   | `Team`, `Team_Attributes`     | 28           |


**Entities (5):** **Country** (lookup), **League** (core), **Match (fixture)** (fact), **Player** (core), **Team** (core).
**Extensions (merged into parent):** `Player_Attributes`, `Team_Attributes`.

**Totals:** 5 entities, 192 entity attributes (38.4 per entity), 192 attributes in schema.

---

## `financial`

**District** (lookup), **Client**, **Account** as cores; `**disp`** links clients to accounts (bridge). Card, loan, order, and `trans` are **account- or client-scoped dependents**, not peers of Client.

### Tables


| Table      | PK            | Foreign keys                                                            | Role      | Entity group        | Non-PK attrs |
| ---------- | ------------- | ----------------------------------------------------------------------- | --------- | ------------------- | ------------ |
| `account`  | `account_id`  | `district_id` -> `district.district_id`                                 | core      | Account             | 3            |
| `card`     | `card_id`     | `disp_id` -> `disp.disp_id`                                             | dependent | Card                | 3            |
| `client`   | `client_id`   | `district_id` -> `district.district_id`                                 | core      | Client              | 3            |
| `disp`     | `disp_id`     | `client_id` -> `client.client_id`; `account_id` -> `account.account_id` | bridge    | Client-Account link | 3            |
| `district` | `district_id` | none                                                                    | lookup    | District            | 15           |
| `loan`     | `loan_id`     | `account_id` -> `account.account_id`                                    | dependent | Loan                | 6            |
| `order`    | `order_id`    | `account_id` -> `account.account_id`                                    | dependent | Order               | 5            |
| `trans`    | `trans_id`    | `account_id` -> `account.account_id`                                    | dependent | Bank transaction    | 9            |


### Entity groups


| Entity group        | Role      | Tables     | Non-PK attrs |
| ------------------- | --------- | ---------- | ------------ |
| Account             | core      | `account`  | 3            |
| Bank transaction    | dependent | `trans`    | 9            |
| Card                | dependent | `card`     | 3            |
| Client              | core      | `client`   | 3            |
| Client-Account link | bridge    | `disp`     | 3            |
| District            | lookup    | `district` | 15           |
| Loan                | dependent | `loan`     | 6            |
| Order               | dependent | `order`    | 5            |


**Entities (7):** **Account** (core), **Bank transaction** (dependent), **Card** (dependent), **Client** (core), **District** (lookup), **Loan** (dependent), **Order** (dependent).
**Bridges (not counted):** `disp`.

**Totals:** 7 entities, 44 entity attributes (6.3 per entity), 47 attributes in schema.

---

## `formula_1`

**Circuit, Season, Status** (lookups); **Constructor, Driver, Race** (cores); six **fact/standing** tables (results, qualifying, lapTimes, pitStops, constructor/driver standings). High table count, moderate distinct entity count.

### Tables


| Table                  | PK                           | Foreign keys                                                                                                                                   | Role   | Entity group            | Non-PK attrs |
| ---------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ----------------------- | ------------ |
| `circuits`             | `circuitId`                  | none                                                                                                                                           | lookup | Circuit                 | 8            |
| `constructorResults`   | `constructorResultsId`       | `constructorId` -> `constructors.constructorId`; `raceId` -> `races.raceId`                                                                    | fact   | Constructor race result | 4            |
| `constructorStandings` | `constructorStandingsId`     | `constructorId` -> `constructors.constructorId`; `raceId` -> `races.raceId`                                                                    | fact   | Constructor standing    | 6            |
| `constructors`         | `constructorId`              | none                                                                                                                                           | core   | Constructor             | 4            |
| `driverStandings`      | `driverStandingsId`          | `driverId` -> `drivers.driverId`; `raceId` -> `races.raceId`                                                                                   | fact   | Driver standing         | 6            |
| `drivers`              | `driverId`                   | none                                                                                                                                           | core   | Driver                  | 8            |
| `lapTimes`             | `raceId`, `driverId`, `lap`  | `driverId` -> `drivers.driverId`; `raceId` -> `races.raceId`                                                                                   | fact   | Lap time                | 3            |
| `pitStops`             | `raceId`, `driverId`, `stop` | `driverId` -> `drivers.driverId`; `raceId` -> `races.raceId`                                                                                   | fact   | Pit stop                | 4            |
| `qualifying`           | `qualifyId`                  | `constructorId` -> `constructors.constructorId`; `driverId` -> `drivers.driverId`; `raceId` -> `races.raceId`                                  | fact   | Qualifying              | 8            |
| `races`                | `raceId`                     | `circuitId` -> `circuits.circuitId`; `year` -> `seasons.year`                                                                                  | core   | Race                    | 7            |
| `results`              | `resultId`                   | `statusId` -> `status.statusId`; `constructorId` -> `constructors.constructorId`; `driverId` -> `drivers.driverId`; `raceId` -> `races.raceId` | fact   | Race result             | 17           |
| `seasons`              | `year`                       | none                                                                                                                                           | lookup | Season                  | 1            |
| `status`               | `statusId`                   | none                                                                                                                                           | lookup | Status                  | 1            |


### Entity groups


| Entity group            | Role   | Tables                 | Non-PK attrs |
| ----------------------- | ------ | ---------------------- | ------------ |
| Circuit                 | lookup | `circuits`             | 8            |
| Constructor             | core   | `constructors`         | 4            |
| Constructor race result | fact   | `constructorResults`   | 4            |
| Constructor standing    | fact   | `constructorStandings` | 6            |
| Driver                  | core   | `drivers`              | 8            |
| Driver standing         | fact   | `driverStandings`      | 6            |
| Lap time                | fact   | `lapTimes`             | 3            |
| Pit stop                | fact   | `pitStops`             | 4            |
| Qualifying              | fact   | `qualifying`           | 8            |
| Race                    | core   | `races`                | 7            |
| Race result             | fact   | `results`              | 17           |
| Season                  | lookup | `seasons`              | 1            |
| Status                  | lookup | `status`               | 1            |


**Entities (13):** **Circuit** (lookup), **Constructor** (core), **Constructor race result** (fact), **Constructor standing** (fact), **Driver** (core), **Driver standing** (fact), **Lap time** (fact), **Pit stop** (fact), **Qualifying** (fact), **Race** (core), **Race result** (fact), **Season** (lookup), **Status** (lookup).

**Totals:** 13 entities, 77 entity attributes (5.9 per entity), 77 attributes in schema.

---

## `student_club`

**Major, ZIP** (lookups); **Member, Event** (cores). Budget/expense/income are **financial records** tied to events or members. `**attendance`** is an Event-Member bridge (composite PK = both FKs).

### Tables


| Table        | PK                                | Foreign keys                                                                   | Role      | Entity group | Non-PK attrs |
| ------------ | --------------------------------- | ------------------------------------------------------------------------------ | --------- | ------------ | ------------ |
| `attendance` | `link_to_event`, `link_to_member` | `link_to_member` -> `member.member_id`; `link_to_event` -> `event.event_id`    | bridge    | Event-Member | 0            |
| `budget`     | `budget_id`                       | `link_to_event` -> `event.event_id`                                            | dependent | Event budget | 6            |
| `event`      | `event_id`                        | none                                                                           | core      | Event        | 6            |
| `expense`    | `expense_id`                      | `link_to_member` -> `member.member_id`; `link_to_budget` -> `budget.budget_id` | dependent | Expense      | 6            |
| `income`     | `income_id`                       | `link_to_member` -> `member.member_id`                                         | dependent | Income       | 5            |
| `major`      | `major_id`                        | none                                                                           | lookup    | Major        | 3            |
| `member`     | `member_id`                       | `zip` -> `zip_code.zip_code`; `link_to_major` -> `major.major_id`              | core      | Member       | 8            |
| `zip_code`   | `zip_code`                        | none                                                                           | lookup    | ZIP code     | 5            |


### Entity groups


| Entity group | Role      | Tables       | Non-PK attrs |
| ------------ | --------- | ------------ | ------------ |
| Event        | core      | `event`      | 6            |
| Event budget | dependent | `budget`     | 6            |
| Event-Member | bridge    | `attendance` | 0            |
| Expense      | dependent | `expense`    | 6            |
| Income       | dependent | `income`     | 5            |
| Major        | lookup    | `major`      | 3            |
| Member       | core      | `member`     | 8            |
| ZIP code     | lookup    | `zip_code`   | 5            |


**Entities (7):** **Event** (core), **Event budget** (dependent), **Expense** (dependent), **Income** (dependent), **Major** (lookup), **Member** (core), **ZIP code** (lookup).
**Bridges (not counted):** `attendance`.

**Totals:** 7 entities, 39 entity attributes (5.6 per entity), 39 attributes in schema.

---

## `superhero`

Each `id` is **scoped to its own table** (`race.id` != `publisher.id`). **Superhero** is the only core noun; seven small **lookup** tables; `hero_attribute` / `hero_power` are **M:N bridges** with no PK.

### Tables


| Table            | PK     | Foreign keys                                                                                                                                                                                                             | Role   | Entity group        | Non-PK attrs |
| ---------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ------------------- | ------------ |
| `alignment`      | `id`   | none                                                                                                                                                                                                                     | lookup | Alignment           | 1            |
| `attribute`      | `id`   | none                                                                                                                                                                                                                     | lookup | Attribute type      | 1            |
| `colour`         | `id`   | none                                                                                                                                                                                                                     | lookup | Colour              | 1            |
| `gender`         | `id`   | none                                                                                                                                                                                                                     | lookup | Gender              | 1            |
| `hero_attribute` | (none) | `hero_id` -> `superhero.id`; `attribute_id` -> `attribute.id`                                                                                                                                                            | bridge | Superhero-Attribute | 3            |
| `hero_power`     | (none) | `power_id` -> `superpower.id`; `hero_id` -> `superhero.id`                                                                                                                                                               | bridge | Superhero-Power     | 2            |
| `publisher`      | `id`   | none                                                                                                                                                                                                                     | lookup | Publisher           | 1            |
| `race`           | `id`   | none                                                                                                                                                                                                                     | lookup | Race                | 1            |
| `superhero`      | `id`   | `skin_colour_id` -> `colour.id`; `race_id` -> `race.id`; `publisher_id` -> `publisher.id`; `hair_colour_id` -> `colour.id`; `gender_id` -> `gender.id`; `eye_colour_id` -> `colour.id`; `alignment_id` -> `alignment.id` | core   | Superhero           | 11           |
| `superpower`     | `id`   | none                                                                                                                                                                                                                     | lookup | Superpower          | 1            |


### Entity groups


| Entity group        | Role   | Tables           | Non-PK attrs |
| ------------------- | ------ | ---------------- | ------------ |
| Alignment           | lookup | `alignment`      | 1            |
| Attribute type      | lookup | `attribute`      | 1            |
| Colour              | lookup | `colour`         | 1            |
| Gender              | lookup | `gender`         | 1            |
| Publisher           | lookup | `publisher`      | 1            |
| Race                | lookup | `race`           | 1            |
| Superhero           | core   | `superhero`      | 11           |
| Superhero-Attribute | bridge | `hero_attribute` | 3            |
| Superhero-Power     | bridge | `hero_power`     | 2            |
| Superpower          | lookup | `superpower`     | 1            |


**Entities (8):** **Alignment** (lookup), **Attribute type** (lookup), **Colour** (lookup), **Gender** (lookup), **Publisher** (lookup), **Race** (lookup), **Superhero** (core), **Superpower** (lookup).
**Bridges (not counted):** `hero_attribute`, `hero_power`.

**Totals:** 8 entities, 18 entity attributes (2.2 per entity), 23 attributes in schema.

---

## `thrombosis_prediction`

**One patient entity.** `Laboratory` = lab panel per (`ID`, `Date`). `Examination` has **no PK** and allows multiple rows per patient (and NULL `ID`); treat as examination observations, not a separate Patient type.

### Tables


| Table         | PK           | Foreign keys         | Role      | Entity group | Non-PK attrs |
| ------------- | ------------ | -------------------- | --------- | ------------ | ------------ |
| `Examination` | (none)       | `ID` -> `Patient.ID` | extension | Patient      | 13           |
| `Laboratory`  | `ID`, `Date` | `ID` -> `Patient.ID` | extension | Patient      | 42           |
| `Patient`     | `ID`         | none                 | core      | Patient      | 6            |


### Entity groups


| Entity group | Role | Tables                                 | Non-PK attrs |
| ------------ | ---- | -------------------------------------- | ------------ |
| Patient      | core | `Patient`, `Examination`, `Laboratory` | 61           |


**Entities (1):** **Patient** (core).
**Extensions (merged into parent):** `Examination`, `Laboratory`.

**Totals:** 1 entities, 61 entity attributes (61.0 per entity), 61 attributes in schema.

---

## `toxicology`

**Molecule** is the root; **Atom** and **Bond** belong to a molecule. `connected` links atoms to bonds (composite PK on atom pair). Chemically three object types, but **one hub entity** (Molecule) in the FK graph.

### Tables


| Table       | PK                    | Foreign keys                                                                           | Role      | Entity group | Non-PK attrs |
| ----------- | --------------------- | -------------------------------------------------------------------------------------- | --------- | ------------ | ------------ |
| `atom`      | `atom_id`             | `molecule_id` -> `molecule.molecule_id`                                                | dependent | Atom         | 2            |
| `bond`      | `bond_id`             | `molecule_id` -> `molecule.molecule_id`                                                | dependent | Bond         | 2            |
| `connected` | `atom_id`, `atom_id2` | `bond_id` -> `bond.bond_id`; `atom_id2` -> `atom.atom_id`; `atom_id` -> `atom.atom_id` | bridge    | Atom-Bond    | 1            |
| `molecule`  | `molecule_id`         | none                                                                                   | core      | Molecule     | 1            |


### Entity groups


| Entity group | Role      | Tables      | Non-PK attrs |
| ------------ | --------- | ----------- | ------------ |
| Atom         | dependent | `atom`      | 2            |
| Atom-Bond    | bridge    | `connected` | 1            |
| Bond         | dependent | `bond`      | 2            |
| Molecule     | core      | `molecule`  | 1            |


**Entities (3):** **Atom** (dependent), **Bond** (dependent), **Molecule** (core).
**Bridges (not counted):** `connected`.

**Totals:** 3 entities, 5 entity attributes (1.7 per entity), 6 attributes in schema.

---

Regenerate: `python3 analysis/analyze_entity_attribute_model.py`