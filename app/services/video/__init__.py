# -*- coding: utf-8 -*-
"""
SINAX Video Service Package
Local-first video processing, inspection, hardware acceleration, and workflow management.
"""

from app.services.video.video_registry import (
    VIDEO_TOOLS,
    VIDEO_CATEGORIES,
    get_all_video_tools,
    get_tools_by_category,
    get_video_tool_by_id,
)
from app.services.video.hardware_detector import hardware_detector
from app.services.video.ffmpeg_service import ffmpeg_service
from app.services.video.video_service import video_service
from app.services.video.video_workflow import VideoWorkflow, VideoWorkflowStep, get_predefined_workflows
from app.services.video.video_utils import (
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    parse_timestamp,
    format_seconds,
    format_bytes,
    calculate_target_bitrate,
    scan_video_files,
    generate_output_path,
)

__all__ = [
    "VIDEO_TOOLS",
    "VIDEO_CATEGORIES",
    "get_all_video_tools",
    "get_tools_by_category",
    "get_video_tool_by_id",
    "hardware_detector",
    "ffmpeg_service",
    "video_service",
    "VideoWorkflow",
    "VideoWorkflowStep",
    "get_predefined_workflows",
    "VIDEO_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "parse_timestamp",
    "format_seconds",
    "format_bytes",
    "calculate_target_bitrate",
    "scan_video_files",
    "generate_output_path",
]
