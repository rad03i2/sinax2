# -*- coding: utf-8 -*-
"""
Maintenance Recommendation Engine for SINAX.
Implements evidence-based logical rules to match detected system issues with
safe, targeted maintenance actions. Strictly avoids recommending unrelated repairs.
"""

import uuid
import time
from typing import List
from app.services.maintenance.models import (
    DiagnosticIssue,
    MaintenanceAction,
    MaintenancePlan,
    ScanMode,
    Severity,
    RiskLevel,
)
from app.services.maintenance.maintenance_registry import MaintenanceRegistry


class MaintenanceRecommendationEngine:
    """Evaluates diagnostic findings and synthesizes a structured Maintenance Plan."""

    @classmethod
    def generate_plan(
        cls, issues: List[DiagnosticIssue], scan_mode: ScanMode = ScanMode.QUICK
    ) -> MaintenancePlan:
        """
        Takes diagnostic issues, applies rule matrices, and produces a deduplicated,
        prioritized MaintenancePlan with clear explanations.
        """
        recommended_actions: List[MaintenanceAction] = []
        action_ids_added = set()

        total_reclaimable = 0
        restart_count = 0
        admin_count = 0

        # Sort issues by severity priority (Critical > Warning > Review Needed > Suggestion > Info)
        severity_order = {
            Severity.CRITICAL_ISSUE: 0,
            Severity.WARNING: 1,
            Severity.REVIEW_NEEDED: 2,
            Severity.SUGGESTION: 3,
            Severity.INFO: 4,
        }
        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.severity, 5))

        for issue in sorted_issues:
            if not issue.suggested_action_id:
                continue

            action = MaintenanceRegistry.get_action(issue.suggested_action_id)
            if action and action.id not in action_ids_added:
                action_ids_added.add(action.id)
                recommended_actions.append(action)

                if action.requires_restart:
                    restart_count += 1
                if action.requires_admin:
                    admin_count += 1

                # If issue relates to storage cleanup, estimate reclaimable
                if issue.category == "storage" and "bytes" in issue.technical_details:
                    try:
                        import json
                        d = json.loads(issue.technical_details)
                        total_reclaimable += d.get("reclaimable_bytes", 0)
                    except Exception:
                        pass

        # Sort actions: Low risk & safe defaults first, then higher risk
        recommended_actions.sort(key=lambda a: (a.risk_level.value, not a.is_safe_default))

        session_id = str(uuid.uuid4())[:8]
        return MaintenancePlan(
            session_id=session_id,
            timestamp=time.time(),
            scan_mode=scan_mode,
            issues_found=sorted_issues,
            recommended_actions=recommended_actions,
            total_reclaimable_bytes=total_reclaimable,
            requires_restart_count=restart_count,
            requires_admin_count=admin_count,
        )
