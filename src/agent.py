"""Bounded facilitator agent with tool calling (OpenAI) and mock fallback."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from crisis import SafetyResult, assess_message
from models import Session
import storage
from tools import TOOL_SCHEMAS, ToolBelt, ToolContext, ToolResult, format_trace

# System prompt
SYSTEM_PROMPT = """
You are the Small Circles facilitator — a bounded peer-support guide for a
CLI demo. You help adults join a small circle around a life challenge topic.
You are NOT a therapist, psychologist, counsellor, doctor, or crisis service.

Facilitation is CBT-informed (structured noticing, gentle perspective-taking,
optional small actions) via ONE approved research-backed library only. Never
claim to deliver CBT therapy or treatment. Never invent prompts or experiments.

Available topics (via list_topics / join_topic): university stress, burnout,
loneliness, workplace stress, caregiving, grief, job loss, relationship
difficulties. Topics select the peer circle; prompts/experiments stay shared
CBT-informed content.

Turn discipline (critical):
- Handle ONE user intent per turn. Call only the tools needed for that intent.
- Do NOT advance the ritual unless the user clearly asks to continue (e.g. check-in,
  reflection prompt, next prompt, share, experiment, summary).
- Preference-only messages → call set_support_preferences only, confirm briefly,
  stop. Do not call get_session_context or get_weekly_prompt afterward.
- Do not call get_session_context by default. Use it only if the user asks for
  status/progress or you truly cannot infer the next step from their message.
- next_hint from context is guidance when the user wants to continue — not a
  command to auto-run the next stage on unrelated messages.
- If pending_experiment_review is set AND the user is reviewing / saying how an
  experiment went, call record_experiment_review first.

Ritual order (when the user is progressing, not for side requests):
topic → preferences → check-in → prompt → reflection → (optional next prompt) →
demo peer replies → experiment → support map.

Rules:
- Support, don't treat. Facilitate, don't diagnose. Connect, don't create dependency.
- Never diagnose, prescribe, or give medication advice.
- If no topic is selected and they want facilitation, call list_topics / join_topic.
- Reflection prompts: only when asked — get_weekly_prompt (optional focus / advance_sequence).
- After record_check_in, mention routing briefly; fetch a prompt only if they ask.
- Experiments: only when asked — suggest_experiment.
- Peer replies are DEMO ONLY (templates). Label them as not real humans.
- Only use approved library content via tools; never invent interventions or hotlines.
- Keep replies short, warm, and practical for a terminal UI.
- Honor ALL selected support preferences when explaining banners or peer replies.
- If asked "are you my therapist?" or similar, refuse that role; offer facilitation
  + approved resources instead.
