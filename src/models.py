"""Dataclasses for circle sessions and seed content."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# ===== Mock types for session stages, preferences, experiment status, etc. =====

# Session stages
Stage = Literal[
    "ONBOARD", # User is onboarding
    "PREFERENCES", # User is choosing their preferences
    "JOIN_CIRCLE", # User is joining a circle
    "CHECK_IN", # User is checking in
    "REFLECTION", # User is reflecting
    "PEER_POST", # User is posting a peer post
    "PEER_REPLIES", # User is replying to a peer post
    "EXPERIMENT", # User is choosing an experiment
    "SUMMARY", # User is viewing the summary
    "DONE", # User has completed the session
]

# Preferences
Preference = Literal[
    "listening", # User is interested in listening to others
    "shared_experience", # User is interested in sharing their own experiences
    "practical_ideas", # User is interested in practical ideas
    "gentle_accountability", # User is interested in gentle accountability
    "encouragement", # User is interested in encouragement
]

# Experiment status
ExperimentStatus = Literal["accepted", "skipped"]

# Circle members
@dataclass
class Member:
    id: str
    display_name: str
    preferences: list[str]
    persona_note: str = ""

# Circle
@dataclass
class Circle:
    id: str
    topic: str
    title: str
    members: list[Member]

    # Class method to create a Circle from a dictionary
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Circle:
        members = [Member(**m) for m in data.get("members", [])]
        return cls(
            id=data["id"],
            topic=data["topic"],
            title=data["title"],
            members=members,
        )

# Prompts
@dataclass
class Prompt:
    id: str
    text: str
    rationale: str = ""

# Prompt library
@dataclass
class PromptLibrary:
    topic: str
    prompts: list[Prompt]

    # Class method to create a PromptLibrary from a dictionary
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptLibrary:
        prompts = [Prompt(**p) for p in data.get("prompts", [])]
        return cls(topic=data["topic"], prompts=prompts)

# Experiments
@dataclass
class Experiment:
    id: str
    text: str

# Experiment library
@dataclass
class ExperimentLibrary:
    topic: str
    experiments: list[Experiment]

    # Class method to create an ExperimentLibrary from a dictionary
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentLibrary:
        experiments = [Experiment(**e) for e in data.get("experiments", [])]
        return cls(topic=data["topic"], experiments=experiments)


# preference key -> list of template strings with optional {summary}/{hint}
ReplyTemplates = dict[str, list[str]]

# User
@dataclass
class User:
    id: str
    display_name: str
    preferences: list[str] = field(default_factory=list)

# Check in
@dataclass
class CheckIn:
    energy: int
    stress: int
    connection: int
    note: str

# Reflection
@dataclass
class Reflection:
    prompt_id: str
    answer: str

# Post
@dataclass
class Post:
    text: str

# Reply
@dataclass
class Reply:
    from_: str  # peer display name; serialised as "from"
    text: str

    # Method to convert a Reply to a dictionary
    def to_dict(self) -> dict[str, str]:
        return {"from": self.from_, "text": self.text}

    # Class method to create a Reply from a dictionary
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Reply:
        return cls(from_=data["from"], text=data["text"])

# Experiment choice
@dataclass
class ExperimentChoice:
    id: str
    status: ExperimentStatus

# Session
@dataclass
class Session:
    stage: Stage
    user: User | None
    topic: str | None
    circle_id: str | None
    prompt_id: str | None
    check_in: CheckIn | None
    reflection: Reflection | None
    post: Post | None
    replies: list[Reply]
    experiment: ExperimentChoice | None
    created_at: str
    updated_at: str
    completed_prompt_ids: list[str] = field(default_factory=list)
    suggested_prompt_focus: str | None = None
    suggested_experiment_focus: str | None = None
    pending_experiment_review: str | None = None
    experiment_review_note: str | None = None

    # Method to convert a Session to a dictionary
    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "user": asdict(self.user) if self.user else None,
            "topic": self.topic,
            "circle_id": self.circle_id,
            "prompt_id": self.prompt_id,
            "check_in": asdict(self.check_in) if self.check_in else None,
            "reflection": asdict(self.reflection) if self.reflection else None,
            "post": asdict(self.post) if self.post else None,
            "replies": [r.to_dict() for r in self.replies],
            "experiment": asdict(self.experiment) if self.experiment else None,
            "completed_prompt_ids": list(self.completed_prompt_ids),
            "suggested_prompt_focus": self.suggested_prompt_focus,
            "suggested_experiment_focus": self.suggested_experiment_focus,
            "pending_experiment_review": self.pending_experiment_review,
            "experiment_review_note": self.experiment_review_note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        user_data = data.get("user")
        check_in_data = data.get("check_in")
        reflection_data = data.get("reflection")
        post_data = data.get("post")
        experiment_data = data.get("experiment")
        replies_data = data.get("replies") or []

        return cls(
            stage=data["stage"],
            user=User(**user_data) if user_data else None,
            topic=data.get("topic"),
            circle_id=data.get("circle_id"),
            prompt_id=data.get("prompt_id"),
            check_in=CheckIn(**check_in_data) if check_in_data else None,
            reflection=Reflection(**reflection_data) if reflection_data else None,
            post=Post(**post_data) if post_data else None,
            replies=[Reply.from_dict(r) for r in replies_data],
            experiment=(
                ExperimentChoice(**experiment_data) if experiment_data else None
            ),
            completed_prompt_ids=list(data.get("completed_prompt_ids") or []),
            suggested_prompt_focus=data.get("suggested_prompt_focus"),
            suggested_experiment_focus=data.get("suggested_experiment_focus"),
            pending_experiment_review=data.get("pending_experiment_review"),
            experiment_review_note=data.get("experiment_review_note"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    # Property to check if a session is resumable
    @property
    def is_resumable(self) -> bool:
        if self.pending_experiment_review:
            return True
        return self.stage != "DONE"


@dataclass
class TopicInfo:
    id: str
    title: str
    summary: str
    aliases: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TopicInfo:
        return cls(
            id=data["id"],
            title=data["title"],
            summary=data.get("summary", ""),
            aliases=list(data.get("aliases") or []),
        )
