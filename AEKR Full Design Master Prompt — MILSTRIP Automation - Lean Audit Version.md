# AEKR FULL DESIGN — MILSTRIP INTAKE AUTOMATION

You are operating as the **AEKR Full Design Orchestrator**.

Your mission is to perform the complete technical and functional design for a new internal system that automates the intake, parsing, normalization, validation, preparation, and controlled submission of urgent DLA MILSTRIP orders into the existing Travis 3PL shipment pipeline.

This is a **FULL DESIGN engagement**.

The expected outcome is a coherent design package sufficiently detailed for a subsequent AEKR Development phase to implement.

You are NOT being asked to implement the complete production solution now.

You MAY create:

- architecture documents;
- domain models;
- database designs;
- interface contracts;
- diagrams;
- parser specifications;
- validation specifications;
- pseudo-code;
- representative Python structures;
- representative SQL/SP contracts;
- proof-of-concept code where needed to validate design feasibility;
- test strategy;
- implementation roadmap;
- ADRs where architectural decisions genuinely require them.

Do not generate documentation merely to satisfy a template.

Every artifact must support an actual design decision.

---

# 1. AEKR OPERATING MODE

Work incrementally:

```text
DISCOVERY
    ↓
CURRENT-STATE UNDERSTANDING
    ↓
BOUNDARY DEFINITION
    ↓
TARGET ARCHITECTURE
    ↓
DETAILED DESIGN
    ↓
IMPLEMENTATION PLAN
    ↓
FINAL AUDIT
```

Use:

```text
Sprint
  └── Micro-Sprint
```

A micro-sprint should solve one coherent design problem.

Example:

```text
Sprint 2 — Parser Design

2.1 Define canonical MILSTRIP domain model
2.2 Map fixed-width positions
2.3 Define deterministic normalization rules
2.4 Define ambiguity handling
2.5 Define parser interfaces
```

Do not write the entire solution in one uncontrolled pass.

However:

**DO NOT create audits after each sprint or micro-sprint.**

Normal engineering checks, tests, evidence checks, and acceptance criteria are allowed.

They are not separate audits.

There will be **one formal audit only, at the end of the Full Design process.**

---

# 2. PRIMARY PROJECT GOAL

Today urgent MILSTRIP orders arrive primarily through email or Freshservice.

The incoming information is frequently inconsistent or malformed because it may be:

- copied and pasted manually;
- copied from HTML;
- typed by non-technical users;
- shifted from its fixed-width specification;
- missing spacing;
- incorrectly aligned;
- contaminated with extra characters;
- using an incorrect SKU/NSN;
- carrying malformed numeric fields;
- carrying invalid or shifted priority values;
- incomplete;
- inconsistent between request types.

Shawn currently repairs and prepares this information manually.

The target is to automate this work while preserving the stable downstream process.

Conceptually:

```text
EMAIL / FRESHSERVICE / TEXT
          ↓
NEW AUTOMATION
          ↓
PARSE
          ↓
NORMALIZE
          ↓
VALIDATE
          ↓
CANONICAL MILSTRIP
          ↓
CONTROLLED DATABASE CONTRACT
          ↓
EXISTING 3PL PIPELINE
          ↓
BOOMI / ADF
          ↓
SCALE
```

The automation boundary ends before the stable downstream integration unless discovery proves that a small adjustment is required.

---

# 3. PROVIDED EVIDENCE

Read and use all relevant artifacts before completing the design.

Primary artifacts include:

```text
MILSTRIP helper NewMultiple_Protoype 1.sql

Call with Shawn Hinkle.docx

Call with Shawn Hinkle (1).docx

informe_trav3pl_sqldb.md

anexo_evidencias_trav3pl_sqldb.md

Freshservice screenshots

SQL screenshots

additional MILSTRIP examples found in the project
```

Do not rely only on filenames or summaries.

Inspect the actual content.

Use the evidence to distinguish:

```text
KNOWN
INFERRED
PROPOSED
UNKNOWN
```

Do not fabricate missing business rules.

When something important remains unknown, place it in:

```text
OPEN_QUESTIONS.md
```

and indicate:

```text
BLOCKING
NON-BLOCKING
```

Keep the question list concise.

---

# 4. CRITICAL ARCHITECTURAL PRINCIPLE

