"""Load and save seed data and session JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import (
    Circle,
    Prompt,
    PromptLibrary,
    ReplyTemplates,
    Session,
    TopicInfo,
    User,
)

# Project root is parent of src/
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
TOPICS_DIR = DATA_DIR / "topics"

TOPICS_CATALOG_PATH = DATA_DIR / "topics.json"
TEMPLATES_PATH = DATA_DIR / "templates.json"
RESOURCES_PATH = DATA_DIR / "resources.json"
SESSION_PATH = DATA_DIR / "session.json"
CBT_INFORMED_PATH = DATA_DIR / "interventions" / "cbt_informed.json"

# ===== Helpers =====
# Get current UTC time in ISO format
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

# Load JSON
def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)

# Save JSON
def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

# Load topics
def load_topics() -> list[TopicInfo]:
    data = load_json(TOPICS_CATALOG_PATH)
    return [TopicInfo.from_dict(t) for t in data.get("topics", [])]

# Resolve topic ID
def resolve_topic_id(query: str) -> TopicInfo | None:
    """Match a topic id, title, or alias (case-insensitive, substring for aliases)."""
    q = query.strip().lower().replace("-", "_").replace(" ", "_")
    q_raw = query.strip().lower()
    topics = load_topics()

    # Match topic ID or title
    for topic in topics:
        if topic.id == q or topic.id.replace("_", " ") == q_raw:
            return topic
        if topic.title.lower() == q_raw:
            return topic

    # Match topic alias
    for topic in topics:
        for alias in topic.aliases:
            a = alias.lower()
            if a == q_raw or a.replace(" ", "_") == q:
                return topic
            if len(a) >= 4 and (a in q_raw or q_raw in a):
                return topic
    return None

# Get topic directory
def topic_dir(topic_id: str) -> Path:
    return TOPICS_DIR / topic_id

# Require topic
def require_topic(topic_id: str | None) -> str:
    if not topic_id:
        raise ValueError(
            "No topic selected. Call list_topics then join_topic first."
        )
    info = resolve_topic_id(topic_id)
    if info is None:
        raise ValueError(f"Unknown topic: {topic_id}")
    return info.id

# Load circle
def load_circle(topic_id: str | None = None) -> Circle:
    tid = require_topic(topic_id)
    return Circle.from_dict(load_json(topic_dir(tid) / "circle.json"))

# Load prompts (shared CBT-informed library; topic_id kept for API compat)
def load_prompts(topic_id: str | None = None) -> PromptLibrary:
    data = load_cbt_informed()
    prompts = [
        Prompt(
            id=p["id"],
            text=p["text"],
            rationale=p.get("rationale", ""),
        )
        for p in data.get("prompts") or []
    ]
    label = topic_id or "cbt_informed"
    return PromptLibrary(topic=label, prompts=prompts)

# Load reply templates (supports legacy flat map or structured CBT-informed file)
def load_templates() -> ReplyTemplates:
    data = load_json(TEMPLATES_PATH)
    if isinstance(data, dict) and "templates" in data:
        templates = data["templates"]
    else:
        templates = data
    if not isinstance(templates, dict):
        raise ValueError("templates.json must map preferences to template lists")
    return {str(k): list(v) for k, v in templates.items()}


def load_template_library() -> dict[str, Any]:
    """Full CBT-informed peer-template library (framing, norms, hints, templates)."""
    data = load_json(TEMPLATES_PATH)
    if isinstance(data, dict) and "templates" in data:
        return data
    return {
        "framing": "preference-matched peer replies",
        "templates": data if isinstance(data, dict) else {},
        "hints": {},
        "preference_norms": {},
    }

# Load resources
def load_resources(topic_id: str | None = None) -> list[dict[str, Any]]:
    data = load_json(RESOURCES_PATH)
    resources = list(data.get("resources", []))
    if not topic_id:
        return resources
    filtered = []
    for r in resources:
        topics = r.get("topics") or ["*"]
        if "*" in topics or topic_id in topics:
            filtered.append(r)
    return filtered


def load_cbt_informed() -> dict[str, Any]:
    """Shared CBT-informed prompt + experiment library (not clinical CBT)."""
    return load_json(CBT_INFORMED_PATH)

# Check if session exists
def session_exists() -> bool:
    return SESSION_PATH.is_file()

# Load session
def load_session() -> Session | None:
    if not session_exists():
        return None
    return Session.from_dict(load_json(SESSION_PATH))

# Save session
def save_session(session: Session) -> None:
    session.updated_at = utc_now_iso()
    save_json(SESSION_PATH, session.to_dict())

# Create session
def create_session(
    *,
    display_name: str = "",
    topic: str | None = None,
    circle_id: str | None = None,
    prompt_id: str | None = None,
) -> Session:
    """Create a fresh session at ONBOARD and persist it."""
    now = utc_now_iso()
    user = None
    if display_name:
        user = User(id="user-local", display_name=display_name, preferences=[])

    # Create session
    session = Session(
        stage="ONBOARD",
        user=user,
        topic=topic,
        circle_id=circle_id,
        prompt_id=prompt_id,
        check_in=None,
        reflection=None,
        post=None,
        replies=[],
        experiment=None,
        completed_prompt_ids=[],
        suggested_prompt_focus=None,
        suggested_experiment_focus=None,
        pending_experiment_review=None,
        experiment_review_note=None,
        created_at=now,
        updated_at=now,
    )
    
    # Save session
    save_json(SESSION_PATH, session.to_dict())
    return session

# Delete session
def delete_session() -> None:
    # Delete session file if it exists
    if session_exists():
        SESSION_PATH.unlink()
