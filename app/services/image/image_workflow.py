# -*- coding: utf-8 -*-
"""
SINAX Batch Workflow Engine
Chained sequential processing pipeline allowing users to combine multiple actions
(e.g., Auto-Orient -> Resize -> Watermark -> Strip GPS -> Convert to WebP)
and execute them in a single batch pass over thousands of images.
"""

import json
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.services.image.image_service import image_service
from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WorkflowStep:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStep":
        return cls(
            action=data.get("action", ""),
            params=data.get("params", {}),
            enabled=data.get("enabled", True)
        )


class ImageWorkflow:
    """Represents an ordered sequence of image processing actions."""

    def __init__(self, name: str = "سير عمل جديد", description: str = "", steps: Optional[List[WorkflowStep]] = None):
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = steps or []

    def add_step(self, action: str, params: Optional[Dict[str, Any]] = None):
        self.steps.append(WorkflowStep(action=action, params=params or {}, enabled=True))

    def remove_step(self, index: int):
        if 0 <= index < len(self.steps):
            self.steps.pop(index)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageWorkflow":
        steps = [WorkflowStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data.get("name", "سير عمل"),
            description=data.get("description", ""),
            steps=steps
        )

    def execute_on_image(self, input_path: Path, output_path: Path) -> Dict[str, Any]:
        """
        Executes the chained workflow steps sequentially on a single image.
        Uses a double-buffered temp file approach so each step receives the previous step's output.
        Cleans up intermediate files immediately to guarantee low memory and disk footprint.
        """
        active_steps = [s for s in self.steps if s.enabled]
        if not active_steps:
            # Simply copy if no active steps
            import shutil
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_path, output_path)
            return {"success": True, "steps_executed": 0, "output_path": str(output_path)}

        in_p = Path(input_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        temp_files_to_clean: List[Path] = []
        curr_in = in_p

        try:
            total = len(active_steps)
            for idx, step in enumerate(active_steps):
                is_last = (idx == total - 1)
                
                if is_last:
                    curr_out = out_p
                else:
                    # Temporary file for intermediate step
                    ext = in_p.suffix or ".png"
                    tmp = Path(tempfile.mktemp(suffix=ext, prefix="sinax_wf_"))
                    curr_out = tmp
                    temp_files_to_clean.append(tmp)

                # Dispatch step action
                self._dispatch_step(step.action, step.params, curr_in, curr_out)
                curr_in = curr_out

            return {
                "success": True,
                "steps_executed": total,
                "output_path": str(out_p)
            }
        except Exception as e:
            logger.error(f"Workflow execution failed on {input_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "output_path": str(out_p)
            }
        finally:
            # Clean intermediate temporary files
            for tf in temp_files_to_clean:
                try:
                    if tf.exists():
                        tf.unlink()
                except Exception:
                    pass

    def _dispatch_step(self, action: str, params: Dict[str, Any], in_path: Path, out_path: Path):
        """Dispatches an atomic operation to ImageService."""
        if action == "auto_orient":
            image_service.rotate_orient_image(in_path, out_path, auto_orient=True)

        elif action == "rotate":
            image_service.rotate_orient_image(
                in_path, out_path,
                angle=params.get("angle", 90),
                flip_h=params.get("flip_h", False),
                flip_v=params.get("flip_v", False)
            )

        elif action == "resize":
            image_service.resize_image(
                in_path, out_path,
                mode=params.get("mode", "longest"),
                longest_edge=params.get("longest_edge", 1920),
                shortest_edge=params.get("shortest_edge"),
                width=params.get("width"),
                height=params.get("height"),
                percent=params.get("percent"),
                do_not_enlarge=params.get("do_not_enlarge", True)
            )

        elif action == "crop":
            image_service.crop_image(
                in_path, out_path,
                aspect_ratio=params.get("aspect_ratio", "1:1"),
                align=params.get("align", "center")
            )

        elif action == "strip_gps":
            image_service.metadata_image(in_path, out_path, action="strip_gps")

        elif action == "strip_metadata":
            image_service.metadata_image(in_path, out_path, action="strip_all")

        elif action == "watermark":
            image_service.watermark_image(
                in_path, out_path,
                text=params.get("text", "SINAX"),
                logo_path=params.get("logo_path"),
                position=params.get("position", "bottom_right"),
                opacity=params.get("opacity", 0.75),
                color=params.get("color", "#FFFFFF")
            )

        elif action == "enhance":
            image_service.enhance_filter_image(
                in_path, out_path,
                auto_enhance=params.get("auto_enhance", True),
                brightness=params.get("brightness", 1.0),
                contrast=params.get("contrast", 1.0),
                saturation=params.get("saturation", 1.0),
                sharpness=params.get("sharpness", 1.0),
                grayscale=params.get("grayscale", False)
            )

        elif action == "convert":
            image_service.convert_image(
                in_path, out_path,
                target_format=params.get("target_format", "webp"),
                quality=params.get("quality", 82)
            )

        elif action == "compress":
            image_service.compress_image(
                in_path, out_path,
                preset=params.get("preset", "balanced"),
                quality=params.get("quality", 80),
                target_size_kb=params.get("target_size_kb")
            )

        elif action == "border":
            image_service.border_canvas_image(
                in_path, out_path,
                border_width=params.get("border_width", 10),
                border_color=params.get("border_color", "#FFFFFF")
            )

        else:
            # Fallback direct copy
            import shutil
            shutil.copy2(in_path, out_path)


# Built-in industry presets
BUILTIN_WORKFLOWS = [
    ImageWorkflow(
        name="تجهيز الويب السريع (Web Ready)",
        description="تصحيح الاتجاه تلقائياً، تصغير حتى 1920px كحد أقصى، حذف GPS، والتحويل إلى صيغة WebP بجودة 82%",
        steps=[
            WorkflowStep("auto_orient", {}),
            WorkflowStep("resize", {"mode": "longest", "longest_edge": 1920, "do_not_enlarge": True}),
            WorkflowStep("strip_gps", {}),
            WorkflowStep("convert", {"target_format": "webp", "quality": 82})
        ]
    ),
    ImageWorkflow(
        name="تنظيف الخصوصية والمشاركة الآمنة",
        description="تصحيح الاتجاه، حذف كافة بيانات الميتاداتا و EXIF و GPS لضمان الخصوصية عند إرسال الصور",
        steps=[
            WorkflowStep("auto_orient", {}),
            WorkflowStep("strip_metadata", {})
        ]
    ),
    ImageWorkflow(
        name="سوشيال ميديا وتوقيع الحقوق",
        description="تصحيح الاتجاه، تحسين التباين، إضافة علامة مائية لحماية الحقوق، وتصدير JPG عالي الدقة",
        steps=[
            WorkflowStep("auto_orient", {}),
            WorkflowStep("enhance", {"auto_enhance": True}),
            WorkflowStep("watermark", {"text": "© SINAX", "position": "bottom_right", "opacity": 0.8}),
            WorkflowStep("convert", {"target_format": "jpg", "quality": 90})
        ]
    ),
    ImageWorkflow(
        name="توليد المصغرات السريعة Thumbnails",
        description="تصغير الصور إلى أبعاد 300px وحفظها كـ WebP خفيف جداً للأرشفة أو المواقع",
        steps=[
            WorkflowStep("auto_orient", {}),
            WorkflowStep("resize", {"mode": "longest", "longest_edge": 300, "do_not_enlarge": True}),
            WorkflowStep("convert", {"target_format": "webp", "quality": 75})
        ]
    ),
]