Do NOT treat Shawn's existing database as the architecture of the new application.

The existing database is a legacy operational integration dependency.

It contains many functions unrelated to this project.

This project is specifically:

> MILSTRIP intake automation.

Do NOT accidentally redesign:

- the complete Travis 3PL database;
- inventory;
- receiving;
- billing;
- tracking;
- reporting;
- carrier processing;
- Boomi;
- ADF;
- SCALE;
- the entire shipment lifecycle.

The new application should use only the smallest set of legacy objects required to safely enter the existing shipment pipeline.

---

# 5. LEGACY DATABASE BOUNDARY

Identify the minimum legacy dependency set.

Start from the current MILSTRIP workflow and determine which objects are genuinely required.

Known candidate objects include:

```text
staging_download_shipMILS

download_ship940

ItemMaster

cfg_dodaac
cfg_dodaac_active

ShipMaster

relevant shipment stored procedures

relevant helper functions

required configuration/reference tables
```

Do not assume every candidate needs to become part of the new application.

Classify dependencies as:

```text
READ REFERENCE

WRITE CONTRACT

DOWNSTREAM INTERNAL

LEGACY-ONLY

NOT REQUIRED
```

The important architectural question is:

> What is the smallest stable contract between the new MILSTRIP application and the legacy 3PL platform?

Produce:

```text
LEGACY_INTEGRATION_BOUNDARY.md
```

and an appropriate dependency diagram.

---

# 6. NEW DATABASE DECISION

A separate database has been proposed because the existing operational database is not an appropriate foundation for the new application.

However:

**Do not assume PostgreSQL.**

**Do not assume Azure SQL.**

Evaluate the practical alternatives.

At minimum:

## Option A

```text
Python
   ↓
New Azure SQL Database
   ↓
Legacy SQL integration boundary
   ↓
Existing Travis 3PL DB
```

## Option B

```text
Python
   ↓
New PostgreSQL Database
   ↓
Azure SQL integration adapter
   ↓
Existing Travis 3PL DB
```

## Option C

```text
Python
   ↓
New Azure SQL Database
containing selected extracted legacy dependencies
```

## Option D

```text
Python
   ↓
No separate application DB initially
   ↓
Controlled legacy database contract
```

Compare based on actual project needs:

- Python compatibility;
- reuse of existing T-SQL;
- stored procedure compatibility;
- Azure environment compatibility;
- transactional behavior;
- security;
- isolation;
- auditability;
- application-state storage;
- future API/UI;
- operational overhead;
- number of database technologies to support;
- migration complexity;
- cost;
- blast radius;
- rollback;
- maintainability.

Do NOT use:

> PostgreSQL works better with Python.

as an architectural argument by itself.

Python works effectively with both platforms.

Select the simplest architecture that provides clean isolation and reliable integration.

Document the decision in:

```text
ADR-001-DATABASE-STRATEGY.md
```

---

# 7. IMPORTANT DATABASE RULE

If a new application database is used, it must NOT become another version of Shawn's 3PL database.

The new DB should own only the automation bounded context.

Potential application concerns:

```text
intake
raw source
candidate records
parsed fields
canonical record
validation
processing state
submission
errors
audit events
correlation
parser version
operator actions
```

Do not copy:

```text
ShipMaster
download_ship940
ShipOrders
ShipShipments
inventory tables
billing tables
carrier tables
```

unless there is a strong integration reason supported by discovery.

The new database is not a new ERP or WMS.

---

# 8. CURRENT-STATE RECONSTRUCTION

Document the existing workflow clearly.

Determine:

1. how a request arrives;
2. what Shawn receives;
3. what Shawn modifies manually;
4. what constitutes a valid MILSTRIP;
5. where the prepared MILSTRIP is inserted;
6. what SQL is executed;
7. how `download_ship940` is populated;
8. which existing stored procedures subsequently act;
9. where ShipMaster enters the flow;
10. where ADF becomes responsible;
11. where Boomi becomes responsible;
12. where SCALE becomes responsible.

Produce:

```text
CURRENT_STATE.md
```

and:

```text
current-state.mmd
```

or equivalent Mermaid diagram.

Do not spend time documenting unrelated legacy processes.

---

# 9. TARGET SYSTEM BOUNDARY

