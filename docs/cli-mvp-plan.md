# CLI MVP — Initial State Plan

**Deadline:** 25 August 2026

**Goal:** Ship a terminal walkthrough of the **main peer-support flow** — not the full platform from `README.md`.

**Success looks like:** one end-to-end session where a user onboards, joins a seeded circle, completes one weekly cycle, sees preference-aware peer replies, then a Support Map–style summary.

---

## 1. Product slice

Prove this vertical slice only:

```text
Onboard → Support preferences → Join circle → Weekly cycle → Summary
```

Weekly cycle (single pass):

1. Private check-in
2. Guided reflection (fixed prompt from a tiny library)
3. Peer responses (user post + seeded / templated replies)
4. Optional small behavioural experiment
5. Printed “this week” summary (Support Map lite)

**Out of scope for this MVP**

- Auth / accounts
- Real matching algorithm
- Database / multi-device sync
- LLM facilitator or Safety Gateway
- Full crisis classifier or escalation queue (keyword stub is optional)
- Moderation dashboard, report/block UI
- PDPA flows, export, retention jobs
- Web UI, multi-week circle lifecycle, reactions

---

## 2. Design constraints

| Constraint | Choice |
|---|---|
| Interface | Terminal CLI only |
| Users | Single human user + **seeded fake peers** |
| Topic | One topic only (university stress) |
| Intelligence | Rule-based state machine + JSON templates — **no LLM** |
| Persistence | Local JSON files under `data/` |
| AI role | Deferred; structure stages so a bounded facilitator can plug in later |
| Language / tone | Peer support only — no diagnosis, therapy claims, or medication advice |

Core philosophy for this build: **predictable ritual first, sophisticated AI later.**

---

## 3. Suggested stack

Keep dependencies minimal:

- **Python 3.11+**
- Stdlib `input()` / `print()` *or* a thin CLI helper (`typer` / `click`) if preferred
- JSON for seed data and session state
- No web framework, no DB driver required

Suggested layout:

```text
Small-Circles/
  docs/
    cli-mvp-plan.md          # this file
  data/
    circle.json              # seeded members + preferences
    prompts.json             # 3–5 approved reflection prompts
    templates.json           # peer reply templates by preference
    experiments.json         # optional small-action suggestions
    session.json             # current run state (created at runtime)
  src/
    cli.py                   # entrypoint + menu loop
    flow.py                  # state machine / stage handlers
    models.py                # thin dataclasses / typed dicts
    storage.py               # load/save JSON
    replies.py               # preference banner + template rendering
    crisis.py                # optional keyword stub
  README.md                  # product vision (existing)
```

---

## 4. State machine

Stages are explicit. Advance only when the current step completes. Persist `session.json` after every successful stage transition.

```text
START
  → ONBOARD          # display name + confirm topic
  → PREFERENCES      # pick 1–2 support preferences
  → JOIN_CIRCLE      # auto-join seeded circle (no matching)
  → CHECK_IN         # energy / stress / connection + short text
  → REFLECTION       # show one prompt → user answer
  → PEER_POST        # user posts to circle
  → PEER_REPLIES     # show preference banner + 2–3 templated replies
  → EXPERIMENT       # offer one optional small action (accept / skip)
  → SUMMARY          # print Support Map lite
  → DONE
```

**Resume behaviour:** if `session.json` exists and `stage != DONE`, offer Resume and continue from the saved stage.

**Optional interrupt:** `CRISIS_STUB` — if free-text input matches a small keyword list, pause normal flow, print fixed Singapore crisis resources, and offer exit. Do not diagnose or continue as a counsellor.

---

## 5. CLI menu tree (happy path)

```text
Small Circles (CLI MVP)
──────────────────────
1. Start this week's circle
2. Resume session (if session.json exists)
3. Quit

→ Start
  Display name: ____
  Topic: University stress (fixed)
  Community reminder: peer support, not therapy / diagnosis

→ Preferences (multi-select, max 2)
  [ ] Listening
  [ ] Shared experience
  [ ] Practical ideas
  [ ] Gentle accountability
  [ ] Encouragement

→ Circle
  You joined Circle #demo-uni-01 (5 members)
  Members listed with preference tags

→ Check-in
  Energy (1–5): _
  Stress (1–5): _
  Connection (1–5): _
  What's on your mind? (1–2 sentences)

→ Reflection
  Prompt: "<from prompts.json>"
  Your reflection: ____

→ Peer post
  Share with the circle (what others will respond to): ____
  Banner shown before replies:
    Support preference: Listening
    "This person would prefer empathy rather than advice."

→ Peer replies
  2–3 seeded replies using templates keyed to user preference

→ Experiment
  Suggestion: "<one small action>"
  [A] I'll try it  [S] Skip

→ Summary
  My Support Map (this week)
  Energy / Stress / Connection bars
  Noticed / experiment status
  Done.
```

