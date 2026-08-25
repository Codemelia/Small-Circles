# CBT-informed research notes (Small Circles)

**Who this is for:** designers and builders deciding *why* prompts and peer norms look the way they do.

Screening completed against OpenAlex results (`data/research/openalex_results.csv`, min year **2015** / last ~10 years).  
Decisions are abstract/title-level for product design—not a formal systematic review.

**How this connects to the demo:** the CLI facilitator only serves reflection prompts and experiments from [`data/interventions/cbt_informed.json`](../data/interventions/cbt_informed.json). See the plain-language architecture in [`docs/agentic-cli-demo.md`](agentic-cli-demo.md).

**Do not** paste copyrighted full texts or clinical worksheets into the agent library.  
Translate findings into **original** prompts / experiments / facilitation rules.

## Search + screening summary

| Decision | Count |
|---|---|
| `include` | 49 |
| `maybe` | 24 |
| `exclude` | 42 |
| **Total** | **115** |

Query buckets covered: `cbt_mhealth`, `peer_support_digital`, `cbt_group_online`, `behavioural_activation_app`, `facilitation_peer_mental`.

Re-run search:

```powershell
python scripts/lit_search_openalex.py --mailto you@example.com
```

Then re-apply or redo screening (a new search overwrites CSV screening columns).

## How screening was judged

**Include** if useful for Small Circles: digital/mHealth CBT or CBT-informed self-help, peer support/forums/moderation, engagement/adherence, university/young-adult relevance, AI-as-adjunct with human/social support, privacy, or intervention-reporting methods.

**Exclude** if minors-focused, false positives (e.g. osteoporosis), pure clinical specialty protocols, broad COVID/policy commissions, or off-topic mHealth (meds, sports, marketing).

**Maybe** if useful background (ICBT ≡ F2F efficacy, epidemiology) but weak for circle/facilitator design.

## Design principles log

Derived from `include` rows (rewritten for Small Circles).

### Facilitation role

- Position the agent as a **bounded facilitator / coach adjunct**, not a therapist (human support improves DMHI adherence; blended iCBT guidance literature).
- Prefer **tool-retrieved, approved content** over open-ended “therapy chat” (maps to human-centered AI for iCBT: preserve supporter agency; avoid over-reliance on model output).
- Moderators/facilitators in online peer communities should **encourage peer-to-peer support**, not replace it.
- Directional vs nondirectional peer support online maps cleanly to Small Circles **support preferences** (listening vs ideas vs encouragement).

### Group / circle structure

- Small, structured peer contexts beat unstructured social feeds (peer support network mechanisms; forum realist syntheses).
- Crowdsourced / peer cognitive-reappraisal platforms show value in combining **peer presence + structured skill prompts**.
- Define peer roles and outcomes clearly (peer-work reporting literature).
- Avoid engagement-maximising infinite feeds; prefer time-bounded weekly rituals (aligns with product philosophy and single-session / guided self-help patterns).

### CBT-informed moves that fit “support, don’t treat”

- Use **CBT-informed** language (not “we deliver CBT therapy”)—matches narrative reviews distinguishing CBT-informed support from full clinical CBT.
- Map app/library features to **basic CBT elements** carefully (many apps claim CBT without implementing it).
- Useful non-clinical moves for the library:
  - Noticing situation / thoughts / feelings / body cues
  - Gentle cognitive reappraisal prompts (optional, peer-framed—not “correcting” the user)
  - **Behavioural activation lite**: one small, optional action
  - Short guided self-help sequences (single-session / weekly check-in style)
- Personalization should be explicit (what is personalized: topic, preferences, experiment)—not opaque model improvisation.

### Small actions (behavioural activation lite)

- BA/CBT depression app literature and MoodHacker-style programs support **small self-manage actions** plus light guidance.
- Chatbot + BA skill studies are the closest analog to a **tool-using facilitator** suggesting optional experiments.
- Keep effect-size expectations modest (app MH meta-analyses show small effects); experiments are optional, not prescriptions.
- Adherence improves with brevity, perceived usefulness, and light prompts—not long unstructured homework.

### Safety / boundaries

- Digital MH can help and also relate to self-harm risk online—retain **crisis keyword stop + local resources**.
- Online peer forums help in some contexts and harm in others (realist synthesis)—need norms, preference banners, and escalation paths.
- Privacy/security of mHealth apps is a first-class requirement (PDPA / data minimisation already in product vision).
- Marketing claims often overreach—never advertise Small Circles as CBT therapy or clinical treatment.
- Generative AI in digital MH is evolving (2025 reviews): useful only with implementation discipline and evaluation.

### Engagement & product quality