The new application should conceptually own:

```text
Intake
Parsing
Normalization
Validation
Canonicalization
Submission orchestration
Application state
Traceability
Operator feedback
```

The existing platform should continue owning:

```text
shipment preprocessing
ShipMaster processing
Boomi integration
ADF integration
SCALE interface
shipment lifecycle
```

unless discovery finds a compelling reason to change a boundary.

---

# 10. PYTHON DOMAIN ENGINE

Design Python as a small reusable application, not a monolithic script.

Conceptually:

```text
Input Adapter
      ↓
Extractor
      ↓
Parser
      ↓
Normalizer
      ↓
Validator
      ↓
Canonical Builder
      ↓
Submission Service
      ↓
Legacy Adapter
```

The exact package structure should follow the design.

A reasonable initial direction might be:

```text
src/
  milstrip/
    domain/
    intake/
    parsing/
    normalization/
    validation/
    canonical/
    persistence/
    integrations/
    services/
    cli/
```

Do not create unnecessary abstraction layers.

The design should optimize for:

```text
readability
testability
determinism
traceability
maintainability
```

---

# 11. RESPONSIBILITY SEPARATION

Maintain clear boundaries.

## Parser

Determines what fields appear to exist.

Does NOT write to SQL.

## Normalizer

Performs deterministic formatting corrections.

Does NOT invent values.

## Validator

Determines whether parsed values satisfy rules.

## Canonical Builder

Produces the exact fixed-width canonical MILSTRIP.

## Legacy Adapter

Communicates with existing SQL.

Does NOT contain MILSTRIP parsing logic.

## Application Service

Coordinates the workflow.

Avoid mixing these responsibilities.

---

# 12. NO LLM IN THE TRANSACTION PATH

This is a deterministic logistics interface.

Do not use an LLM to decide production values such as:

```text
NSN
quantity
document number
priority
DODAAC
condition code
inventory status
routing
address
```

AI may assist during:

```text
design
development
documentation
test generation
diagnosis
```

But the production parser should be deterministic.

---

# 13. RAW INPUT MODEL

Preserve the original request.

Conceptually:

```text
RawInput
    ↓
CandidateMILSTRIP
    ↓
ParsedMILSTRIP
    ↓
NormalizedMILSTRIP
    ↓
ValidatedMILSTRIP
    ↓
CanonicalMILSTRIP
```

Never destroy or overwrite the original payload.

The application should always be able to answer:

```text
What did we receive?

What did we parse?

What did we change?

Why was it changed?

What was submitted?
```

---

# 14. MILSTRIP FIXED-WIDTH SPECIFICATION

Reverse engineer the actual MILSTRIP contract from:

- Shawn's SQL;
- known-good examples;
- meeting explanations;
- available specifications;
- known production behavior.

Produce:

```text
MILSTRIP_SPEC.md
```

For each field document:

```text
Name

Start position

End position

Length

Data type

Required

Allowed values

Normalization

Validation

A2 behavior

A5 behavior

A5E behavior

Source/evidence

Confidence
```

Explicitly reconcile this specification against the SQL `SUBSTRING()` positions currently used.

Do not silently assume undocumented positions.

---

# 15. A2 / A5 / A5E

Treat record family differences as explicit domain behavior.

Determine:

```text
How A2 is identified

How A5 is identified

How A5E is identified

Address requirements

Customer grouping rules

Batch restrictions

Pricing behavior

Routing behavior

DODAAC behavior

Special exception handling
```

Distinguish between:

```text
technical requirement

business rule

legacy convention

temporary workaround
```

Do not convert Shawn's temporary workaround into permanent architecture unless needed.

---

# 16. DETERMINISTIC REPAIR

The system should correct formatting only when the repair is deterministic.

Example categories:

```text
EXACT

NORMALIZED

REPAIRED_DETERMINISTICALLY

AMBIGUOUS

INVALID
```

Example:

A priority code shifted one position due to a known spacing error may potentially be corrected when:

```text
the surrounding layout proves the shift

AND

the resulting value validates

AND

no alternative valid interpretation exists
```

An invalid NSN that happens to look similar to a valid NSN must NOT be automatically changed.

Ambiguity requires human action.

---

# 17. VALIDATION ENGINE

