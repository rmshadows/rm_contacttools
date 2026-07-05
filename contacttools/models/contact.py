from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


def new_id() -> str:
    return str(uuid4())


@dataclass
class Phone:
    number: str
    types: list[str] = field(default_factory=lambda: ["CELL"])
    pref: bool = False
    sort_order: int = 0


@dataclass
class Email:
    address: str
    types: list[str] = field(default_factory=lambda: ["HOME"])
    sort_order: int = 0


@dataclass
class Contact:
    fn: str
    id: str = field(default_factory=new_id)
    fn_pinyin: str = ""
    sort_string: str = ""
    n_family: str = ""
    n_given: str = ""
    phones: list[Phone] = field(default_factory=list)
    emails: list[Email] = field(default_factory=list)
    org: Optional[str] = None
    title: Optional[str] = None
    note: Optional[str] = None
    url: Optional[str] = None
    photo: Optional[bytes] = None
    source: Optional[str] = None
    imported_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.fn and (self.n_family or self.n_given):
            self.fn = composed_from_parts(self.n_family, self.n_given)
        if not self.n_given and self.fn and not self.n_family:
            self.n_given = self.fn

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


def composed_from_parts(family: str, given: str) -> str:
    return (family or "") + (given or "")
