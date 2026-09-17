"""Pydantic models. These validate and clean every piece of input before it ever
touches the database or the AI layer. Never trust the client."""
from __future__ import annotations
from pydantic import BaseModel, EmailStr, field_validator
from .security import PASSWORD_RULE


class SignupIn(BaseModel):
    display_name: str
    email: EmailStr
    password: str

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not (2 <= len(v) <= 120):
            raise ValueError("Please enter a name between 2 and 120 characters.")
        return v

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if not PASSWORD_RULE.match(v):
            raise ValueError("Password needs at least 8 characters, with a letter and a number.")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AnalyzeIn(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def sane_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 20:
            raise ValueError("Please paste a real argument, at least a couple of sentences.")
        if len(v) > 6000:
            raise ValueError("That is longer than one page. Please shorten it to keep the analysis sharp.")
        return v
