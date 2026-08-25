"""Permitted tools for the bounded peer-support facilitator agent."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

import replies
import storage
from models import (
    CheckIn,
    ExperimentChoice,
    Post,
    Reflection,
    Reply,
    Session,
    User,
)

# OpenAI-style tool schemas (also used by mock agent docs)
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_topics",
            "description": (
                "List available support circle topics (university stress, burnout, "
                "loneliness, workplace stress, caregiving, grief, job loss, "
                "relationship difficulties). Call when the user has not chosen a topic."
            ),
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "join_topic",
            "description": (
                "Join a support circle for a topic id or natural-language topic name "
                "(e.g. burnout, grief, university_stress)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic id, title, or alias.",
                    }
                },
                "required": ["topic"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_session_context",
            "description": (
                "Get session stage, topic, preferences, and next_hint. "
                "Use sparingly — only if the user asks for status/progress, or you "
                "cannot tell what they want from their message. Do not call this on "
                "every turn, and never as a prelude to preference-only updates."
            ),
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_circle_members",
            "description": "List members of the current topic's support circle and their preference tags.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_support_preferences",
            "description": (
                "Set the user's support preferences (1-2). Keys: listening, "
                "shared_experience, practical_ideas, gentle_accountability, encouragement. "
                "All selected preferences are stored and used together for banners and peer replies. "
                "When the user only changes preferences, call THIS tool alone — do not also "
                "fetch prompts, peer replies, or experiments in the same turn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 2,
                    }
                },
                "required": ["preferences"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_check_in",
            "description": "Record a private check-in: energy/stress/connection (1-5) and a short note.",
            "parameters": {
                "type": "object",
                "properties": {
                    "energy": {"type": "integer", "minimum": 1, "maximum": 5},
                    "stress": {"type": "integer", "minimum": 1, "maximum": 5},
                    "connection": {"type": "integer", "minimum": 1, "maximum": 5},
                    "note": {"type": "string"},
                },
                "required": ["energy", "stress", "connection", "note"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weekly_prompt",
            "description": (
                "Retrieve an approved CBT-informed reflection prompt from the shared "
                "research-backed intervention library (noticing, thought-feeling, gentle "
                "reappraisal, self-compassion, behavioural activation). This is "
                "psychoeducation for peer-support facilitation — NOT clinical CBT therapy. "
                "Always use this for reflection prompts; do not invent worksheets. "
                "Omit focus/prompt_id to follow check-in routing or the library sequence. "
                "Set advance_sequence=true after a reflection to fetch the next prompt in sequence. "
                "Call only when the user asks for a prompt / reflection / next prompt — "
                "not after unrelated actions like setting preferences."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": (
                            "Optional focus: noticing, thought_feeling, reappraisal_lite, "
                            "behavioural_activation, self_compassion, values_action."
                        ),
                    },
                    "prompt_id": {
                        "type": "string",
                        "description": "Optional specific prompt id from the CBT-informed library.",
                    },
                    "advance_sequence": {
                        "type": "boolean",
                        "description": (
                            "If true, pick the next unused prompt in the library sequence "
                            "(situation → thought-feeling → reappraisal → BA)."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_reflection",
            "description": "Save the user's reflection answer for the current weekly prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "prompt_id": {"type": "string"},
                },
                "required": ["answer"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_peer_replies",
            "description": (
                "CLI DEMO ONLY: generate preference-aware peer-style reply suggestions from "
                "approved CBT-informed templates. These are NOT real human peer messages — "
                "names are demo stand-ins. Label them clearly to the user. Use after the user "
                "shares something with the circle."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "share_text": {
                        "type": "string",
                        "description": "What the user wants peers to respond to.",
                    },
                    "count": {"type": "integer", "minimum": 1, "maximum": 3},
                },
                "required": ["share_text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_experiment",
            "description": (
                "Suggest one optional CBT-informed / behavioural-activation-lite experiment "
                "from the approved research-backed library. Frame as optional, never as "
                "prescription, clinical homework, or therapy."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "Optional focus key matching library experiments.",
                    },
                    "experiment_id": {
                        "type": "string",
                        "description": "Optional specific experiment id.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_experiment_choice",
            "description": "Record whether the user accepted or skipped the suggested experiment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "experiment_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["accepted", "skipped"]},
                },
                "required": ["experiment_id", "status"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_experiment_review",
            "description": (
                "Plan–do–review lite: record a short note about how an previously accepted "
                "optional experiment went. Call when pending_experiment_review is set "
                "(e.g. on session resume). Not clinical homework grading."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": "Brief reflection on how the optional step went.",
                    },
                    "experiment_id": {
                        "type": "string",
                        "description": "Defaults to pending_experiment_review id.",
                    },
                },
                "required": ["note"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_approved_resource",
            "description": (
                "Retrieve approved resources (filtered by current topic when set). "
                "Never invent hotlines."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_support_map_summary",
            "description": "Build a Support Map lite summary from the current session.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]

# Tool result
@dataclass
class ToolResult:
    name: str
    arguments: dict[str, Any]
    output: Any

# Tool context
@dataclass
class ToolContext:
    session: Session
    traces: list[ToolResult] = field(default_factory=list)

    # Persist session
    def persist(self) -> None:
        storage.save_session(self.session)

# Bar function to display score as a bar
def _bar(score: int, width: int = 8) -> str:
    filled = max(0, min(width, int(round(score / 5 * width))))
    return "#" * filled + "-" * (width - filled)

# Ensure user
def _ensure_user(session: Session) -> User:
    if session.user is None:
        session.user = User(id="user-local", display_name="Friend", preferences=[])
    return session.user

# Route focus based on check-in scores
def route_focus_from_check_in(
    energy: int, stress: int, connection: int
) -> dict[str, str]:
    """Non-diagnostic focus hints from process check-in scores."""
    if stress >= 4:
        return {
            "prompt_focus": "noticing",
            "experiment_focus": "behavioural_activation",
            "reason": "Higher stress → start with situation noticing; prefer a tiny BA-lite step.",
        }
    if connection <= 2:
        return {
            "prompt_focus": "values_action",
            "experiment_focus": "values_action",
            "reason": "Lower connection → gentle values/connection focus (optional).",
        }
    if energy <= 2:
        return {
            "prompt_focus": "behavioural_activation",
            "experiment_focus": "behavioural_activation",
            "reason": "Lower energy → inch-sized activation prompts/experiments.",
        }
    return {
        "prompt_focus": "thought_feeling",
        "experiment_focus": "noticing",
        "reason": "Balanced check-in → thought–feeling noticing as default.",
    }

# Next ritual step based on session state
def next_ritual_step(session: Session) -> dict[str, str]:
    """Soft next-stage hint for live facilitator stickiness."""
    if session.pending_experiment_review:
        return {
            "next_stage": "EXPERIMENT_REVIEW",
            "hint": (
                f"Ask how optional experiment '{session.pending_experiment_review}' went, "
                "then call record_experiment_review."
            ),
        }
    if not session.topic:
        return {"next_stage": "JOIN_CIRCLE", "hint": "Call list_topics / join_topic."}
    user = session.user
    if not user or not user.preferences:
        return {
            "next_stage": "PREFERENCES",
            "hint": "When the user sets preferences, call set_support_preferences only.",
        }
    if session.check_in is None:
        return {
            "next_stage": "CHECK_IN",
            "hint": "When the user wants to check in, call record_check_in (energy/stress/connection 1–5).",
        }
    if not session.completed_prompt_ids and session.stage in (
        "CHECK_IN",
        "REFLECTION",
        "JOIN_CIRCLE",
        "PREFERENCES",
    ):
        focus = session.suggested_prompt_focus or "noticing"
        return {
            "next_stage": "REFLECTION",
            "hint": (
                f"When the user asks for a reflection prompt, call get_weekly_prompt "
                f"(suggested focus: {focus}). Do not auto-fetch a prompt after unrelated actions."
            ),
        }
    if session.reflection is None and session.prompt_id:
        return {
            "next_stage": "REFLECTION",
            "hint": "Invite a short reflection, then save_reflection.",
        }
    if session.post is None:
        return {
            "next_stage": "PEER_POST",
            "hint": (
                "When the user wants to share with the circle, call suggest_peer_replies "
                "(label as demo templates)."
            ),
        }
    if session.experiment is None:
        focus = session.suggested_experiment_focus or "behavioural_activation"
        return {
            "next_stage": "EXPERIMENT",
            "hint": (
                f"When the user asks for an experiment, call suggest_experiment "
                f"(suggested focus: {focus})."
            ),
        }
    if session.stage != "DONE":
        return {
            "next_stage": "SUMMARY",
            "hint": "Call get_support_map_summary to close the ritual.",
        }
    return {"next_stage": "DONE", "hint": "Session complete unless user starts again."}

# Next sequence prompt based on completed prompts
def _next_sequence_prompt(
    library: dict[str, Any], completed: list[str]
) -> dict[str, Any] | None:
    prompts = {p["id"]: p for p in library.get("prompts") or []}
    for pid in library.get("sequence") or []:
        if pid not in completed and pid in prompts:
            return prompts[pid]
    return None


# Tool belt
# 1. Register tool handlers - names and functions
# 2. execute(name, arguments) - execute a tool
# 3. Reject unknown tools
# 4. Update session and traces, and build banner/summary/replies
class ToolBelt:
    """Explicit least-privilege tool surface for the facilitator agent."""

    def __init__(self, ctx: ToolContext) -> None:
        self.ctx = ctx
        self._handlers: dict[str, Callable[..., Any]] = {
            "list_topics": self.list_topics,
            "join_topic": self.join_topic,
            "get_session_context": self.get_session_context,
            "get_circle_members": self.get_circle_members,
            "set_support_preferences": self.set_support_preferences,
            "record_check_in": self.record_check_in,
            "get_weekly_prompt": self.get_weekly_prompt,
            "save_reflection": self.save_reflection,
            "suggest_peer_replies": self.suggest_peer_replies,
            "suggest_experiment": self.suggest_experiment,
            "record_experiment_choice": self.record_experiment_choice,
            "record_experiment_review": self.record_experiment_review,
            "retrieve_approved_resource": self.retrieve_approved_resource,
            "get_support_map_summary": self.get_support_map_summary,
        }

    # Get tool names
    def names(self) -> list[str]:
        return list(self._handlers.keys())

    # Execute tool
    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        arguments = arguments or {}
        if name not in self._handlers:
            result = ToolResult(
                name=name,
                arguments=arguments,
                output={"error": f"Tool '{name}' is not permitted."},
            )
            self.ctx.traces.append(result)
            return result
        try:
            output = self._handlers[name](**arguments)
        except TypeError as exc:
            output = {"error": f"Invalid arguments: {exc}"}
        except Exception as exc:  # noqa: BLE001 - surface to agent
            output = {"error": str(exc)}
        result = ToolResult(name=name, arguments=arguments, output=output)
        self.ctx.traces.append(result)
        return result

    # Get topic id
    def _topic_id(self) -> str | None:
        return self.ctx.session.topic

    # List topics
    def list_topics(self) -> dict[str, Any]:
        topics = storage.load_topics()
        return {
            "topics": [
                {
                    "id": t.id,
                    "title": t.title,
                    "summary": t.summary,
                    "aliases": t.aliases,
                }
                for t in topics
            ],
            "hint": "Ask the user to pick one, then call join_topic.",
        }

    # Join topic
    def join_topic(self, topic: str) -> dict[str, Any]:
        info = storage.resolve_topic_id(topic)
        if info is None:
            available = [t.id for t in storage.load_topics()]
            return {"error": f"Unknown topic '{topic}'", "available": available}
        circle = storage.load_circle(info.id)
        prompts = storage.load_prompts(info.id)
        self.ctx.session.topic = info.id
        self.ctx.session.circle_id = circle.id
        self.ctx.session.prompt_id = prompts.prompts[0].id if prompts.prompts else None
        if self.ctx.session.stage in ("ONBOARD", "PREFERENCES", "JOIN_CIRCLE"):
            self.ctx.session.stage = "JOIN_CIRCLE"
        self.ctx.persist()
        return {
            "topic": info.id,
            "title": info.title,
            "summary": info.summary,
            "circle_id": circle.id,
            "circle_title": circle.title,
            "member_count": len(circle.members),
            "framing": (
                "Topic selects your peer circle. Prompts and experiments come from the "
                "shared CBT-informed library — facilitation, not clinical CBT therapy."
            ),
            "session_path": (
                "preferences → check-in → CBT-informed prompt → reflection → "
                "peer replies → optional experiment → support map"
            ),
        }

    # Get session context
    def get_session_context(self) -> dict[str, Any]:
        s = self.ctx.session
        user = s.user
        ritual = next_ritual_step(s)
        return {
            "stage": s.stage,
            "topic": s.topic,
            "display_name": user.display_name if user else None,
            "preferences": user.preferences if user else [],
            "circle_id": s.circle_id,
            "prompt_id": s.prompt_id,
            "completed_prompt_ids": list(s.completed_prompt_ids),
            "suggested_prompt_focus": s.suggested_prompt_focus,
            "suggested_experiment_focus": s.suggested_experiment_focus,
            "has_check_in": s.check_in is not None,
            "has_reflection": s.reflection is not None,
            "has_post": s.post is not None,
            "reply_count": len(s.replies),
            "experiment": (
                {"id": s.experiment.id, "status": s.experiment.status}
                if s.experiment
                else None
            ),
            "pending_experiment_review": s.pending_experiment_review,
            "next_stage": ritual["next_stage"],
            "next_hint": ritual["hint"],
            "demo_note": (
                "Peer replies are demo templates only until real circles exist."
            ),
        }

    # Get circle members
    def get_circle_members(self) -> dict[str, Any]:
        circle = storage.load_circle(self._topic_id())
        self.ctx.session.circle_id = circle.id
        if self.ctx.session.stage in ("ONBOARD", "PREFERENCES"):
            self.ctx.session.stage = "JOIN_CIRCLE"
        self.ctx.persist()
        return {
            "id": circle.id,
            "title": circle.title,
            "topic": circle.topic,
            "members": [
                {
                    "display_name": m.display_name,
                    "preferences": m.preferences,
                    "persona_note": m.persona_note,
                }
                for m in circle.members
            ],
        }

    # Set support preferences
    def set_support_preferences(self, preferences: list[str]) -> dict[str, Any]:
        allowed = {
            "listening",
            "shared_experience",
            "practical_ideas",
            "gentle_accountability",
            "encouragement",
        }
        cleaned = [p for p in preferences if p in allowed][:2]
        if not cleaned:
            return {"error": "Provide 1-2 valid preference keys."}
        user = _ensure_user(self.ctx.session)
        user.preferences = cleaned
        self.ctx.session.stage = "CHECK_IN"
        self.ctx.persist()
        banner = replies.preference_banner(cleaned)
        library = storage.load_template_library()
        norms = library.get("preference_norms") or {}
        return {
            "preferences": cleaned,
            "banner": banner,
            "preference_norms": {p: norms.get(p) for p in cleaned if p in norms},
            "framing": library.get(
                "framing",
                "CBT-informed peer norms — not peer-delivered CBT therapy.",
            ),
        }

    # Record check-in
    def record_check_in(
        self, energy: int, stress: int, connection: int, note: str
    ) -> dict[str, Any]:
        for label, value in (
            ("energy", energy),
            ("stress", stress),
            ("connection", connection),
        ):
            if not isinstance(value, int) or value < 1 or value > 5:
                return {"error": f"{label} must be an integer 1-5"}
        self.ctx.session.check_in = CheckIn(
            energy=energy,
            stress=stress,
            connection=connection,
            note=note.strip(),
        )
        routing = route_focus_from_check_in(energy, stress, connection)
        self.ctx.session.suggested_prompt_focus = routing["prompt_focus"]
        self.ctx.session.suggested_experiment_focus = routing["experiment_focus"]
        self.ctx.session.stage = "REFLECTION"
        self.ctx.persist()
        return {
            "saved": True,
            "energy": energy,
            "stress": stress,
            "connection": connection,
            "note": note.strip(),
            "suggested_prompt_focus": routing["prompt_focus"],
            "suggested_experiment_focus": routing["experiment_focus"],
            "routing_reason": routing["reason"],
            "framing": (
                "Session monitoring (energy / stress / connection) — process check-in "
                "for facilitation, not a clinical assessment or diagnosis."
            ),
            "next_hint": (
                f"Next: get_weekly_prompt with focus '{routing['prompt_focus']}' "
                "(or omit focus to use this routing / sequence)."
            ),
        }

    # Get weekly prompt (CBT-informed shared library only)
    def get_weekly_prompt(
        self,
        focus: str | None = None,
        prompt_id: str | None = None,
        advance_sequence: bool = False,
    ) -> dict[str, Any]:
        library = storage.load_cbt_informed()
        prompts = list(library.get("prompts") or [])
        if not prompts:
            return {"error": "CBT-informed prompt library is empty."}
        by_id = {p["id"]: p for p in prompts}
        prompt = None
        selection = "default"

        if prompt_id:
            prompt = by_id.get(prompt_id)
            selection = "prompt_id"
        elif focus:
            focused = [p for p in prompts if p.get("focus") == focus]
            prompt = focused[0] if focused else None
            selection = "focus"
        elif advance_sequence:
            prompt = _next_sequence_prompt(
                library, self.ctx.session.completed_prompt_ids
            )
            selection = "advance_sequence"
        else:
            suggested = self.ctx.session.suggested_prompt_focus
            if suggested and not self.ctx.session.completed_prompt_ids:
                focused = [p for p in prompts if p.get("focus") == suggested]
                if focused:
                    prompt = focused[0]
                    selection = "check_in_routing"
            if prompt is None:
                prompt = _next_sequence_prompt(
                    library, self.ctx.session.completed_prompt_ids
                )
                selection = "sequence" if prompt else "default"
            if prompt is None:
                prompt = prompts[0]
                selection = "default"

        if prompt is None:
            return {"error": f"Unknown prompt selection ({selection})."}

        self.ctx.session.prompt_id = prompt["id"]
        self.ctx.session.stage = "REFLECTION"
        self.ctx.persist()
        next_prompt = _next_sequence_prompt(
            library,
            self.ctx.session.completed_prompt_ids
            + (
                [prompt["id"]]
                if prompt["id"] not in self.ctx.session.completed_prompt_ids
                else []
            ),
        )
        return {
            "id": prompt["id"],
            "focus": prompt.get("focus"),
            "text": prompt["text"],
            "rationale": prompt.get("rationale", ""),
            "framing": prompt.get("framing", "psychoeducation_not_treatment"),
            "library_framing": library.get("framing"),
            "circle_topic": self.ctx.session.topic,
            "informed_by_themes": prompt.get("informed_by_themes", []),
            "research_backing": library.get("research_backing", []),
            "source": "cbt_informed_approved_library",
            "available_foci": library.get("foci", []),
            "sequence": library.get("sequence", []),
            "selection": selection,
            "completed_prompt_ids": list(self.ctx.session.completed_prompt_ids),
            "next_in_sequence": (
                {"id": next_prompt["id"], "focus": next_prompt.get("focus")}
                if next_prompt
                else None
            ),
        }

    # Save reflection
    def save_reflection(self, answer: str, prompt_id: str | None = None) -> dict[str, Any]:
        pid = prompt_id or self.ctx.session.prompt_id
        if not pid:
            library = storage.load_cbt_informed()
            prompts = list(library.get("prompts") or [])
            if not prompts:
                return {"error": "CBT-informed prompt library is empty."}
            pid = prompts[0]["id"]
            self.ctx.session.prompt_id = pid
        self.ctx.session.reflection = Reflection(prompt_id=pid, answer=answer.strip())
        if pid not in self.ctx.session.completed_prompt_ids:
            self.ctx.session.completed_prompt_ids.append(pid)
        self.ctx.session.stage = "PEER_POST"
        self.ctx.persist()
        library = storage.load_cbt_informed()
        nxt = _next_sequence_prompt(library, self.ctx.session.completed_prompt_ids)
        return {
            "saved": True,
            "prompt_id": pid,
            "completed_prompt_ids": list(self.ctx.session.completed_prompt_ids),
            "next_in_sequence": (
                {
                    "id": nxt["id"],
                    "focus": nxt.get("focus"),
                    "hint": "Call get_weekly_prompt with advance_sequence=true for the next CBT-informed prompt.",
                }
                if nxt
                else None
            ),
            "framing": (
                "Reflection kept on the CBT-informed loop (prompt → notice → share). "
                "Not homework or therapy documentation."
            ),
            "next_hint": (
                "Optional: advance to the next prompt in sequence, or share with the circle "
                "for demo CBT-informed peer-style replies."
            ),
        }

    # Suggest peer replies
    def suggest_peer_replies(
        self, share_text: str, count: int = 2
    ) -> dict[str, Any]:
        user = _ensure_user(self.ctx.session)
        prefs = replies.normalize_preferences(user.preferences)
        banner = replies.preference_banner(prefs)
        library = storage.load_template_library()
        templates = storage.load_templates()
        hints = {str(k): str(v) for k, v in (library.get("hints") or {}).items()}
        norms = library.get("preference_norms") or {}
        circle = storage.load_circle(self._topic_id())
        peers = [m for m in circle.members if m.display_name]
        count = max(1, min(3, int(count), len(peers)))
        specs = replies.select_reply_specs(prefs, templates, count=count)

        self.ctx.session.post = Post(text=share_text.strip())
        generated: list[Reply] = []
        reply_meta: list[dict[str, str]] = []
        for i, (pref, template) in enumerate(specs):
            text = replies.render_template(
                template,
                summary=share_text,
                preference=pref,
                hints=hints,
            )
            peer_name = peers[i % len(peers)].display_name
            norm = norms.get(pref) or {}
            generated.append(Reply(from_=peer_name, text=text))
            reply_meta.append(
                {
                    "from": peer_name,
                    "preference": pref,
                    "label": replies.PREFERENCE_LABELS.get(pref, pref),
                    "cbt_move": str(norm.get("cbt_move", "")),
                    "text": text,
                }
            )

        self.ctx.session.replies = generated
        self.ctx.session.stage = "PEER_REPLIES"
        self.ctx.persist()
        return {
            "banner": banner,
            "preferences_used": prefs,
            "preference_norms": {p: norms.get(p) for p in prefs if p in norms},
            "topic": circle.topic,
            "replies": [r.to_dict() for r in generated],
            "replies_detail": reply_meta,
            "demo": True,
            "demo_label": (
                "DEMO ONLY — suggested peer-style replies from CBT-informed templates. "
                "Names are stand-ins, not real circle members."
            ),
            "framing": library.get(
                "framing",
                "CBT-informed peer replies — not peer-delivered CBT therapy.",
            ),
            "source": "cbt_informed_peer_templates",
            "note": (
                "Replies and banner reflect ALL selected support preferences via "
                "approved CBT-informed peer templates (round-robin). Not live humans."
            ),
        }

    # Suggest experiment (CBT-informed / BA-lite shared library only)
    def suggest_experiment(
        self, focus: str | None = None, experiment_id: str | None = None
    ) -> dict[str, Any]:
        library = storage.load_cbt_informed()
        experiments = list(library.get("experiments") or [])
        if not experiments:
            return {"error": "CBT-informed experiment library is empty."}
        experiment = None
        if experiment_id:
            experiment = next(
                (e for e in experiments if e.get("id") == experiment_id), None
            )
        if experiment is None and focus:
            focused = [e for e in experiments if e.get("focus") == focus]
            experiment = focused[0] if focused else None
        if experiment is None:
            suggested = self.ctx.session.suggested_experiment_focus
            if suggested:
                focused = [e for e in experiments if e.get("focus") == suggested]
                if focused:
                    experiment = focused[0]
        if experiment is None:
            check = self.ctx.session.check_in
            if check and check.stress >= 4:
                experiment = next(
                    (
                        e
                        for e in experiments
                        if e.get("id") == "cbt-ba-ten-minutes"
                    ),
                    experiments[0],
                )
            else:
                experiment = experiments[0]
        self.ctx.session.stage = "EXPERIMENT"
        self.ctx.persist()
        return {
            "id": experiment["id"],
            "focus": experiment.get("focus"),
            "text": experiment["text"],
            "rationale": experiment.get("rationale", ""),
            "framing": experiment.get(
                "framing", "optional_suggestion_not_prescription"
            ),
            "library_framing": library.get("framing"),
            "circle_topic": self.ctx.session.topic,
            "informed_by_themes": experiment.get("informed_by_themes", []),
            "research_backing": library.get("research_backing", []),
            "source": "cbt_informed_approved_library",
            "selection_note": (
                "Defaults may follow check-in routing (suggested_experiment_focus)."
            ),
        }

    # Record experiment choice
    def record_experiment_choice(
        self, experiment_id: str, status: str
    ) -> dict[str, Any]:
        if status not in ("accepted", "skipped"):
            return {"error": "status must be accepted or skipped"}
        self.ctx.session.experiment = ExperimentChoice(
            id=experiment_id, status=status  # type: ignore[arg-type]
        )
        if status == "accepted":
            self.ctx.session.pending_experiment_review = experiment_id
        else:
            self.ctx.session.pending_experiment_review = None
        self.ctx.session.stage = "SUMMARY"
        self.ctx.persist()
        return {
            "saved": True,
            "experiment_id": experiment_id,
            "status": status,
            "pending_experiment_review": self.ctx.session.pending_experiment_review,
            "framing": (
                "Plan–do–review lite: you chose to accept or skip an optional "
                "BA-style experiment — not clinical homework."
            ),
            "next_hint": (
                "Close with support map summary. If accepted, the next CLI open will "
                "nudge a short experiment review."
                if status == "accepted"
                else "You can close with a support-map recap whenever you're ready."
            ),
        }

    def record_experiment_review(
        self, note: str, experiment_id: str | None = None
    ) -> dict[str, Any]:
        eid = experiment_id or self.ctx.session.pending_experiment_review
        if not eid:
            return {
                "error": "No pending experiment review. Accept an experiment first.",
            }
        self.ctx.session.experiment_review_note = note.strip()
        self.ctx.session.pending_experiment_review = None
        if self.ctx.session.stage == "DONE":
            self.ctx.session.stage = "CHECK_IN"
        self.ctx.persist()
        return {
            "saved": True,
            "experiment_id": eid,
            "note": note.strip(),
            "framing": (
                "Plan–do–review lite complete — noticing how an optional step went, "
                "not grading homework or delivering therapy."
            ),
            "next_hint": "Continue the ritual (check-in / prompt) or ask for a support map.",
        }

    # Retrieve approved resource
    def retrieve_approved_resource(
        self, resource_id: str | None = None
    ) -> dict[str, Any]:
        resources = storage.load_resources(self._topic_id())
        if resource_id:
            match = next((r for r in resources if r.get("id") == resource_id), None)
            if not match:
                return {
                    "error": "Unknown resource_id",
                    "available_ids": [r["id"] for r in resources],
                }
            return {"resource": match, "source": "approved_resource_list"}
        return {
            "resources": resources,
            "topic_filter": self._topic_id(),
            "source": "approved_resource_list",
        }

    # Get support map summary
    def get_support_map_summary(self) -> dict[str, Any]:
        s = self.ctx.session
        check = s.check_in
        summary: dict[str, Any] = {
            "title": "My Support Map (this week)",
            "topic": s.topic,
            "stage": s.stage,
            "framing": (
                "CBT-informed session recap: what you noticed, peer support received, "
                "and any optional next inch — facilitation summary, not a clinical report."
            ),
        }
        if check:
            summary["bars"] = {
                "energy": _bar(check.energy),
                "stress": _bar(check.stress),
                "connection": _bar(check.connection),
            }
            summary["scores"] = {
                "energy": check.energy,
                "stress": check.stress,
                "connection": check.connection,
            }
            summary["noticed"] = [check.note]
            summary["check_in_note"] = (
                "Process monitoring only (not diagnosis): energy / stress / connection."
            )
        if s.prompt_id:
            summary["prompt_id"] = s.prompt_id
        if s.reflection:
            summary["reflection"] = s.reflection.answer
            summary["noticed_this_session"] = s.reflection.answer
        if s.experiment:
            summary["experiment"] = {
                "id": s.experiment.id,
                "status": s.experiment.status,
            }
            summary["optional_next_inch"] = (
                f"Experiment '{s.experiment.id}' was {s.experiment.status}."
            )
        if s.experiment_review_note:
            summary["experiment_review_note"] = s.experiment_review_note
        if s.pending_experiment_review:
            summary["pending_experiment_review"] = s.pending_experiment_review
            summary["review_hint"] = (
                "On next open, briefly review how that optional step went "
                "(record_experiment_review)."
            )
        elif s.stage in ("PEER_REPLIES", "EXPERIMENT", "SUMMARY") and not s.experiment:
            summary["optional_next_inch"] = (
                "No experiment recorded — that's fine; noticing and peer support still count."
            )
        if s.replies:
            summary["peer_replies_received"] = len(s.replies)
            summary["peer_support_note"] = (
                "DEMO: preference-matched CBT-informed template replies "
                "(not real human peers yet)."
            )
        summary["closing"] = (
            "You can return next session for another short ritual. "
            "This is peer-support facilitation, not therapy."
        )
        s.stage = "DONE"
        self.ctx.persist()
        return summary

# Format trace
def format_trace(result: ToolResult) -> str:
    payload = json.dumps(result.output, ensure_ascii=False, indent=2)
    args = json.dumps(result.arguments, ensure_ascii=False)
    return f"[tool] {result.name}({args})\n{payload}"
