# Android Validation Agent Design

## Overview

This document defines a validation-oriented agent system for Android development. The system works alongside Cursor or Codex: after an implementation agent completes a feature, the validation agent verifies whether the requirement is actually complete, produces actionable issue reports when it is not, and drives an iterative repair loop until the feature is verified or blocked for human review.

The design goal is to avoid self-certification by the implementation agent. Requirement understanding, acceptance judgement, execution evidence, and repair-loop orchestration are owned by the validation system, while code changes remain the responsibility of Cursor or Codex.

## Goals

- Verify whether an Android requirement is truly complete, not just apparently implemented.
- Cover both UI behavior and business-flow behavior with end-to-end validation.
- Run primarily on Android Emulator, with optional device re-verification when needed.
- Produce structured issue reports and repair prompts for Cursor or Codex.
- Support repeated validation-repair cycles until completion, a stop condition, or human intervention.

## Non-Goals

- Replace all manual QA processes in the first version.
- Support every Android feature type in the MVP.
- Fully automate real-payment, high-risk external-account, or destructive workflows.
- Depend on the implementation agent's own success judgement.

## Primary Users

- Android developers using Cursor or Codex to implement features.
- Technical product or QA collaborators who want evidence-backed completion checks.
- A supervising engineer who can intervene when the system is blocked or uncertain.

## High-Level Workflow

1. A user submits a requirement and environment context as a validation request.
2. The system converts natural-language requirement sources into a structured acceptance spec.
3. The system maps acceptance items into an executable test plan.
4. The system prepares the emulator environment, installs the app, and executes validation using Maestro CLI plus adb support commands.
5. The system collects artifacts such as screenshots, recordings, logs, and step results.
6. The system judges each acceptance item against the collected evidence.
7. If failures are found, the system produces issue reports and a repair prompt for Cursor or Codex.
8. The orchestration layer triggers the next implementation-repair cycle or stops on defined conditions.

## System Components

### 1. Intake

The Intake component normalizes one validation request into a machine-readable payload. It gathers:

- requirement text and requirement sources
- target build or branch reference
- app startup or install instructions
- test account information
- environment mode and device preference
- operator constraints such as maximum repair loops

Output: `validation_request`

### 2. Spec Builder

The Spec Builder converts requirement sources into a structured acceptance spec. This is the authoritative interpretation layer for scope and completion criteria.

Responsibilities:

- define in-scope and out-of-scope behavior
- split the requirement into acceptance items
- separate UI assertions from business-flow assertions
- capture preconditions, steps, expected outcomes, and required evidence
- identify ambiguous or missing requirement details before execution

Output: `acceptance_spec`

### 3. Test Planner

The Test Planner maps each acceptance item to executable checks.

Responsibilities:

- choose Maestro flows for UI-driven interactions
- choose adb commands for install, launch, deep link, activity inspection, and log capture
- determine whether a case can run on emulator or should be flagged for optional device re-verification
- declare assertions and required artifacts for each case

Output: `test_plan`

### 4. Executor

The Executor runs the test plan and records evidence.

Responsibilities:

- prepare emulator or device environment
- install and launch the app
- execute Maestro CLI flows
- run adb helper commands
- record screenshots, videos, logs, and per-step outcomes

Output: `execution_run`

### 5. Judge and Reporter

The Judge and Reporter evaluate whether the collected evidence satisfies the acceptance spec.

Responsibilities:

- classify acceptance items as passed, failed, or uncertain
- produce machine-readable judgement output
- generate issue reports for actionable failures
- generate human-readable reports and repair prompts for implementation agents

Output: `judgement_result`, `issue_report`, `repair_prompt`

### 6. Repair Loop Manager

The Repair Loop Manager drives repeated execution until the feature is verified or halted.

Responsibilities:

- send repair prompts to Cursor or Codex in automatic mode
- persist loop history and outcomes
- detect stop conditions
- support a manual fallback mode where the operator copies the repair prompt themselves

## Execution Model

The default validation mode is emulator-first. The system should support optional device re-verification for scenarios that are more sensitive to real-device behavior, but this is not required for the first MVP path.

The execution stack for MVP is:

- Maestro CLI as the main UI automation runner
- YAML flows as the primary executable test description
- adb as the support tool for environment control and evidence collection

Maestro Studio may be useful for debugging or authoring flows, but it is not a required runtime dependency for the validation loop.

## Core State Machine

Each validation request progresses through the following states:

1. `REQUESTED`
The system has received a new validation request.

2. `SPEC_READY`
The system has produced a structured acceptance spec. If the requirement cannot be interpreted reliably, the request should stop here with an ambiguity report.

3. `PLAN_READY`
The acceptance spec has been mapped into an executable test plan.

4. `ENV_PREPARED`
The emulator or device is ready, the app is installed, and required setup has completed.

5. `RUNNING`
The validation plan is being executed.

6. `EVIDENCE_COLLECTED`
Execution is complete and artifacts have been stored.

7. `JUDGED`
Acceptance items have been evaluated against the evidence.

8. `REPAIR_REQUESTED`
The system has produced issue reports and a repair prompt for the implementation agent.

9. `AWAITING_FIX`
The system is waiting for the next build, code change, or implementation-agent result.

10. `VERIFIED`
All required acceptance items have passed.

11. `BLOCKED`
The loop cannot proceed without human intervention.

## Data Contracts

The system should use JSON as the primary machine-readable format. Markdown reports are derived outputs for human consumption.

### Validation Request

Suggested fields:

- `request_id`
- `feature_name`
- `goal`
- `requirement_sources[]`
- `build`
- `environment`
- `credentials`
- `constraints`

### Acceptance Spec

Suggested fields:

