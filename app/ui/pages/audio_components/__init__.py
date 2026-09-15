# -*- coding: utf-8 -*-
"""
SINAX Audio UI Components Package
"""

from app.ui.pages.audio_components.audio_card_widget import AudioCardWidget
from app.ui.pages.audio_components.audio_inspector_dialog import AudioInspectorDialog
from app.ui.pages.audio_components.audio_options_panel import AudioOptionsPanel
from app.ui.pages.audio_components.audio_player_widget import AudioPlayerWidget
from app.ui.pages.audio_components.audio_workflow_builder import AudioWorkflowBuilderWidget
from app.ui.pages.audio_components.audio_workspace import AudioToolWorkspace

__all__ = [
    "AudioCardWidget",
    "AudioPlayerWidget",
    "AudioOptionsPanel",
    "AudioInspectorDialog",
    "AudioWorkflowBuilderWidget",
    "AudioToolWorkspace",
]