### Input validation (minimum)

- Display name: non-empty, reasonable length
- Preference: at least one, at most two
- Check-in scores: integers 1–5
- Free-text fields: non-empty; trim whitespace
- Invalid menu choices: re-prompt without crashing

---

## 6. Seed data schemas

### `data/circle.json`

```json
{
  "id": "demo-uni-01",
  "topic": "university_stress",
  "title": "University stress circle",
  "members": [
    {
      "id": "peer-1",
      "display_name": "River",
      "preferences": ["listening"],
      "persona_note": "quiet listener"
    },
    {
      "id": "peer-2",
      "display_name": "Sage",
      "preferences": ["shared_experience"],
      "persona_note": "shares similar Uni stories"
    },
    {
      "id": "peer-3",
      "display_name": "Kai",
      "preferences": ["practical_ideas"],
      "persona_note": "offers optional tips when asked"
    },
    {
      "id": "peer-4",
      "display_name": "Ash",
      "preferences": ["gentle_accountability"],
      "persona_note": "checks in on small steps"
    }
  ]
}
```

Include 4–5 fake members. The human user is appended into the circle at `JOIN_CIRCLE`.

### `data/prompts.json`

```json
{
  "topic": "university_stress",
  "prompts": [
    {
      "id": "energy-drain",
      "text": "What has been taking most of your energy this week?",
      "rationale": "Noticing load without diagnosing"
    },
    {
      "id": "what-helped",
      "text": "Was there anything small that helped, even briefly?",
      "rationale": "Recognising strengths and helpful conditions"
    },
    {
      "id": "self-kindness",
      "text": "If a friend were in your situation, what would you want them to hear?",
      "rationale": "Self-compassion via perspective shift"
    }
  ]
}
```

Ship 3–5 prompts; MVP selects one for the session (first, or deterministic pick from session seed).

### `data/templates.json`

```json
{
  "listening": [
    "It sounds like {summary}. I'm here with you — no advice unless you want it."
  ],
  "shared_experience": [
    "I've felt something similar with coursework. What helped me a little was {hint}."
  ],
  "practical_ideas": [
    "One small thing that sometimes helps: {hint}. Take or leave it."
  ],
  "gentle_accountability": [
    "If you want, we can check in next time on one tiny step you choose."
  ],
  "encouragement": [
    "You're showing up and reflecting — that already counts for something."
  ]
}
```

Replies must respect the **poster's** preference, not the peer's. Prefer 2–3 distinct peer voices per post.

### `data/experiments.json`

```json
{
  "topic": "university_stress",
  "experiments": [
    {
      "id": "one-evening-off",
      "text": "Take one evening away from coursework this week, if that feels manageable."
    },
    {
      "id": "one-trusted-message",
      "text": "Send one short message to someone you trust."
    }
  ]
}
```

Present as optional suggestion, never as clinical prescription.

### `data/session.json` (runtime)

```json
{
  "stage": "CHECK_IN",
  "user": {
    "id": "user-local",
    "display_name": "Wong",
    "preferences": ["listening"]
  },
  "circle_id": "demo-uni-01",
  "prompt_id": "energy-drain",
  "check_in": null,
  "reflection": null,
  "post": null,
  "replies": [],
  "experiment": null,
  "created_at": "...",
  "updated_at": "..."
}
```

Example populated fields after progress:

```json
{
  "check_in": {
    "energy": 2,
    "stress": 4,
    "connection": 2,
    "note": "Deadlines stacking up and I feel behind."
  },
  "reflection": {
    "prompt_id": "energy-drain",
    "answer": "Group projects and not sleeping enough."
  },
  "post": {
    "text": "Feeling wiped by continuous assessments."
  },
  "replies": [
    {
      "from": "River",
      "text": "It sounds like continuous assessments have been draining. I'm here with you — no advice unless you want it."
    }
  ],
  "experiment": {
    "id": "one-evening-off",
    "status": "accepted"
  }
}
```

---

## 7. Preference → reply behaviour