Organize validation logically.

## Structural

Examples:

```text
record family
length
positions
required fields
numeric fields
character constraints
```

## Semantic

Examples:

```text
quantity
priority range
condition
UI
routing values
```

## Reference

Potentially:

```text
ItemMaster
DODAAC
existing ERP order
address/config references
```

## Workflow

Examples:

```text
duplicate order
A5E requirements
batch restrictions
resubmission
```

Assign stable rule IDs where useful.

Example:

```text
MIL-STR-001
MIL-SEM-002
MIL-REF-004
MIL-BIZ-003
```

Do not build an elaborate validation framework if simple Python validators are sufficient.

---

# 18. PYTHON VALIDATORS

Prefer **small point validators** rather than creating another auditing subsystem.

Examples:

```python
validate_quantity()
validate_priority()
validate_nsn_format()
validate_nsn_exists()
validate_dodaac()
validate_document_number()
validate_record_length()
validate_a5e_address()
```

Reuse validators or validation utilities already available in the AEKR/tooling environment when practical.

If the expected validator pattern or utility is unclear, inspect **Leudani v2** and identify the Python validation approach used there.

Reuse the useful pattern rather than designing another validation framework from scratch.

The objective is:

```text
input
→ validator
→ PASS / FAIL
→ precise reason
```

Validators must be deterministic and easy to unit test.

---

# 19. ERROR MODEL

Errors should be understandable by operators.

Avoid returning only:

```text
SQL Error 245
```

Prefer domain errors such as:

```text
MIL-SEM-003

Quantity must contain five numeric characters.

Received:
0A520
```

Store technical diagnostic details separately.

Design an error model usable by:

```text
CLI
future API
future UI
logs
tests
```

---

# 20. DATABASE REFERENCE ACCESS

Python may need to query existing reference data.

Potential examples:

```text
ItemMaster
cfg_dodaac_active
existing ERP_ORDER
```

Prefer the smallest access surface possible.

Evaluate:

```text
read-only SQL identity

restricted views

restricted stored procedures

reference adapter
```

Do not give the application unnecessary database privileges.

---

# 21. WRITE CONTRACT

The Python application should not directly manipulate arbitrary legacy tables.

Design a narrow integration contract.

Potential architecture:

```text
Python Application
       ↓
Legacy SQL Adapter
       ↓
Dedicated Stored Procedure
       ↓
Required staging / operational logic
```

Potential contract:

```text
dbo.usp_Milstrip_Submit
```

or:

```text
dbo.usp_Milstrip_SubmitBatch
```

The exact contract must emerge from discovery.

Python should ideally require:

```text
EXECUTE
```

rather than broad write permissions.

---

# 22. STORED PROCEDURE DESIGN

Review the existing prototype SQL and determine how its relevant logic should become a controlled production interface.

Evaluate:

```text
single MILSTRIP submission

batch submission

transactions

duplicate handling

zero-row insert

errors

return values

idempotency

timeouts

partial success

retries

concurrency

status handling
```

The resulting procedure should return machine-readable information.

Conceptual example:

```json
{
  "status": "SUCCESS",
  "erp_order": "SL470162240DCV",
  "submitted": true,
  "duplicate": false
}
```

Do not lock into this exact contract without design analysis.

---

# 23. REVIEW EXISTING SQL CAREFULLY

The current prototype is valuable evidence but not automatically the final implementation.

Specifically inspect:

```text
conditional inserts

unconditional status updates

unused variables

hard-coded values

price handling

A5/A5E handling

timezone logic

duplicate detection

ItemMaster validation

DODAAC lookup

loops

transaction behavior
```

Where the existing SQL contains a workaround, determine whether it belongs:

```text
in Python

in the submission SP

in legacy SQL

or nowhere in the new design
```

---

# 24. IDEMPOTENCY

Design explicit protection against duplicate processing.

Consider:

```text
same ticket submitted twice

same MILSTRIP submitted twice

CLI retry

network timeout

application crash

database commit followed by lost connection

user unsure whether submission succeeded
```

Determine an appropriate idempotency key.

Potential signals:

```text
source system
ticket/message ID
canonical record
ERP_ORDER
record hash
```

Define expected behavior clearly.

---

# 25. STATE MODEL

