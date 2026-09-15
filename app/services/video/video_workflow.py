# -*- coding: utf-8 -*-
"""
SINAX Video Batch Workflow Engine
Chained sequential processing pipeline allowing users to combine multiple video actions
(e.g., Cut Intro -> Scale to 9:16 Shorts -> Watermark -> Volume Normalize -> Compress)
and execute them in a single batch pass over many videos.
"""

import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.core.logger import get_logger
from app.services.video.video_service import video_service

logger = get_logger("video_workflow")


@dataclass
class VideoWorkflowStep:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoWorkflowStep":
        return cls(
            action=data.get("action", ""),
            params=data.get("params", {}),
            enabled=data.get("enabled", True),
        )


class VideoWorkflow:
    """Represents an ordered sequence of video processing actions."""

    def __init__(
        self,
        name: str = "سير عمل فيديو جديد",
        description: str = "",
        steps: Optional[List[VideoWorkflowStep]] = None,
    ):
        self.name = name
        self.description = description
        self.steps: List[VideoWorkflowStep] = steps or []

    def add_step(self, action: str, params: Optional[Dict[str, Any]] = None):
        self.steps.append(VideoWorkflowStep(action=action, params=params or {}, enabled=True))

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
    def from_dict(cls, data: Dict[str, Any]) -> "VideoWorkflow":
        steps = [VideoWorkflowStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data.get("name", "سير عمل فيديو"),
            description=data.get("description", ""),
            steps=steps,
        )

    def execute_on_video(
        self,
        input_path: str,
        output_path: str,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Executes the chained workflow steps sequentially on a single video.
        Uses double-buffering with intermediate temp files and cleans up automatically.
        """
        active_steps = [s for s in self.steps if s.enabled]
        if not active_steps:
            # Fallback: lossless copy
            res = video_service.fast_remux(input_path, output_path, callback, cancel_token)
            return {"success": res.get("success", False), "steps_executed": 0, "output_path": output_path}

        in_p = str(input_path)
        out_p = str(output_path)
        Path(out_p).parent.mkdir(parents=True, exist_ok=True)

        temp_files_to_clean: List[str] = []
        curr_in = in_p

        try:
            total_steps = len(active_steps)
            for idx, step in enumerate(active_steps):
                if cancel_token and cancel_token.is_set():
                    return {"success": False, "message": "تم إلغاء سير العمل."}

                is_last = (idx == total_steps - 1)

                if is_last:
                    curr_out = out_p
                else:
                    ext = Path(in_p).suffix or ".mp4"
                    tmp = tempfile.mktemp(suffix=ext, prefix=f"sinax_vwf_step{idx}_")
                    curr_out = tmp
                    temp_files_to_clean.append(tmp)

                step_cb = None
                if callback:
                    def make_cb(step_idx=idx, total=total_steps):
                        def _inner_cb(step_pct, info):
                            overall = ((step_idx + (step_pct / 100.0)) / total) * 100.0
                            info["workflow_step"] = f"{step_idx + 1}/{total}"
                            callback(overall, info)
                        return _inner_cb
                    step_cb = make_cb()

                res = self._dispatch_step(step.action, step.params, curr_in, curr_out, step_cb, cancel_token)
                if not res.get("success"):
                    return {
                        "success": False,
                        "error": f"فشلت الخطوة {idx + 1} ({step.action}): {res.get('message', 'خطأ غير معروف')}",
                        "output_path": out_p,
                    }

                curr_in = curr_out

            return {
                "success": True,
                "steps_executed": total_steps,
                "output_path": out_p,
            }
        except Exception as e:
            logger.error(f"Workflow execution failed on {input_path}: {e}", exc_info=True)
            return {"success": False, "error": str(e), "output_path": out_p}
        finally:
            for tf in temp_files_to_clean:
                try:
                    if Path(tf).exists():
                        Path(tf).unlink()
                except Exception:
                    pass

    def _dispatch_step(
        self,
        action: str,
        params: Dict[str, Any],
        in_p: str,
        out_p: str,
        callback: Optional[Callable],
        cancel_token: Optional[Any],
    ) -> Dict[str, Any]:
        """Dispatches an action to VideoService."""
        if action == "compress":
            return video_service.compress_video(
                in_p,
                out_p,
                preset=params.get("preset", "balanced"),
                crf=params.get("crf"),
                target_size_mb=params.get("target_size_mb"),
                use_gpu=params.get("use_gpu", True),
                callback=callback,
                cancel_token=cancel_token,
            )
        elif action == "resize":
            return video_service.resize_resolution(
                in_p,
                out_p,
                resolution=params.get("resolution", "1080p"),
                mode=params.get("mode", "fit"),
                custom_w=params.get("custom_w"),
                custom_h=params.get("custom_h"),
                use_gpu=params.get("use_gpu", True),
                callback=callback,
                cancel_token=cancel_token,
            )
        elif action == "rotate_flip":
            return video_service.rotate_flip(
                in_p,
                out_p,
                rotation=params.get("rotation", 0),
                flip_h=params.get("flip_h", False),
                flip_v=params.get("flip_v", False),
                use_gpu=params.get("use_gpu", True),
                callback=callback,
                cancel_token=cancel_token,
            )
        elif action == "watermark":
            return video_service.add_watermark(
                in_p,
                out_p,
                text=params.get("text"),
                logo_path=params.get("logo_path"),
                position=params.get("position", "bottom_right"),
                opacity=params.get("opacity", 0.8),
                font_size=params.get("font_size", 24),
                use_gpu=params.get("use_gpu", True),
                callback=callback,
                cancel_token=cancel_token,
            )
        elif action == "mute":
            return video_service.mute_audio(in_p, out_p, callback=callback, cancel_token=cancel_token)
        elif action == "normalize_volume":
            return video_service.normalize_volume(
                in_p,
                out_p,
                mode=params.get("mode", "ebu_r128"),
                factor=params.get("factor", 1.5),
                callback=callback,
                cancel_token=cancel_token,
            )
        elif action == "speed":
            return video_service.adjust_speed(
                in_p,
                out_p,
                speed_factor=params.get("speed_factor", 2.0),
                reverse=params.get("reverse", False),
                use_gpu=params.get("use_gpu", True),
                callback=callback,
                cancel_token=cancel_token,
            )
        elif action == "enhance":
            return video_service.enhance_video(
                in_p,
                out_p,
                brightness=params.get("brightness", 0.0),
                contrast=params.get("contrast", 1.0),
                saturation=params.get("saturation", 1.0),
                denoise=params.get("denoise", False),
                sharpen=params.get("sharpen", False),
                use_gpu=params.get("use_gpu", True),
                callback=callback,
                cancel_token=cancel_token,
            )
        elif action == "strip_metadata":
            return video_service.strip_metadata(in_p, out_p, callback=callback, cancel_token=cancel_token)
        elif action == "convert":
            return video_service.convert_format(
                in_p,
                out_p,
                video_codec=params.get("video_codec", "auto"),
                audio_codec=params.get("audio_codec", "auto"),
                use_gpu=params.get("use_gpu", True),
                callback=callback,
                cancel_token=cancel_token,
            )
        else:
            return video_service.fast_remux(in_p, out_p, callback=callback, cancel_token=cancel_token)


def get_predefined_workflows() -> List[Dict[str, Any]]:
    """Returns standard ready-made video automation workflows."""
    return [
        {
            "id": "wf_social_shorts",
            "name": "تجهيز مقاطع تيك توك و Shorts و Reels (9:16)",
            "description": "تحويل إلى مقاس طولي 9:16 مع خلفية ضبابية + ضبط الصوت EBU R128 + علامة مائية",
            "steps": [
                {"action": "resize", "params": {"resolution": "shorts_9_16", "mode": "vertical_blur"}, "enabled": True},
                {"action": "normalize_volume", "params": {"mode": "ebu_r128"}, "enabled": True},
                {"action": "watermark", "params": {"text": "SINAX", "position": "bottom_right", "opacity": 0.7}, "enabled": True},
            ],
        },
        {
            "id": "wf_web_optimized",
            "name": "ضغط فائق للنشر السريع على الويب ومواقع التواصل",
            "description": "ضغط متوازن CRF 24 + إزالة بيانات الكاميرا والبيانات الوصفية للخصوصية",
            "steps": [
                {"action": "compress", "params": {"preset": "balanced"}, "enabled": True},
                {"action": "strip_metadata", "params": {}, "enabled": True},
            ],
        },
        {
            "id": "wf_silent_speedup",
            "name": "مضاعفة السرعة وإلغاء الصوت (Timelapse صامت)",
            "description": "تسريع الفيديو x2 مع كتم الصوت كلياً لتجهيز لقطات تسريع الحركة",
            "steps": [
                {"action": "mute", "params": {}, "enabled": True},
                {"action": "speed", "params": {"speed_factor": 2.0}, "enabled": True},
            ],
        },
    ]