| User preference | Reply behaviour |
|---|---|
| Listening | Empathy / reflecting language; avoid “you should” |
| Shared experience | Peer shares a similar Uni moment; no diagnosis |
| Practical ideas | One optional tip; framed as suggestion |
| Gentle accountability | Offer a check-back on a user-chosen step |
| Encouragement | Warm acknowledgement without toxic positivity |

Before peer replies, always print the preference banner (product differentiator from README §4–5).

**Discouraged language in all shipped copy**

- Diagnosis or clinical labels
- Medication or treatment instructions
- “You should…” / coercive framing
- Toxic positivity (“just stay positive”)
- Claims of professional authority

---

## 8. Build work breakdown

Complete all must-have work by the deadline. Optional items only after the happy path is solid.

### Must have

1. **Project skeleton** — `src/`, `data/`, runnable entrypoint
2. **Seed data** — circle, prompts, templates, experiments JSON
3. **Storage layer** — load seeds; create / update / resume `session.json`
4. **Main menu** — Start / Resume / Quit
5. **Stages** — ONBOARD through SUMMARY, with save after each transition
6. **Preference banner + templated peer replies** — keyed to poster preference
7. **Support Map summary** — check-in bars, reflection snippet, experiment status
8. **How to run** — short run instructions (in this doc or a brief note)

### Should have

- Resume mid-flow without losing filled fields
- Clear re-prompts on invalid input
- 4–5 seeded peers with distinct names
- At least two preference-aligned reply templates used in one session

### Nice to have (same deadline if ready)

- Keyword crisis stub with Singapore resources
- Slightly richer Support Map (“what I’ve noticed” bullets from check-in + reflection)
- Start-over that archives or replaces `session.json`

### Do not start before deadline freeze

- Matching, auth, LLM, moderation UI, multi-week closure rituals, real multi-user networking

---

## 9. Minimal crisis stub (optional)

Include only after the happy path works:

- Small keyword list on free-text inputs (check-in note, reflection, peer post)
- On match: stop normal stage advancement, print fixed Singapore crisis resources, offer exit
- Do **not** build classifier, escalation queue, moderator notifications, or agent autonomy levels

Example resources to surface (copy may be refined later):

- Emergency: 995
- Samaritans of Singapore (SOS): 1767
- Institute of Mental Health (IMH) Helpline: 6389 2222
- Clear note: this app is not emergency care

---

## 10. Definition of done

- [ ] CLI runs with no extra services beyond Python
- [ ] User can complete one full weekly cycle in one sitting
- [ ] Seeded circle of 4–5 peers is visible
- [ ] Support preference banner appears before replies
- [ ] At least two peer replies reflect the chosen preference
- [ ] Session persists to `session.json` and can resume mid-flow
- [ ] Summary prints check-in bars + experiment status
- [ ] No therapy / diagnosis / medication language in shipped prompts or templates
- [ ] Happy-path demo script below can be walked without crashes
- [ ] Build frozen by **25 August 2026**

---

## 11. Demo script (acceptance walkthrough)

1. Start CLI → Start this week's circle  
2. Enter display name; accept university stress topic  
3. Choose **Listening**  
4. See circle members  
5. Check-in scores + one sentence  
6. Answer guided reflection  
7. Post to circle  
8. See preference banner + listening-style peer replies  
9. Accept or skip experiment  
10. See Support Map summary → Done  

Optional resume check: quit mid check-in, relaunch, Resume, continue without data loss.

---

## 12. Next increments (after CLI MVP)

Ordered follow-ups — not part of this build:

1. Two local terminals / shared SQLite — real peer posts  
2. Rule-based facilitator that selects prompts via tools (still no open chat)  
3. Dedicated crisis screen + clearer escalation policy  
4. Bounded LLM + tool permissions + Safety Gateway  
5. Matching by topic + preferences  
6. Multi-week cycle + closure ritual  

---

## 13. Mapping back to product vision

| README concept | CLI MVP treatment |
|---|---|
| Core user journey (§2) | Full single-cycle walkthrough |
| Support preferences (§4) | Selection + reply banner + template routing |
| Response guardrails (§5) | Hardcoded templates only |
| Support Map (§6) | Printed summary at end |
| Behavioural experiment (§3.3) | One optional suggestion from `experiments.json` |
| Agentic AI (§8–14) | Deferred; stages reserved |
| Safety Gateway (§12) | Optional keyword stub only |
| Recommended MVP (§29) | Deliberately reduced to terminal slice |

> **Initial state principle:** Ship the weekly ritual and preference-shaped peer support. Everything else waits.
