# -*- coding: utf-8 -*-
"""
SINAX Audio Service Package
"""

from app.services.audio.audio_registry import (
    AUDIO_CATEGORIES,
    AUDIO_TOOLS_REGISTRY,
    AudioToolDefinition,
    get_audio_tool_by_id,
    get_audio_tools_by_category,
    search_audio_tools,
)
from app.services.audio.audio_service import AudioService, audio_service
from app.services.audio.audio_utils import (
    AUDIO_FORMATS,
    AUDIO_EXTENSIONS,
    is_audio_file,
    scan_audio_files,
    format_duration,
    parse_time_str,
    calc_target_audio_bitrate,
    COMPRESS_PRESETS,
    LOUDNORM_PRESETS,
    EQ_PRESETS,
)
from app.services.audio.audio_workflow import (
    AudioWorkflow,
    AudioWorkflowStep,
    AudioWorkflowRunner,
    DEFAULT_AUDIO_WORKFLOW_PRESETS,
)

__all__ = [
    "AUDIO_CATEGORIES",
    "AUDIO_TOOLS_REGISTRY",
    "AudioToolDefinition",
    "get_audio_tool_by_id",
    "get_audio_tools_by_category",
    "search_audio_tools",
    "AudioService",
    "audio_service",
    "AUDIO_FORMATS",
    "AUDIO_EXTENSIONS",
    "is_audio_file",
    "scan_audio_files",
    "format_duration",
    "parse_time_str",
    "calc_target_audio_bitrate",
    "COMPRESS_PRESETS",
    "LOUDNORM_PRESETS",
    "EQ_PRESETS",
    "AudioWorkflow",
    "AudioWorkflowStep",
    "AudioWorkflowRunner",
    "DEFAULT_AUDIO_WORKFLOW_PRESETS",
]