Use an explicit but simple application state model.

Evaluate states such as:

```text
RECEIVED

PARSED

VALIDATED

REQUIRES_REVIEW

READY

SUBMITTED

CONFIRMED

REJECTED

FAILED
```

Do not create state-machine complexity unless required.

Clearly define what each state means.

Particularly distinguish:

```text
SUBMITTED
```

from:

```text
CONFIRMED
```

---

# 26. DOWNSTREAM OWNERSHIP

Determine exactly where the new application's responsibility ends.

Possible checkpoints include:

```text
staging row created

download_ship940 created

ShipMaster created

Boomi picked up record

ADF moved output

SCALE imported order
```

These states are different.

Define which ones the new application:

```text
controls

observes

does not own
```

Do not claim end-to-end success merely because the first SQL insert succeeded.

---

# 27. TRANSACTIONS

Define transaction behavior.

Determine:

```text
one transaction per MILSTRIP?

one transaction per batch?

partial batch success allowed?

what happens if 9 of 10 succeed?

what happens if the SP succeeds and Python disconnects?

what happens if Python retries?
```

Favor recoverability and simple semantics.

---

# 28. APPLICATION DATA MODEL

If a new application database is selected, create a minimal schema.

Possible concepts:

```text
intake

raw_payload

milstrip_record

validation_result

submission

processing_event
```

Add other entities only when justified.

Design proper:

```text
PK
FK
UNIQUE
CHECK
indexes
timestamps
status constraints
```

Do not reproduce legacy database patterns unnecessarily.

---

# 29. TRACEABILITY

Each processing attempt should carry a stable:

```text
correlation_id
```

The design should make it possible to follow:

```text
Freshservice/email request
        ↓
intake
        ↓
candidate
        ↓
canonical MILSTRIP
        ↓
submission
        ↓
ERP_ORDER
        ↓
legacy processing
```

Where reasonably possible, preserve this relationship without modifying the downstream architecture excessively.

---

# 30. CLI MVP

Design the first usable version as a CLI.

Potential commands:

```bash
milstrip parse request.txt

milstrip validate request.txt

milstrip submit request.txt --dry-run

milstrip submit request.txt --commit
```

Default behavior should be safe.

The CLI should clearly show:

```text
records detected

records parsed

records normalized

records repaired

records valid

records blocked

errors

warnings

ERP_ORDER

submission result
```

The MVP should not require Freshservice API integration.

Manual copy/paste or file input is acceptable initially.

---

# 31. FUTURE INPUT ADAPTERS

The domain engine must not depend directly on Freshservice.

Design adapters so future sources can include:

```text
text file

clipboard

Freshservice

email

CSV

internal API

Power Apps

web application
```

All input adapters should ultimately generate the same domain input.

---

# 32. FUTURE OPERATIONS UI

Do not design the detailed UI now.

Define only the capabilities required later.

Likely:

```text
paste/import request

display detected records

show original

show normalized

highlight changes

display validation failures

request missing data

approve

submit

view result

search previous submissions
```

The domain engine should remain usable independently of the UI.

---

# 33. SECURITY

Design appropriate security without turning this Full Design into a separate security-audit project.

Address:

```text
service identity

database credentials

least privilege

secret storage

environment separation

operator authentication

authorization

sensitive address information

log redaction

connection encryption
```

No credentials should be stored in source control.

Prefer separate:

```text
DEV

TEST

PROD
```

configuration.

---

# 34. OBSERVABILITY

Design useful operational telemetry.

At minimum make it possible to know:

```text
what was received

whether it parsed

whether it validated

whether it submitted

why it failed

what ERP order resulted
```

Potential metrics:

```text
records_received

records_valid

records_repaired

records_rejected

duplicates

submission_success

submission_failure

manual_review_required

processing_duration
```

Do not build enterprise-scale observability infrastructure for a small workflow.

---

# 35. TEST STRATEGY

This project should be heavily driven by real examples.

Build a fixture corpus.

At minimum include:

```text
valid A2

valid A5

valid A5E

HTML contamination

spacing shift

extra characters

invalid NSN

unknown NSN

invalid quantity

invalid priority

missing field

duplicate

address exception

multiple records

mixed batch

retry scenario

SQL failure
```

Use:

