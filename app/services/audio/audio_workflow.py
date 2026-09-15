# -*- coding: utf-8 -*-
"""
SINAX Audio Batch Workflow Engine
Chained sequential processing pipeline allowing users to combine multiple audio actions
(e.g., Silence Truncate -> Denoise -> EQ -> Loudness Normalization -> MP3 Convert)
and execute them in a single batch pass over hundreds or thousands of tracks.
"""

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.core.logger import get_logger
from app.services.audio.audio_service import audio_service

logger = get_logger("audio_workflow")


@dataclass
class AudioWorkflowStep:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioWorkflowStep":
        return cls(
            action=data.get("action", ""),
            params=data.get("params", {}),
            enabled=data.get("enabled", True),
        )


class AudioWorkflow:
    """Represents an ordered sequence of audio processing actions."""

    def __init__(
        self,
        name: str = "سير عمل صوتي مخصص",
        description: str = "",
        steps: Optional[List[AudioWorkflowStep]] = None,
    ):
        self.name = name
        self.description = description
        self.steps: List[AudioWorkflowStep] = steps or []

    def add_step(self, action: str, params: Optional[Dict[str, Any]] = None):
        self.steps.append(AudioWorkflowStep(action=action, params=params or {}, enabled=True))

    def remove_step(self, index: int):
        if 0 <= index < len(self.steps):
            self.steps.pop(index)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioWorkflow":
        steps = [AudioWorkflowStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data.get("name", "سير عمل صوتي مخصص"),
            description=data.get("description", ""),
            steps=steps,
        )

    def save_to_file(self, filepath: str):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "AudioWorkflow":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# Built-in Presets
DEFAULT_AUDIO_WORKFLOW_PRESETS: List[AudioWorkflow] = [
    AudioWorkflow(
        name="تجهيز البودكاست الاحترافي",
        description="إزالة الصمت + تنقية وشيش الخلفية + تجميل طبقات الصوت + معايرة -16 LUFS للنشر المباشر.",
        steps=[
            AudioWorkflowStep(action="silence_remove_audio", params={"threshold_db": -45.0, "min_dur_sec": 0.8}),
            AudioWorkflowStep(action="denoise_audio", params={"nr_level_db": -24.0}),
            AudioWorkflowStep(action="graphic_eq_audio", params={"bass_db": 2.0, "mid_db": 3.0, "treble_db": 2.0}),
            AudioWorkflowStep(action="loudness_normalize_audio", params={"target_lufs": -16.0, "true_peak": -1.0}),
            AudioWorkflowStep(action="batch_audio_convert", params={"format": "mp3", "bitrate": "192k"}),
        ]
    ),
    AudioWorkflow(
        name="تنقية وتضخيم التسجيلات والمحاضرات",
        description="حذف الصمت + إزالة طنين 50Hz + ضاغط ديناميكي لرفع الأصوات الهادئة + ضغط خفيف.",
        steps=[
            AudioWorkflowStep(action="silence_remove_audio", params={"threshold_db": -40.0, "min_dur_sec": 1.0}),
            AudioWorkflowStep(action="hum_removal_audio", params={"freq": 50}),
            AudioWorkflowStep(action="compressor_audio", params={"threshold_db": -20.0, "ratio": 4.0, "makeup_gain_db": 3.0}),
            AudioWorkflowStep(action="batch_audio_convert", params={"format": "mp3", "bitrate": "128k"}),
        ]
    ),
    AudioWorkflow(
        name="المعايرة الموسيقية لليوتيوب وسبوتيفاي",
        description="معايرة -14 LUFS بدقة عالمية + ليمتر حماية -1 dBFS + تحويل عالي الجودة 320k.",
        steps=[
            AudioWorkflowStep(action="loudness_normalize_audio", params={"target_lufs": -14.0, "true_peak": -1.0, "dual_pass": True}),
            AudioWorkflowStep(action="limiter_audio", params={"limit_db": -1.0}),
            AudioWorkflowStep(action="batch_audio_convert", params={"format": "mp3", "bitrate": "320k"}),
        ]
    ),
    AudioWorkflow(
        name="ضغط فائق للواتساب والتخزين السحابي",
        description="تحويل إلى مونو + خفض الحجم إلى 64k لمشاركة سريعة جداً على تطبيقات المراسلة.",
        steps=[
            AudioWorkflowStep(action="channel_routing_audio", params={"mode": "stereo_to_mono"}),
            AudioWorkflowStep(action="batch_audio_compress", params={"preset": "max"}),
        ]
    ),
]


class AudioWorkflowRunner:
    """Executes an AudioWorkflow pipeline on a file with double-buffered intermediate temp files."""

    def __init__(self, workflow: AudioWorkflow):
        self.workflow = workflow

    def execute(
        self,
        input_path: str,
        final_output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        enabled_steps = [s for s in self.workflow.steps if s.enabled]
        if not enabled_steps:
            return {"success": False, "message": "لا توجد خطوات مفعّلة في سير العمل."}

        total_steps = len(enabled_steps)
        curr_in = input_path
        temp_files_to_clean: List[str] = []

        try:
            for idx, step in enumerate(enabled_steps):
                if cancel_token and getattr(cancel_token, "is_cancelled", False):
                    return {"success": False, "message": "تم إلغاء سير العمل."}

                is_last = (idx == total_steps - 1)
                if is_last:
                    step_out = final_output_path
                else:
                    fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix=f"sinax_wf_step{idx}_")
                    os.close(fd)
                    step_out = temp_path
                    temp_files_to_clean.append(temp_path)

                if progress_callback:
                    pct = (idx / total_steps) * 100.0
                    progress_callback(pct, f"الخطوة {idx+1}/{total_steps}: {step.action}")

                # Execute step
                res = audio_service.dispatch_audio_operation(
                    tool_id=step.action,
                    input_path=curr_in,
                    output_path=step_out,
                    options=step.params,
                    cancel_token=cancel_token
                )

                if not res.get("success"):
                    return {
                        "success": False,
                        "message": f"فشلت الخطوة {idx+1} ({step.action}): {res.get('message')}"
                    }

                curr_in = step_out

            if progress_callback:
                progress_callback(100.0, "اكتمل سير العمل بنجاح!")

            return {"success": True, "output_path": final_output_path, "message": "اكتمل سير العمل بنجاح"}

        finally:
            for t_file in temp_files_to_clean:
                if os.path.exists(t_file):
                    try:
                        os.unlink(t_file)
                    except Exception:
                        pass