""".strip()

# Agent turn
@dataclass
class AgentTurn:
    user_text: str
    safety: SafetyResult
    assistant_text: str
    traces: list[ToolResult] = field(default_factory=list)
    mode: str = "mock"  # mock | openai

# Get OpenAI API key
def _env_api_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("SMALL_CIRCLES_OPENAI_API_KEY")


def _debug_enabled() -> bool:
    return os.environ.get("OPENAI_DEBUG", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _debug_log(message: str) -> None:
    if _debug_enabled():
        print(f"[openai-debug] {message}")


def _try_load_dotenv() -> None:
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        return


def _format_openai_error(exc: BaseException) -> str:
    parts = [f"{type(exc).__name__}: {exc}"]
    status = getattr(exc, "status_code", None)
    if status is not None:
        parts.append(f"status={status}")
    body = getattr(exc, "body", None)
    if body is not None:
        try:
            parts.append(f"body={json.dumps(body, ensure_ascii=False)}")
        except TypeError:
            parts.append(f"body={body!r}")
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            parts.append(f"response_json={json.dumps(response.json(), ensure_ascii=False)}")
        except Exception:  # noqa: BLE001
            pass
    return " | ".join(parts)

# Facilitator agent
class FacilitatorAgent:
    def __init__(self, session: Session, *, force_mock: bool = False) -> None:
        _try_load_dotenv()
        self.session = session # Session object
        self.force_mock = force_mock # Force mock mode if API key is not set
        self.ctx = ToolContext(session=session) # Tool context
        self.tools = ToolBelt(self.ctx) # Tool belt
        self.history: list[dict[str, Any]] = [ # Chat history
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        key = _env_api_key() or ""
        _debug_log(
            f"agent init mode={self.mode} model={os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')!r} "
            f"key_prefix={(key[:8] + '...') if key else '(none)'} key_len={len(key)}"
        )

    # Get mode - mock or openai
    @property
    def mode(self) -> str:
        if self.force_mock or not _env_api_key():
            return "mock"
        return "openai"

    # Handle user text
    def handle(self, user_text: str) -> AgentTurn:
        self.ctx.traces = []
        safety = assess_message(user_text)
        # If user text is not safe, return safety message
        if not safety.allow_facilitator_tools:
            text = safety.message or "I need to stop normal facilitation here."
            return AgentTurn(
                user_text=user_text,
                safety=safety,
                assistant_text=text,
                traces=[],
                mode=self.mode,
            )

        if self.mode == "openai":
            return self._handle_openai(user_text, safety)
        return self._handle_mock(user_text, safety)

    # Handle mock mode
    def _handle_mock(self, user_text: str, safety: SafetyResult) -> AgentTurn:
        text = user_text.lower().strip()
        parts: list[str] = []

        # Plan–do–review lite on resume
        if self.session.pending_experiment_review and any(
            k in text
            for k in (
                "review",
                "how it went",
                "how did it go",
                "went well",
                "didn't try",
                "did not try",
                "experiment went",
            )
        ):
            rev = self.tools.execute(
                "record_experiment_review", {"note": user_text}
            ).output
            if rev.get("error"):
                parts.append(rev["error"])
            else:
                parts.append(
                    f"Thanks — noted your experiment review for {rev.get('experiment_id')}."
                )
                parts.append(rev.get("framing", ""))

        # Topic selection
        if any(k in text for k in ("list topics", "what topics", "available topics", "/topics")):
            listed = self.tools.execute("list_topics", {}).output
            parts.append("Available topics:")
            for t in listed.get("topics", []):
                parts.append(f"- {t['id']}: {t['title']} — {t['summary']}")

        # Join topic
        join_match = re.search(
            r"^(?:join|switch\s+to|topic(?:\s+is)?)\s+(.+)$", text
        )
        
        if join_match or (not self.session.topic and storage.resolve_topic_id(user_text)):
            query = join_match.group(1).strip() if join_match else user_text
            query = re.sub(r"\b(please|circle|topic)\b", "", query).strip()
            joined = self.tools.execute("join_topic", {"topic": query}).output
            if joined.get("error"):
                parts.append(joined["error"])
                if joined.get("available"):
                    parts.append("Try one of: " + ", ".join(joined["available"]))
            else:
                parts.append(
                    f"Joined {joined.get('circle_title')} ({joined.get('topic')}). "
                    f"{joined.get('member_count')} peers are in this circle."
                )

        # If no topic is selected, list topics and help user join a topic
        if not self.session.topic and not parts:
            listed = self.tools.execute("list_topics", {}).output
            parts.append(
                "Pick a support topic first (e.g. 'join burnout' or 'join grief')."
            )
            for t in listed.get("topics", []):
                parts.append(f"- {t['id']}: {t['title']}")
            return AgentTurn(
                user_text=user_text,
                safety=safety,
                assistant_text="\n".join(parts),
                traces=list(self.ctx.traces),
                mode="mock",
            )

        # Role boundary: not a therapist
        if any(
            k in text
            for k in (
                "are you my therapist",
                "be my therapist",
                "my cbt therapist",
                "you are my therapist",
                "act as my therapist",
            )
        ):
            parts.append(
                "No — I'm a bounded peer-support facilitator, not a therapist or "
                "CBT clinician. I can guide weekly circle rituals and retrieve "
                "approved CBT-informed prompts/experiments, but I don't provide therapy."
            )
            res = self.tools.execute("retrieve_approved_resource", {}).output
            if res.get("resources"):
                parts.append("If you want clinical care, start with approved resources:")
                for r in res["resources"][:3]:
                    parts.append(f"- {r['title']}: {r['summary']}")

        # Heuristic tool plan so the demo is visibly agentic without an API key
        if any(k in text for k in ("prefer", "listening", "advice", "accountability")):
            prefs = []
            if "listen" in text:
                prefs.append("listening")
            if "practical" in text or "idea" in text:
                prefs.append("practical_ideas")
            if "account" in text:
                prefs.append("gentle_accountability")
            if "encourag" in text:
                prefs.append("encouragement")
            if "share" in text or "similar" in text:
                prefs.append("shared_experience")
            if not prefs:
                prefs = ["listening"]
            result = self.tools.execute(
                "set_support_preferences", {"preferences": prefs[:2]}
            )
            parts.append(
                f"I've set your support preference to: {', '.join(result.output.get('preferences', prefs))}."
            )
            parts.append(result.output.get("banner", {}).get("message", ""))

        # Check in
        if re.search(r"\b(energy|stress|connection)\b", text) or "check in" in text or "check-in" in text:
            energy = _extract_score(text, "energy", default=3)
            stress = _extract_score(text, "stress", default=3)
            connection = _extract_score(text, "connection", default=3)
            note = user_text.strip()
            check = self.tools.execute(
                "record_check_in",
                {
                    "energy": energy,
                    "stress": stress,
                    "connection": connection,
                    "note": note,
                },
            ).output
            parts.append(
                f"Check-in saved (energy {energy}, stress {stress}, connection {connection})."
            )
            if check.get("routing_reason"):
                parts.append(
                    f"Routing hint: {check['routing_reason']} "
                    f"(prompt focus: {check.get('suggested_prompt_focus')})."
                )

        # Reflection: single CBT-informed library path
        advance = any(
            k in text
            for k in ("next prompt", "another prompt", "advance", "next reflection")
        )
        prompt_intent = advance or any(
            k in text
            for k in (
                "prompt",
                "reflect",
                "reflection",
                "guided",
                "cbt",
                "noticing",
                "thought-feeling",
                "thought feeling",
                "thoughts and feelings",
                "reappraisal",
                "structured noticing",
                "energy this week",
            )
        ) or (self.session.stage == "REFLECTION" and "check" not in text)

        if prompt_intent:
            args: dict[str, Any] = {}
            if advance:
                args["advance_sequence"] = True
            elif "thought" in text and "feel" in text:
                args["focus"] = "thought_feeling"
            elif "notic" in text:
                args["focus"] = "noticing"
            elif "reappraisal" in text or "balanced" in text:
                args["focus"] = "reappraisal_lite"
            elif "compassion" in text or "friend" in text:
                args["focus"] = "self_compassion"
            elif "activation" in text or "inch" in text:
                args["focus"] = "behavioural_activation"
            if (
                advance
                or "prompt" in text
                or "reflect" in text
                or "cbt" in text
                or "notic" in text
                or "thought" in text
                or "reappraisal" in text
                or self.session.prompt_id is None
            ):
                prompt = self.tools.execute("get_weekly_prompt", args).output
                if prompt.get("error"):
                    parts.append(prompt["error"])
                else:
                    parts.append(
                        "CBT-informed prompt (research-backed library — not therapy):\n"
                        f"({prompt.get('id')} / {prompt.get('focus')}):\n"
                        f"\"{prompt.get('text')}\"\n"
                        f"Framing: {prompt.get('framing')}"
                    )
                    if prompt.get("next_in_sequence"):
                        nxt = prompt["next_in_sequence"]
                        parts.append(
                            f"Next in sequence when you're ready: {nxt.get('id')} "
                            f"({nxt.get('focus')}) — say 'next prompt'."
                        )
            if (
                len(user_text.split()) > 6
                and "prefer" not in text
                and "join" not in text
                and "prompt" not in text
                and not advance
            ):
                saved = self.tools.execute("save_reflection", {"answer": user_text}).output
                parts.append("I've saved that as your reflection.")
                if saved.get("next_in_sequence"):
                    parts.append(
                        "You can say 'next prompt' for the following CBT-informed step, "
                        "or share with the circle."
                    )

        # Circle members
        if any(
            k in text
            for k in ("circle", "members", "who is", "peers")
        ) and "join" not in text:
            members = self.tools.execute("get_circle_members", {}).output
            if members.get("error"):
                parts.append(members["error"])
            else:
                names = ", ".join(m["display_name"] for m in members.get("members", []))
                parts.append(
                    f"Demo circle '{members.get('title')}' stand-ins: {names}. "
                    "(Not real humans yet.)"
                )

        # Share intent
        share_intent = any(
            k in text
            for k in ("share", "tell the circle", "peer", "post", "feeling wiped", "feeling")
        )
        if share_intent and len(user_text.split()) > 4 and "prefer" not in text:
            peer = self.tools.execute(
                "suggest_peer_replies", {"share_text": user_text, "count": 2}
            ).output
            if peer.get("error"):
                parts.append(peer["error"])
            else:
                parts.append(peer.get("demo_label", "DEMO peer-style template replies:"))
                banner = peer.get("banner", {})
                parts.append(
                    f"Support preference banner: {banner.get('label')} — {banner.get('message')}"
                )
                for reply in peer.get("replies", []):
                    parts.append(f"- {reply['from']} (demo): {reply['text']}")

        # Experiment: single CBT-informed / BA-lite path
        if any(
            k in text
            for k in (
                "experiment",
                "small step",
                "try this week",
                "action",
                "behavioural activation",
                "behavioral activation",
                "ba-lite",
                "ba lite",
            )
        ) and "review" not in text and "how did" not in text and "how it went" not in text:
            exp_args: dict[str, Any] = {}
            if "activation" in text or "ba" in text:
                exp_args["focus"] = "behavioural_activation"
            elif "notic" in text or "thought" in text:
                exp_args["focus"] = "noticing"
            elif "compassion" in text or "kind" in text:
                exp_args["focus"] = "self_compassion"
            exp = self.tools.execute("suggest_experiment", exp_args).output
            if exp.get("error"):
                parts.append(exp["error"])
            else:
                parts.append(
                    f"Optional CBT-informed experiment ({exp.get('id')}): {exp.get('text')}\n"
                    f"Framing: {exp.get('framing')} — not clinical homework.\n"
                    "Say 'accept experiment <id>' or 'skip experiment <id>' if you want to record a choice."
                )
        # Accept or skip experiment
        accept = re.search(r"accept(?: experiment)?\s+(\S+)", text)
        skip = re.search(r"skip(?: experiment)?\s+(\S+)", text)
        if accept:
            self.tools.execute(
                "record_experiment_choice",
                {"experiment_id": accept.group(1), "status": "accepted"},
            )
            parts.append("Recorded: you accepted the experiment.")
        elif skip:
            self.tools.execute(
                "record_experiment_choice",
                {"experiment_id": skip.group(1), "status": "skipped"},
            )
            parts.append("Recorded: you skipped the experiment.")

        # Resources
        if any(k in text for k in ("resource", "helpline", "hotline", "help line")):
            res = self.tools.execute("retrieve_approved_resource", {}).output
            parts.append("Approved resources:")
            for r in res.get("resources", [])[:4]:
                parts.append(f"- {r['title']}: {r['summary']}")

        # Support map summary
        if any(k in text for k in ("summary", "support map", "done", "finish")):
            summary = self.tools.execute("get_support_map_summary", {}).output
            parts.append(summary.get("title", "Support Map"))
            if summary.get("topic"):
                parts.append(f"  Topic: {summary['topic']}")
            bars = summary.get("bars") or {}
            for key in ("energy", "stress", "connection"):
                if key in bars:
                    parts.append(f"  {key.title():<12} {bars[key]}")
            if summary.get("experiment"):
                parts.append(f"Experiment: {summary['experiment']}")

        # Always orient if nothing matched - no tool calls
        if not self.ctx.traces:
            ctx = self.tools.execute("get_session_context", {}).output
            parts.append(
                "I'm your bounded facilitator (mock tool-calling mode). "
                f"Topic: {ctx.get('topic') or '(none)'}. Stage: {ctx.get('stage')}. "
                "Try: join burnout; I prefer listening; check-in energy 2 stress 4 connection 2 …; "
                "give me a reflection prompt; share with the circle that …; "
                "suggest an experiment; show resources; support map summary."
            )

        # If no parts, return default message
        if not parts:
            parts.append(
                "Thanks for sharing. I can help you join a topic circle, set preferences, "
                "check in, reflect, get preference-aware peer replies, or try an optional experiment."
            )

        # Return agent turn
        return AgentTurn(
            user_text=user_text,
            safety=safety,
            assistant_text="\n\n".join(p for p in parts if p),
            traces=list(self.ctx.traces),
            mode="mock",
        )

    # Handle openai mode
    def _handle_openai(self, user_text: str, safety: SafetyResult) -> AgentTurn:
        from openai import OpenAI

        client = OpenAI(api_key=_env_api_key()) # OpenAI client
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini") # OpenAI model
        key = _env_api_key() or ""
        self.history.append({"role": "user", "content": user_text})

        for step in range(6): # Max 6 tool-call rounds
            _debug_log(
                f"create step={step + 1}/6 model={model!r} "
                f"key_prefix={(key[:8] + '...') if key else '(none)'} "
                f"msgs={len(self.history)} user_chars={len(user_text)}"
            )
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=self.history,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
            except Exception as exc:  # noqa: BLE001 - surface API failures to the CLI
                detail = _format_openai_error(exc)
                _debug_log(f"CREATE FAILED step={step + 1}: {detail}")
                return AgentTurn(
                    user_text=user_text,
                    safety=safety,
                    assistant_text=(
                        "OpenAI request failed — the session is still running.\n"
                        f"model={model!r}\n"
                        f"{detail}\n\n"
                        "Hints: confirm this API key's project can call that model; "
                        "try OPENAI_DEBUG=1; or /reset and retry. "
                        "Set OPENAI_DEBUG=0 to hide debug lines."
                    ),
                    traces=list(self.ctx.traces),
                    mode="openai",
                )

            message = response.choices[0].message
            tool_calls = message.tool_calls or []
            _debug_log(
                f"create ok step={step + 1} tool_calls={len(tool_calls)} "
                f"has_content={bool((message.content or '').strip())}"
            )

            # If no tool calls, return assistant message
            if not tool_calls:
                content = (message.content or "").strip()
                self.history.append({"role": "assistant", "content": content})
                return AgentTurn(
                    user_text=user_text,
                    safety=safety,
                    assistant_text=content
                    or "(No response text — try asking for a prompt or peer replies.)",
                    traces=list(self.ctx.traces),
                    mode="openai",
                )

            # Add tool calls to history
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
            self.history.append(assistant_msg)

            # Execute tool calls
            for tc in tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                _debug_log(f"tool execute {name}({json.dumps(args, ensure_ascii=False)})")
                result = self.tools.execute(name, args)
                self.history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result.output, ensure_ascii=False),
                    }
                )

        # If no tool calls, return default message
        return AgentTurn(
            user_text=user_text,
            safety=safety,
            assistant_text=(
                "I hit the tool-call step limit. Try a simpler request, "
                "or run with --mock to use the deterministic facilitator."
            ),
            traces=list(self.ctx.traces),
            mode="openai",
        )

# Extract score from user text
def _extract_score(text: str, label: str, default: int = 3) -> int:
    match = re.search(rf"{label}\s*[:=]?\s*([1-5])", text)
    if match:
        return int(match.group(1))
    return default

# Print turn
def print_turn(turn: AgentTurn, *, show_traces: bool = True) -> None:
    if show_traces and turn.traces:
        print("\n--- tool trace ---")
        for tr in turn.traces:
            print(format_trace(tr))
        print("--- end tools ---\n")
    print(f"Facilitator ({turn.mode}):\n{turn.assistant_text}\n")