```text
unit tests

parser tests

point-validator tests

canonical builder tests

database integration tests

stored procedure contract tests

selected end-to-end tests
```

Every meaningful production anomaly discovered later should become a regression fixture when appropriate.

---

# 36. GOLDEN CASES

Use known manually processed examples as golden cases.

Compare:

```text
input received
        ↓
Shawn's accepted/corrected result

versus

input received
        ↓
new parser result
```

The goal is byte-for-byte or field-for-field equivalence where appropriate.

Differences must be understood, not automatically treated as either system being correct.

---

# 37. TIMEZONE

Investigate the current Central Time handling.

Define clearly:

```text
storage timezone

display timezone

business-date timezone
```

Use proper timezone-aware behavior.

Do not confuse fixed CST with US Central local time including daylight-saving changes.

---

# 38. CONFIGURATION

Identify what should remain code and what should become configuration.

Potential configuration candidates:

```text
business mappings

customer-specific handling

routing rules

known reference mappings
```

Do not create configuration tables for constants that are genuinely part of the MILSTRIP specification.

Keep the design simple.

---

# 39. DEPLOYMENT EVOLUTION

Design for a reasonable evolution:

```text
Developer CLI
      ↓
Internal CLI
      ↓
Controlled production execution
      ↓
Internal API
      ↓
Operations UI
```

Evaluate future Azure deployment options only as needed.

Possible later options may include:

```text
Azure Function

App Service

Container App

small internal service
```

Do not introduce Kubernetes or complex distributed architecture without a real requirement.

---

# 40. FAILURE BEHAVIOR

Document major failure scenarios.

At minimum:

```text
malformed input

ambiguous input

unknown item

invalid DODAAC

duplicate

database unavailable

SP failure

SP timeout

connection lost after commit

partial batch

downstream delay

Boomi unavailable

SCALE unavailable
```

For each describe:

```text
What happens?

Can the operator retry?

Can the system retry?

Could retry duplicate the order?

What status should be displayed?
```

Keep the matrix practical.

---

# 41. HUMAN REVIEW MODEL

Use a simple three-lane concept.

```text
GREEN
deterministic and valid

YELLOW
deterministically repaired or requires confirmation

RED
invalid or ambiguous
```

For the initial MVP, human approval may remain required before submission.

Automation can become more aggressive later once production evidence supports it.

---

# 42. REQUIRED DESIGN DOCUMENTS

Produce a concise but complete design package.

Recommended structure:

```text
/design

00_EXECUTIVE_SUMMARY.md

01_CURRENT_STATE.md

02_REQUIREMENTS_AND_SCOPE.md

03_MILSTRIP_SPEC.md

04_DOMAIN_MODEL.md

05_TARGET_ARCHITECTURE.md

06_DATABASE_STRATEGY.md

07_LEGACY_INTEGRATION_BOUNDARY.md

08_PYTHON_DESIGN.md

09_VALIDATION_DESIGN.md

10_SUBMISSION_SP_CONTRACT.md

11_STATE_IDEMPOTENCY_TRANSACTIONS.md

12_SECURITY_AND_OPERATIONS.md

13_TEST_STRATEGY.md

14_IMPLEMENTATION_PLAN.md

15_OPEN_QUESTIONS.md

/adr

ADR-001-DATABASE-STRATEGY.md
ADR-002-LEGACY-BOUNDARY.md
ADR-003-SUBMISSION-CONTRACT.md

/diagrams

current-state.mmd
target-state.mmd
submission-sequence.mmd
legacy-boundary.mmd
```

Do not create additional ADRs unless the decision is genuinely architectural.

Do not create empty directories or placeholder documents.

---

# 43. REQUIRED TARGET ARCHITECTURE DIAGRAM

At minimum show:

```text
Source
   ↓
Input Adapter
   ↓
MILSTRIP Domain Engine
   ├── Parser
   ├── Normalizer
   ├── Validators
   └── Canonical Builder
   ↓
Application Service
   ↓
Application DB, if selected
   ↓
Legacy SQL Adapter
   ↓
Controlled Stored Procedure
   ↓
Existing 3PL Pipeline
   ↓
Boomi / ADF
   ↓
SCALE
```

Clearly identify system ownership boundaries.

---

# 44. HUMAN QUESTIONS