- Real-world MH app engagement is often low—optimize for **short CLI/session completion**, not daily streak theatre.
- Barriers/facilitators reviews: reduce friction, clarify value, support continuity across stages.
- Person-based / user-centered development: design from user perspectives before adding features.
- Document intervention development (GUIDED-style): every prompt/experiment should have id + rationale.
- Evaluate library content for CBT-element fidelity, usability, and claimed outcomes (commercial app evaluation methods).

### Cultural / local fit

- Cultural adaptation of internet/mobile interventions matters for non-Western settings—keep Singapore resources and culturally careful copy.
- University-student digital CBT/anxiety and college guided self-help metas support targeting young adults under stress (without claiming clinical treatment).

### What we will NOT build into the agent

- Open-ended AI CBT **therapy** chat or “I am your CBT therapist”
- Diagnosis or labelling “cognitive distortions” as clinical fact
- Copied copyrighted worksheets or scraped full-text protocols
- Engagement leaderboards / addictive social feeds
- Surveillance NLP on users’ social media
- Minors-focused pathways in the MVP
- Replacing human peer support with the model

## Library drafting checklist

- [x] Shared CBT-informed prompt library ([`data/interventions/cbt_informed.json`](../data/interventions/cbt_informed.json))
- [x] Matching behavioural-activation-lite experiments
- [x] Single path: `get_weekly_prompt` / `suggest_experiment` → CBT library only
- [x] `research_backing` + `informed_by_themes` linking to screened OpenAlex includes
- [x] Eval cases: [`scripts/eval_cbt_informed.py`](../scripts/eval_cbt_informed.py)
- [x] Peer replies: [`data/templates.json`](../data/templates.json) + [`src/replies.py`](../src/replies.py)
- [x] CLI ritual deepen (see [agentic-cli-demo.md](agentic-cli-demo.md))

## End-to-end session checklist (CBT-informed circle)

Goal: every stage of a support-circle session is justified by CBT-informed + digital peer-support literature — **not** that peers deliver clinical CBT.

| Stage | Research intent | Status |
|---|---|---|
| Onboard / join topic | Structured peer context + guided self-help fit; non-clinical framing | Done (join framing + session_path) |
| Support preferences | Directional vs nondirectional peer support → preference norms | Done (CBT-aligned banners + norms) |
| Check-in | Brief process monitoring; routes focus without diagnosing | Done (`suggested_*_focus`) |
| Weekly prompt | Sequence: situation → thought/feeling → reappraisal → BA | Done (`sequence` / `advance_sequence`) |
| Reflection save | Keep user in CBT loop; unlock next sequence step | Done |
| Peer share + replies | Demo CBT-informed templates (not live humans) | Done (`demo` / `demo_label`) |
| Experiment | BA-lite optional action; may follow check-in routing | Done |
| Accept / skip + review | Plan–do–review lite on resume | Done (`pending_experiment_review`) |
| Support map / close | Recap noticed → demo peers → optional next inch | Done |
| Safety / resources | Crisis stop; overclaim caution; approved helplines | Done |

## High-signal includes (starter reading list)

Prioritize these when writing library copy:

1. Human support for DMHIs (adherence) — facilitator necessity  
2. Moderators encouraging peer-to-peer support online  
3. Directional vs nondirectional forum support — preference model  
4. Crowdsourced peer cognitive reappraisal platform  
5. CBT/BA apps reviews + CBT implementation in e-mental health apps  
6. Person-based / user-centered digital intervention development  
7. College/university digital MH and guided self-help metas  
8. MH app engagement reality + adherence factors  
9. AI-assisted social therapy / human-centered AI for iCBT supporters  
10. mHealth privacy/security + app-store claim caution  

### Deepened takeaways used for the library (step 1)

| Theme | Product implication |
|---|---|
| Human support ↑ adherence | Keep a facilitator agent that *guides stages* and retrieves library items |
| Moderators enable peer-to-peer | Agent should push toward circle sharing + preference-aware replies, not monologue therapy |
| Directional vs nondirectional support | Dual preferences + combined banners already match forum evidence |
| Peer + structured reappraisal | CBT-informed prompts can sit beside peer replies without replacing peers |
| Many apps claim CBT loosely | Every prompt needs `id` + `rationale` + explicit non-therapy framing |
| Low real-world engagement | Short prompts and optional inch-sized experiments only |
| GenAI / HCI caution | Tools + approved library; refuse therapist identity |
| Privacy / overclaim risk | No diagnosis; no “we deliver CBT”; Singapore resources stay approved-list only |

Full decisions live in the CSV `screen_decision` / `design_notes` columns.

## Citation hygiene

Keep DOI / OpenAlex ID in the CSV for write-ups.  
In product docs, say **“informed by CBT principles and digital peer-support literature,”** not **“this app delivers CBT.”**