- `spec_id`
- `feature_name`
- `in_scope[]`
- `out_of_scope[]`
- `acceptance_items[]`

Each acceptance item should contain:

- `id`
- `title`
- `type`
- `priority`
- `preconditions[]`
- `steps[]`
- `expected[]`
- `evidence[]`

### Test Plan

Suggested fields:

- `plan_id`
- `spec_id`
- `cases[]`

Each case should contain:

- `case_id`
- `acceptance_item_id`
- `tooling`
- `environment`
- `assertions[]`
- `artifacts[]`

### Execution Run

Suggested fields:

- `run_id`
- `request_id`
- `plan_id`
- `status`
- `device`
- `started_at`
- `finished_at`
- `case_results[]`

### Judgement Result

Suggested fields:

- `judgement_id`
- `run_id`
- `summary`
- `item_results[]`

Each item result should contain:

- `acceptance_item_id`
- `status`
- `reason`
- `linked_case_ids[]`
- `confidence`

### Issue Report

Suggested fields:

- `issue_id`
- `severity`
- `acceptance_item_id`
- `title`
- `reproduction_steps[]`
- `expected_result`
- `actual_result`
- `evidence`
- `suspected_causes[]`
- `repair_hint`

### Repair Prompt

The repair prompt is a structured prompt for Cursor or Codex, generated from issue reports. It should include:

- feature context
- failed acceptance items
- reproduction steps
- expected versus actual results
- artifact paths
- likely code areas or diagnostic hints
- explicit instruction to re-run validation after the fix

## Failure Taxonomy

The system should distinguish between product issues and validation-system issues.

### Product Bug

The app behavior does not satisfy the requirement. Examples:

- UI element missing or incorrect
- navigation path wrong
- state not refreshed
- business result incorrect

Action: generate issue report and repair prompt, then continue the loop.

### Environment Failure

The runtime environment is not usable. Examples:

- emulator unavailable
- installation failure
- backend test environment unavailable
- test account invalid

Action: block the loop and request human intervention.

### Test Script Failure

The test asset is incorrect or unstable. Examples:

- Maestro selector broken
- flow timing issue
- malformed generated flow

Action: route to test-asset repair rather than product-bug repair.

### Uncertain Result

The execution completes but evidence is not strong enough for a reliable judgement.

Action: do not auto-pass. Prefer human review or a stronger verification strategy.

## Stop Conditions and Human Escalation

The loop should stop and escalate when any of the following occurs:

- the same high-priority acceptance item remains unresolved after the configured maximum loop count
- failure reasoning changes significantly across consecutive loops, indicating drift or instability
- environment failures exceed a configured threshold
- the request involves a high-risk action such as real payment or destructive account operations
- a high-priority item reaches an uncertain result

## Automatic and Manual Repair Modes

The system supports two repair handoff modes:

### Automatic Mode

The Repair Loop Manager automatically sends the generated repair prompt and issue report to Cursor or Codex, waits for the updated implementation result, and starts another validation loop.

### Manual Fallback Mode

The system writes the same repair prompt to disk for a human operator to copy into Cursor or Codex manually. This is the fallback path when automatic handoff is disabled, unavailable, or intentionally bypassed.

## Recommended MVP Scope

The first implementation should support one stable end-to-end path:

- one requirement submitted at a time
- one app under test
- emulator-first execution
- Maestro plus adb execution model
- structured acceptance spec generation
- structured issue reporting
- repair prompt generation
- repeated validation loops with a maximum-loop limit

The MVP should defer:

- large-scale concurrency
- real-device farms
- advanced visual diffing
- broad OCR-heavy verification
- high-risk external flows
- automatic code modification inside the validation system itself

## Recommended Repository Structure

```text
autoandroid/
  app/
    cli.py
    orchestrator.py
    models/
      request.py
      spec.py
      plan.py
      run.py
      issue.py
    services/
      intake_service.py
      spec_builder.py
      test_planner.py
      execution_service.py
      judgement_service.py
      repair_loop_manager.py
      prompt_builder.py
    integrations/
      maestro_runner.py
      adb_runner.py
      llm_provider.py
      cursor_adapter.py
      codex_adapter.py
    rules/
      failure_classifier.py
      stop_conditions.py
    templates/
      acceptance_spec_prompt.md
      repair_prompt.md
      issue_report.md
  flows/
    generated/
    stable/
  runs/
  config/
    settings.yaml
  tests/
```

## Flow Asset Strategy

The system should keep generated and stable Maestro flows separate.

### Generated Flows

Used for rapid translation from acceptance items into executable steps. These are useful for speed and experimentation but may be less stable.

### Stable Flows

Used for reusable, high-value, high-stability routines such as login, environment switching, or common entry paths. Over time, the system should prefer stable flows where appropriate.

## Design Constraints

- Requirement interpretation happens only in the Spec Builder.
- Acceptance judgement happens only against the structured acceptance spec, not against raw PRD text.
- Implementation agents must not self-certify completion.
- Every loop must persist machine-readable state and evidence to disk.
- Automatic and manual repair handoff must share the same underlying report structure.

## Open Assumptions

The following assumptions are accepted for the first implementation:

- the operator can provide test accounts and basic environment metadata
- the target app can be installed and launched in an automated test environment
- at least a subset of features can be verified through UI interactions, state observation, and logs
- the first version can operate locally rather than as a distributed service

## Success Criteria

The design is successful if the first implementation can:

- ingest one Android feature request
- build a structured acceptance spec from mixed requirement sources
- execute at least one emulator-based verification loop
- generate an actionable issue report when the feature is incomplete
- generate a repair prompt that can be used by Cursor or Codex
- repeat the loop until verified or blocked
