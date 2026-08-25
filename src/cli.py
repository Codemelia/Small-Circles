"""Agentic CLI demo for Small Circles."""

from __future__ import annotations

import argparse
import sys

import storage
from agent import FacilitatorAgent, print_turn
from models import Session, User

# Preference help
PREFERENCE_HELP = """
Support preferences (pick with natural language, e.g. "I prefer listening"):
  listening | shared_experience | practical_ideas |
  gentle_accountability | encouragement
""".strip()

# Print topics
def _print_topics() -> None:
    print("Available topics:")
    for t in storage.load_topics():
        print(f"  {t.id:<28} {t.title} — {t.summary}")

# Prompt topic
def _prompt_topic() -> str | None:
    _print_topics()
    print()
    raw = input("Topic id (or blank to choose later in chat): ").strip()
    if not raw:
        return None
    info = storage.resolve_topic_id(raw)
    if info is None:
        print(f"Unknown topic '{raw}'. You can join one later with: join burnout")
        return None
    return info.id

# Ensure session
def _ensure_session(
    display_name: str | None = None,
    topic: str | None = None,
) -> Session:
    session = storage.load_session()

    if session is None or not session.is_resumable:
        resolved = None
        if topic:
            info = storage.resolve_topic_id(topic)
            if info is None:
                raise SystemExit(
                    f"Unknown topic '{topic}'. Run with no --topic to see options."
                )
            resolved = info.id

        session = storage.create_session(
            display_name=display_name or "Friend",
            topic=resolved,
        )
        if resolved:
            circle = storage.load_circle(resolved)
            prompts = storage.load_prompts(resolved)
            session.circle_id = circle.id
            session.prompt_id = prompts.prompts[0].id if prompts.prompts else None
            session.stage = "PREFERENCES"
        else:
            session.stage = "ONBOARD"

        if session.user is None:
            session.user = User(
                id="user-local",
                display_name=display_name or "Friend",
                preferences=[],
            )
        elif display_name:
            session.user.display_name = display_name
        storage.save_session(session)
        return session

    if display_name and session.user:
        session.user.display_name = display_name
        storage.save_session(session)

    if topic and not session.topic:
        info = storage.resolve_topic_id(topic)
        if info:
            circle = storage.load_circle(info.id)
            prompts = storage.load_prompts(info.id)
            session.topic = info.id
            session.circle_id = circle.id
            session.prompt_id = prompts.prompts[0].id if prompts.prompts else None
            if session.stage == "ONBOARD":
                session.stage = "PREFERENCES"
            storage.save_session(session)

    return session

# Print banner
def _print_banner(mode: str) -> None:
    print("Small Circles — Agentic CLI Demo")
    print("-" * 36)
    print("Bounded peer-support facilitator with explicit tools.")
    print("CBT-informed facilitation + demo peer templates.")
    print("Not therapy. Not diagnosis. Not emergency care. Peers are not live humans yet.")
    print(f"Agent mode: {mode}")
    print()
    print("Commands: /help  /topics  /status  /tools  /reset  /quit")
    print(PREFERENCE_HELP)
    print()

# Print resume hints - for optional experiment review
def _print_resume_hints(session: Session) -> None:
    if session.pending_experiment_review:
        eid = session.pending_experiment_review
        print(
            f"Pending experiment review: '{eid}'. "
            "Say how that optional step went (plan–do–review lite), e.g.\n"
            "  The experiment went okay — I did about 10 minutes.\n"
        )

# Main function
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Small Circles agentic CLI demo")
    
    # Force mock tool-calling agent (no OpenAI key required)
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force mock tool-calling agent (no OpenAI key required)",
    )
    
    # Display name for this session
    parser.add_argument(
        "--name",
        default=None,
        help="Display name for this session",
    )
    
    # Topic id to join (e.g. burnout, grief, university_stress)
    parser.add_argument(
        "--topic",
        default=None,
        help="Topic id to join (e.g. burnout, grief, university_stress)",
    )
    
    # Hide tool traces
    parser.add_argument(
        "--no-traces",
        action="store_true",
        help="Hide tool traces",
    )
    
    # Parse arguments
    args = parser.parse_args(argv)

    topic = args.topic
    
    # Interactive pick only for brand-new / done sessions without a topic flag
    if topic is None and (storage.load_session() is None or not (
        (s := storage.load_session()) and s.is_resumable and s.topic
    )):
        existing = storage.load_session()
        if existing is None or not existing.is_resumable:
            try:
                topic = _prompt_topic()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                return 0

    try:
        session = _ensure_session(args.name, topic)
    except SystemExit as exc:
        print(exc)
        return 2

    # Create agent
    agent = FacilitatorAgent(session, force_mock=args.mock)
    _print_banner(agent.mode)
    _print_resume_hints(session)

    if session.user:
        prefs = ", ".join(session.user.preferences) or "(not set)"
        topic_label = session.topic or "(pick with: join burnout)"
        print(
            f"Hello, {session.user.display_name}. "
            f"Topic: {topic_label}. Stage: {session.stage}. Prefs: {prefs}"
        )
        print()

    show_traces = not args.no_traces

    while True:
        try:
            user_text = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if not user_text:
            continue

        lowered = user_text.lower()

        if lowered in {"/quit", "/exit", "quit", "exit"}:
            print("Bye.")
            return 0

        if lowered == "/help":
            print(PREFERENCE_HELP)
            print(
                "Try: join burnout\n"
                "     I prefer listening\n"
                "     check-in energy 2 stress 4 connection 2 deadlines are heavy\n"
                "     give me a reflection prompt\n"
                "     next prompt\n"
                "     share with the circle: I feel wiped this week\n"
                "     suggest an experiment\n"
                "     accept experiment cbt-ba-ten-minutes\n"
                "     show resources\n"
                "     support map summary"
            )
            continue

        if lowered in {"/topics", "/topic"}:
            _print_topics()
            continue

        if lowered == "/status":
            print(agent.tools.execute("get_session_context", {}).output)
            continue

        if lowered == "/tools":
            print("Permitted tools:")
            for name in agent.tools.names():
                print(f"  - {name}")
            continue

        if lowered == "/reset":
            storage.delete_session()
            try:
                topic = args.topic or _prompt_topic()
            except (EOFError, KeyboardInterrupt):
                print("\nThanks for being here today. See you next time!")
                return 0
            session = _ensure_session(args.name, topic)
            agent = FacilitatorAgent(session, force_mock=args.mock)
            print(
                f"Session reset. Topic: {session.topic or '(none)'}. "
                f"Agent mode: {agent.mode}"
            )
            continue

        # Handle user text
        turn = agent.handle(user_text)
        # Print turn
        print_turn(turn, show_traces=show_traces)

if __name__ == "__main__":
    sys.exit(main())
