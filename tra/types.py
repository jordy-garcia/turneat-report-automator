from typing import Literal, NotRequired, TypedDict

EnvLabel = str
CommitDateBasis = Literal["author", "committer"]


class CommitRecord(TypedDict):
    sha: str
    message: str
    env: EnvLabel
    author: str
    author_email: str


class BulletItem(TypedDict):
    text: str
    env: EnvLabel
    hours: NotRequired[float | None]


class ExtraTaskLine(TypedDict):
    text: str
    hours: NotRequired[float | None]


class SubsectionBlock(TypedDict):
    title: str
    bullets: list[BulletItem]


class ReportSection(TypedDict):
    title: str
    subsections: list[SubsectionBlock]


class ProjectData(TypedDict):
    name: str
    commits: list[CommitRecord]
    count: int
    extras: list[dict]
    manual_hours: int | None