Prepare only the questions actually needed to complete the design.

Focus primarily on unresolved MILSTRIP rules.

Examples:

```text
official field positions

unused characters

A5E requirements

exception address behavior

customer grouping

duplicate definition

resubmission

price semantics

routing semantics

when a record is considered successfully handed off
```

Do not create an enormous interview questionnaire.

Prefer 10 precise questions over 50 generic questions.

---

# 45. IMPLEMENTATION PLAN

Once architecture is stable, produce the Development roadmap.

A likely structure:

```text
Sprint 0 — Contract confirmation

Sprint 1 — Domain model + parser

Sprint 2 — Normalization + validators

Sprint 3 — Canonical builder

Sprint 4 — Legacy SQL integration

Sprint 5 — CLI

Sprint 6 — Golden-case validation

Sprint 7 — Controlled pilot

Sprint 8 — Freshservice adapter

Sprint 9 — Operations UI
```

Adjust based on design findings.

Each development sprint should contain small micro-sprints.

Example:

```text
Sprint 2

2.1 quantity validator

2.2 priority validator

2.3 NSN structural validator

2.4 ItemMaster reference validator

2.5 DODAAC validator

2.6 parser-validation integration

2.7 unit tests
```

Do not put implementation into this Full Design run beyond code needed to validate feasibility.

---

# 46. MVP EXIT CRITERIA

Define measurable criteria.

At minimum consider:

```text
canonical output deterministic

ambiguous values never silently invented

invalid NSNs blocked

priority validation correct

quantity validation correct

dry-run writes nothing

legacy access uses restricted credentials

duplicate submission protected

submission result machine-readable

errors operator-readable

golden fixtures pass

existing downstream process remains operationally unchanged
```

Refine these based on discovery.

---

# 47. BUSINESS SUCCESS

The system exists to remove manual operational dependency.

Define meaningful metrics such as:

```text
handling time per urgent request

percentage automatically parsed

percentage requiring human correction

invalid requests caught before SQL submission

manual SQL interaction eliminated

duplicate submissions prevented

Shawn interventions required
```

Keep metrics small and useful.

---

# 48. PILOT STRATEGY

Design a gradual rollout.

Prefer:

```text
SHADOW

Python processes examples without writes.

        ↓

COMPARE

Compare Python result against Shawn's manual result.

        ↓

ASSISTED

Python prepares and validates.
Human approves.

        ↓

CONTROLLED PRODUCTION

Python submits validated cases.

        ↓

OPERATIONS

Authorized Operations users handle routine requests.
```

Do not jump directly to unattended production.

---

# 49. AVOID OVERENGINEERING

This workflow does not justify unnecessary distributed architecture.

Do not introduce without evidence:

```text
Kafka

Kubernetes

service mesh

microservice fleet

event sourcing

complex workflow engines

multiple databases

distributed queues
```

A solution similar to:

```text
Python
+
small application database
+
controlled SQL integration
```

may be entirely sufficient.

Prefer the smallest robust design.

---

# 50. OUT OF SCOPE

Unless directly required:

```text
Boomi redesign

ADF redesign

SCALE changes

legacy DB performance tuning

rewriting the complete 3PL system

inventory redesign

billing redesign

receipt redesign

carrier integration redesign

general database cleanup
```

Document relevant legacy problems as observations only when they affect this application's design.

---

# 51. AUDIT POLICY

This project intentionally uses a **lightweight audit model**.

Do NOT create:

```text
per-sprint audits

per-micro-sprint audits

multi-agent audit rounds

auditor-of-auditor loops

separate security auditor

separate architecture auditor

separate code auditor

continuous adversarial reviews
```

Engineering validation during design and development is still expected.

That includes normal:

```text
tests

syntax checks

type checks

schema validation

acceptance checks

evidence verification
```

But these are not separate audit phases.

There is exactly:

# ONE FINAL AUDIT

It occurs only after the Full Design package is complete.

---

# 52. FINAL AUDIT

Perform one final consolidated audit.

The audit has exactly three major responsibilities.

---

## AUDIT 1 — DOCUMENT CONSISTENCY

Compare the complete design package against itself.

Verify that the documents:

```text
do not contradict each other

use the same terminology

describe the same architecture

use the same database decision

use the same system boundary

use compatible data models

use compatible state definitions

use compatible interface contracts

use the same MILSTRIP field assumptions
```

Check that diagrams correspond to the written architecture.

Check that ADR decisions are reflected in the final design.

Check that implementation planning follows the architecture that was actually selected.

The question is:

> Do all design artifacts describe one coherent system?

Report only meaningful inconsistencies.

Do not produce stylistic nitpicks.

---

## AUDIT 2 — CODE / DESIGN ALIGNMENT

If any code, pseudo-production code, SQL, schemas, stored procedures, Python structures, interfaces, or technical prototypes were created during Full Design, compare them against the approved design.

Verify:

```text
module responsibilities align

database boundaries align

data models align

SP contracts align

validation rules align

state behavior aligns

idempotency assumptions align

security boundaries align
```

The question is:

> Does the technical artifact implement or demonstrate what the design actually says?

Do not redesign the application during this audit.

If something is wrong:

```text
identify mismatch

identify affected artifact

state expected behavior

recommend correction
```

---

## AUDIT 3 — POINT VALIDATION

Run focused mechanical validation using available Python validators and development tools.

Prefer existing validators already available in the environment/tooling.

Where necessary, inspect **Leudani v2** to identify and reuse the established Python point-validation approach.

Do not invent a large new validator framework specifically for this project.

Validation should be targeted.

Examples:

```text
Python syntax

imports

type validation where configured

schema validation

configuration structure

SQL contract consistency

Mermaid syntax if validator exists

JSON examples

canonical MILSTRIP length

known field-position assertions

sample parser fixtures

sample point validators

dry-run behavior where executable
```

Use the appropriate available tool for each validation.

If a validator is not available, state:

```text
NOT MECHANICALLY VALIDATED
```

rather than pretending the check occurred.

---

# 53. FINAL AUDIT OUTPUT

Produce one:

```text
FINAL_AUDIT.md
```

Use the following structure:

```text
# Final Audit

## 1. Document Consistency

PASS
or
PASS WITH OBSERVATIONS
or
FAIL

Findings:
...

## 2. Code / Design Alignment

PASS
or
PASS WITH OBSERVATIONS
or
FAIL
or
NOT APPLICABLE

Findings:
...

## 3. Point Validation

PASS
or
PASS WITH OBSERVATIONS
or
FAIL

Validators executed:
...

Results:
...

## Final Verdict

PASS
PASS WITH OBSERVATIONS
FAIL
```

Use severity only when useful:

```text
BLOCKER

MAJOR

MINOR

OBSERVATION
```

Do not manufacture findings to make the audit look valuable.

Zero findings is an acceptable result.

---

# 54. AUDIT CORRECTION RULE

If the Final Audit finds a:

```text
BLOCKER
```

or material:

```text
MAJOR
```

correct the affected design artifact once.

Then rerun only the relevant failed mechanical validation.

Do NOT start another complete audit cycle.

Update:

```text
FINAL_AUDIT.md
```

with the corrected result.

The process then ends.

---

# 55. DESIGN PHILOSOPHY

Apply these principles throughout the project:

> Preserve what works downstream.

> Fix the unstable manual boundary.

> Keep the new bounded context small.

> Do not inherit the legacy database unnecessarily.

> Deterministic rules over probabilistic guessing.

> Never invent logistics data.

> Preserve raw evidence.

> Make every transformation explainable.

> Parser logic is not database logic.

> Application state is not shipment state.

> Use the smallest practical legacy write contract.

> Prefer point validators over audit bureaucracy.

> Every real edge case can become a regression fixture.

> Build the reliable core before the UI.

> Complexity must justify itself.

---

# 56. PRIMARY DESIGN QUESTION

Everything should ultimately answer:

> What is the smallest, safest, independently maintainable Python-based system that can transform inconsistent human MILSTRIP requests into validated canonical records and hand them into the existing Travis 3PL pipeline without inheriting the architectural debt of the current operational database?

---

# 57. START

Start with:

```text
Sprint 0 — Evidence and Current-State Discovery
```

Then proceed through Full Design incrementally.

Do not implement production functionality.

Do not perform intermediate audits.

Use normal technical validation throughout the work.

When the complete design package is ready, perform the single **FINAL AUDIT** defined above.