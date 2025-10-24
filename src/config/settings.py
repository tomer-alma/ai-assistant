from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel


class AudioSettings(BaseModel):
    sample_rate: int
    channels: int
    device_input: str
    device_output: str
    vad_frame_ms: int
    vad_aggressiveness: int


class LanguageSettings(BaseModel):
    stt_lang: str
    tts_lang: str
    style_prompt: str
    greeting: str
    closing: str
    exit_keywords: list[str]


class StreamingSettings(BaseModel):
    stt_partials: bool
    llm_stream_tokens: bool
    tts_stream_audio: bool
    half_duplex: bool
    barge_in: bool
    first_token_timeout_ms: int


class ModelSettings(BaseModel):
    stt: str
    llm: str
    tts: str
    tts_voice: str


class SafetySettings(BaseModel):
    enable_moderation: bool
    fallback_message: str


class TimeoutSettings(BaseModel):
    stt_finalize_ms: int
    llm_total_ms: int
    tts_chunk_ms: int
    post_greeting_settle_ms: int
    post_response_settle_ms: int


class DebuggingSettings(BaseModel):
    show_latency: bool


class AppSettings(BaseModel):
    audio: AudioSettings
    language: LanguageSettings
    streaming: StreamingSettings
    models: ModelSettings
    safety: SafetySettings
    timeouts: TimeoutSettings
    debugging: DebuggingSettings


_DEF_YAML = Path(__file__).with_name("default.yaml")


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge_env(overrides: Dict[str, Any]) -> Dict[str, Any]:
    # Placeholder for future env overrides if needed
    return overrides


def load_settings() -> AppSettings:
    data = _load_yaml(_DEF_YAML)
    data = _merge_env(data)
    return AppSettings(**data)
