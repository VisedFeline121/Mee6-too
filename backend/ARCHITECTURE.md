# Backend Architecture (Lean MVP)

## What This Backend Does

1. **Chat management** — track conversations, context
2. **Scheduling** — when to engage (activity windows, organic timing)
3. **Response generation** — call LLM, get response
4. **Interest detection** — log when users show engagement

## What This Backend Uses

-   **Discord client library** — provided by teammate, exposes events + send methods

---

## Stack

**Runtime:** Python 3.12+ (async/await)

**Dependencies:**

-   `aiosqlite` — async SQLite
-   `pyyaml` — config parsing
-   `openai` — LLM API (pluggable)
-   `apscheduler` — scheduling with randomization
-   `pytest` + `pytest-asyncio` — testing

---

## Component Breakdown

```
backend/
├── main.py              # Entry point, wires everything
├── config.yaml          # Settings (LLM keys, rules, schedules)
├── core/
│   ├── pipeline.py      # Event → Decision → Response → Deliver
│   ├── policy.py        # Should we respond? (rules, cooldowns)
│   └── scheduler.py     # Activity windows, organic timing
├── llm/
│   └── generator.py     # Call LLM, return response
├── interest/
│   └── detector.py      # Detect engagement, log it
├── state/
│   └── store.py         # SQLite: config, conversations, logs
└── requirements.txt
```

**6 files + config. That's it.**

---

## Data (SQLite, 4 tables)

| Table           | Purpose                                       |
| --------------- | --------------------------------------------- |
| `conversations` | user/channel state, last interaction, context |
| `cooldowns`     | rate limiting (user, channel, global)         |
| `audit_log`     | decision traces (responded/skipped, why)      |
| `interest_log`  | engagement signals detected                   |

---

## Flow

**Reactive (Event-Driven):**

```
Discord Event (from client lib)
       │
       ▼
   Policy Check ──→ Skip? → Log reason, done
       │
       ▼ (proceed)
   Scheduler Check ──→ Outside window? → Queue for later
       │
       ▼ (in window)
   LLM Generate Response
       │
       ▼
   Organic Delay (typing, wait)
       │
       ▼
   Send via client lib
       │
       ▼
   Log decision + check interest
```

**Proactive (Periodic/Scheduled):**

```
APScheduler triggers periodic task
       │
       ▼
   Check interest_log for follow-ups
       │
       ▼
   Policy Check (same as reactive)
       │
       ▼
   Generate + Send (same as reactive)
```

**Note:** Scheduler handles both activity windows (when to respond) AND periodic tasks (initiate interactions).

---

## Interfaces (Just Signatures)

**Policy:** `should_respond(event, context) → (bool, reason_codes)`

**Generator:** `generate(context) → str`

**Scheduler:** `is_active_window() → bool`, `get_organic_delay() → seconds`, `schedule_periodic_task(callback, interval)` (APScheduler)

**Interest:** `check(event, context) → interest_event | None`

**Store:** `get_conversation()`, `update_conversation()`, `log_decision()`, `log_interest()`, `get_pending_followups()`

---

## MVP Scope

| In             | Out (Later)       |
| -------------- | ----------------- |
| Single guild   | Multi-guild       |
| SQLite         | Postgres          |
| Config file    | Admin UI          |
| Basic LLM call | Prompt tuning     |
| Log interest   | Alert on interest |

---

## Risks

| Risk                    | Mitigation                               |
| ----------------------- | ---------------------------------------- |
| LLM fails               | Fallback to silence (don't crash)        |
| Rate limited by Discord | Client lib handles, we respect cooldowns |
| Secrets leaked          | Env vars only, never in code/config      |

---

## Implementaition Plan

1. Set up project structure (6 files)
2. Implement policy + scheduler
3. Integrate LLM
4. Add interest detection
5. Wire to client library
