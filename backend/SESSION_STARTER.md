# Session Starter: Backend Onboarding

## Project Context

**What this is:** Backend for a Discord chat agent system (cybersecurity course project). Simulates a "self-bot" but built safely as a simulation.

**What the backend does:**

1. Manages chat conversations (tracks context, state)
2. Decides when to engage (scheduling, activity windows)
3. Generates responses (via LLM)
4. Detects user interest (engagement signals, logging)

**What the backend does NOT own:** Discord client library (teammate provides it, we use it)

---

## Architecture

**Stack:** Python 3.12+, async/await, SQLite, 5 minimal dependencies

**Structure:**

```
backend/
├── main.py              # Entry point, wires components
├── config.yaml          # Settings (LLM, rules, schedules)
├── core/
│   ├── pipeline.py      # Main flow: Event → Decision → Response → Deliver
│   ├── policy.py        # Should we respond? (rules, cooldowns, allow/deny)
│   └── scheduler.py     # Activity windows, organic timing
├── llm/
│   └── generator.py     # LLM integration (OpenAI)
├── interest/
│   └── detector.py      # Detect engagement, log it
└── state/
    └── store.py         # SQLite: conversations, cooldowns, audit_log, interest_log
```

**Data:** 4 SQLite tables (conversations, cooldowns, audit_log, interest_log)

---

## Key Concepts

### Flow

1. Discord event arrives (from client library)
2. **Policy** checks: should respond? (cooldowns, rules, active window)
3. If yes → **LLM** generates response
4. **Organic delay** (typing indicator, human-like wait)
5. Send via client library
6. **Log decision** + **check interest**

### Organic Behavior

-   Random jitter on timing (not robotic intervals)
-   Variable delays (human-like)
-   Context-aware cooldowns (longer after many interactions)

### Security Focus

-   Secrets in env vars only
-   Input validation
-   Audit logging (all decisions traced)
-   Rate limiting (respect Discord limits)

---

## Current State

**Status:** Skeleton structure created, ready for implementation

**Files:** All modules exist as placeholders with function signatures

**Next:** Implement components in order (see ARCHITECTURE.md implementation plan)

---

## How to Contribute

1. **Read ARCHITECTURE.md** for full design details
2. **Check existing code** - see what's implemented vs placeholder
3. **Follow the flow** - understand how components connect
4. **Keep it lean** - MVP scope, no over-engineering
5. **Test async** - everything is async/await
6. **Respect interfaces** - components communicate via defined signatures

---

## Important Constraints

-   **MVP only** - single guild, SQLite, config file (no admin UI yet)
-   **Lean code** - minimal dependencies, simple patterns
-   **Async everywhere** - Discord client is async, so we are too
-   **No code dumps** - keep design docs concise, code focused

---

## Quick Reference

**Interfaces:**

-   `policy.should_respond(event, context) → (bool, reason_codes)`
-   `llm.generate(context) → str`
-   `scheduler.is_active_window() → bool`
-   `scheduler.get_organic_delay() → seconds`
-   `interest.check(event, context) → interest_event | None`
-   `store.get_conversation()`, `update_conversation()`, `log_decision()`, `log_interest()`

**Config:** `config.yaml` (LLM keys, active hours, cooldowns)

**Database:** SQLite at `data/bot.db` (from config)

---

## Questions to Ask Before Coding

1. Does this fit MVP scope?
2. Is it async-compatible?
3. Does it respect the interfaces?
4. Is it testable?
5. Does it handle errors gracefully?

Ready to code? Start with the component you're working on, keep it simple, test it.
