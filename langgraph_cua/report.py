"""
CUA Task Analysis Report Generator

Analyzes the results of a Computer Use Agent run and generates
a detailed report of actions taken, successes, failures, and timing.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class ActionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ActionRecord:
    """Record of a single computer action."""
    action_type: str
    call_id: str
    status: ActionStatus
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class CUAReport:
    """Complete analysis report of a CUA run."""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    skipped_actions: int = 0
    actions: List[ActionRecord] = field(default_factory=list)
    instance_id: Optional[str] = None
    final_status: str = "unknown"
    error_summary: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        if self.total_actions == 0:
            return 0.0
        return (self.successful_actions / self.total_actions) * 100

    def add_action(self, action: ActionRecord) -> None:
        """Add an action record to the report."""
        self.actions.append(action)
        self.total_actions += 1
        if action.status == ActionStatus.SUCCESS:
            self.successful_actions += 1
        elif action.status == ActionStatus.FAILED:
            self.failed_actions += 1
            if action.error:
                self.error_summary.append(f"{action.action_type}: {action.error}")
        else:
            self.skipped_actions += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_actions": self.total_actions,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "skipped_actions": self.skipped_actions,
            "success_rate": f"{self.success_rate:.1f}%",
            "instance_id": self.instance_id,
            "final_status": self.final_status,
            "error_summary": self.error_summary,
            "actions": [
                {
                    "action_type": a.action_type,
                    "call_id": a.call_id,
                    "status": a.status.value,
                    "timestamp": a.timestamp.isoformat(),
                    "details": a.details,
                    "error": a.error,
                    "duration_ms": a.duration_ms,
                }
                for a in self.actions
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Generate a markdown formatted report."""
        lines = [
            "# CUA Task Analysis Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Start Time | {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} |",
            f"| End Time | {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else 'N/A'} |",
            f"| Duration | {self.duration_seconds:.1f}s |" if self.duration_seconds else "| Duration | N/A |",
            f"| Instance ID | `{self.instance_id or 'N/A'}` |",
            f"| Final Status | **{self.final_status.upper()}** |",
            "",
            "## Action Statistics",
            "",
            f"| Status | Count | Percentage |",
            f"|--------|-------|------------|",
            f"| Total | {self.total_actions} | 100% |",
            f"| Successful | {self.successful_actions} | {self.success_rate:.1f}% |",
            f"| Failed | {self.failed_actions} | {(self.failed_actions/max(1,self.total_actions))*100:.1f}% |",
            f"| Skipped | {self.skipped_actions} | {(self.skipped_actions/max(1,self.total_actions))*100:.1f}% |",
            "",
        ]

        # Action breakdown by type
        action_types: Dict[str, Dict[str, int]] = {}
        for action in self.actions:
            if action.action_type not in action_types:
                action_types[action.action_type] = {"success": 0, "failed": 0, "skipped": 0}
            action_types[action.action_type][action.status.value] += 1

        if action_types:
            lines.extend([
                "## Actions by Type",
                "",
                "| Action Type | Success | Failed | Skipped | Total |",
                "|-------------|---------|--------|---------|-------|",
            ])
            for action_type, counts in sorted(action_types.items()):
                total = sum(counts.values())
                lines.append(
                    f"| {action_type} | {counts['success']} | {counts['failed']} | {counts['skipped']} | {total} |"
                )
            lines.append("")

        # Detailed action timeline
        lines.extend([
            "## Action Timeline",
            "",
        ])

        for i, action in enumerate(self.actions, 1):
            status_emoji = "✅" if action.status == ActionStatus.SUCCESS else "❌" if action.status == ActionStatus.FAILED else "⏭️"
            lines.append(f"### {i}. {status_emoji} {action.action_type}")
            lines.append("")
            lines.append(f"- **Call ID:** `{action.call_id}`")
            lines.append(f"- **Status:** {action.status.value}")
            lines.append(f"- **Time:** {action.timestamp.strftime('%H:%M:%S')}")
            if action.duration_ms:
                lines.append(f"- **Duration:** {action.duration_ms:.0f}ms")
            if action.details:
                lines.append(f"- **Details:** `{json.dumps(action.details)}`")
            if action.error:
                lines.append(f"- **Error:** {action.error}")
            lines.append("")

        # Error summary
        if self.error_summary:
            lines.extend([
                "## Error Summary",
                "",
            ])
            for error in self.error_summary:
                lines.append(f"- {error}")
            lines.append("")

        return "\n".join(lines)

    def print_summary(self) -> None:
        """Print a concise summary to console."""
        print("\n" + "=" * 60)
        print("CUA TASK ANALYSIS REPORT")
        print("=" * 60)
        print(f"Duration: {self.duration_seconds:.1f}s" if self.duration_seconds else "Duration: N/A")
        print(f"Status: {self.final_status.upper()}")
        print(f"Instance: {self.instance_id or 'N/A'}")
        print("-" * 60)
        print(f"Total Actions:  {self.total_actions}")
        print(f"  ✅ Successful: {self.successful_actions}")
        print(f"  ❌ Failed:     {self.failed_actions}")
        print(f"  ⏭️  Skipped:    {self.skipped_actions}")
        print(f"  Success Rate: {self.success_rate:.1f}%")
        print("-" * 60)

        if self.error_summary:
            print("Errors:")
            for error in self.error_summary[:5]:  # Show first 5 errors
                print(f"  • {error[:80]}...")
            if len(self.error_summary) > 5:
                print(f"  ... and {len(self.error_summary) - 5} more errors")

        print("=" * 60 + "\n")


class CUAReportGenerator:
    """
    Generates analysis reports from CUA execution results.

    Usage:
        generator = CUAReportGenerator()

        # Track actions during execution
        generator.start()
        generator.record_action("click", "call_123", {"x": 100, "y": 200})
        generator.record_action("type_text", "call_456", {"text": "hello"}, error="Failed to type")
        generator.finish(status="completed", instance_id="abc-123")

        # Generate report
        report = generator.get_report()
        print(report.to_markdown())
    """

    def __init__(self):
        self._report: Optional[CUAReport] = None
        self._last_action_time: Optional[datetime] = None

    def start(self) -> None:
        """Start tracking a new CUA run."""
        self._report = CUAReport(start_time=datetime.now())
        self._last_action_time = datetime.now()

    def record_action(
        self,
        action_type: str,
        call_id: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        status: Optional[ActionStatus] = None,
    ) -> None:
        """Record a computer action."""
        if self._report is None:
            self.start()

        now = datetime.now()
        duration_ms = None
        if self._last_action_time:
            duration_ms = (now - self._last_action_time).total_seconds() * 1000

        if status is None:
            status = ActionStatus.FAILED if error else ActionStatus.SUCCESS

        action = ActionRecord(
            action_type=action_type,
            call_id=call_id,
            status=status,
            timestamp=now,
            details=details or {},
            error=error,
            duration_ms=duration_ms,
        )

        self._report.add_action(action)
        self._last_action_time = now

    def finish(
        self,
        status: str = "completed",
        instance_id: Optional[str] = None,
    ) -> None:
        """Mark the CUA run as finished."""
        if self._report:
            self._report.end_time = datetime.now()
            self._report.final_status = status
            self._report.instance_id = instance_id

    def get_report(self) -> Optional[CUAReport]:
        """Get the generated report."""
        return self._report

    @staticmethod
    def from_stream_updates(updates: List[Any]) -> CUAReport:
        """
        Generate a report from a list of stream updates.

        Args:
            updates: List of updates from graph.astream()

        Returns:
            CUAReport with analyzed results
        """
        report = CUAReport(start_time=datetime.now())

        for update in updates:
            # Handle tuple format from subgraph streaming
            if isinstance(update, tuple) and len(update) == 2:
                path, data = update
            else:
                data = update

            if not isinstance(data, dict):
                continue

            # Extract action info from take_computer_action updates
            if "take_computer_action" in data:
                action_data = data["take_computer_action"]
                messages = action_data.get("messages", {})

                # Get instance_id if available
                if action_data.get("instance_id"):
                    report.instance_id = action_data["instance_id"]

                # Extract action details from the tool call
                additional_kwargs = messages.get("additional_kwargs", {})
                error = additional_kwargs.get("error")

                action = ActionRecord(
                    action_type="computer_action",
                    call_id=messages.get("tool_call_id", "unknown"),
                    status=ActionStatus.FAILED if error else ActionStatus.SUCCESS,
                    timestamp=datetime.now(),
                    details={},
                    error=error,
                )
                report.add_action(action)

            # Extract from call_model updates
            elif "call_model" in data:
                model_data = data["call_model"]
                messages = model_data.get("messages", {})

                if hasattr(messages, "additional_kwargs"):
                    tool_outputs = messages.additional_kwargs.get("tool_outputs", [])
                    for output in tool_outputs:
                        if output.get("type") == "computer_call":
                            action_info = output.get("action", {})
                            action = ActionRecord(
                                action_type=action_info.get("type", "unknown"),
                                call_id=output.get("call_id", "unknown"),
                                status=ActionStatus.SUCCESS,
                                timestamp=datetime.now(),
                                details=action_info,
                            )
                            report.add_action(action)

            # Extract from create_vm_instance updates
            elif "create_vm_instance" in data:
                instance_data = data["create_vm_instance"]
                if instance_data.get("instance_id"):
                    report.instance_id = instance_data["instance_id"]

        report.end_time = datetime.now()
        report.final_status = "completed" if report.failed_actions == 0 else "completed_with_errors"

        return report


def generate_report_from_state(final_state: Dict[str, Any]) -> CUAReport:
    """
    Generate a report from the final state of a CUA run.

    Args:
        final_state: The final state dictionary from the CUA graph

    Returns:
        CUAReport with analyzed results
    """
    report = CUAReport(start_time=datetime.now())
    report.instance_id = final_state.get("instance_id")

    messages = final_state.get("messages", [])

    for message in messages:
        # Check for AI messages with tool outputs
        if hasattr(message, "additional_kwargs"):
            tool_outputs = message.additional_kwargs.get("tool_outputs", [])
            for output in tool_outputs:
                if output.get("type") == "computer_call":
                    action_info = output.get("action", {})
                    action = ActionRecord(
                        action_type=action_info.get("type", "unknown"),
                        call_id=output.get("call_id", "unknown"),
                        status=ActionStatus.SUCCESS,
                        timestamp=datetime.now(),
                        details=action_info,
                    )
                    report.add_action(action)

        # Check for tool messages (responses)
        if hasattr(message, "type") and message.type == "tool":
            additional_kwargs = getattr(message, "additional_kwargs", {})
            if additional_kwargs.get("type") == "computer_call_output":
                error = additional_kwargs.get("error")
                if error:
                    # Find the matching action and mark it as failed
                    call_id = getattr(message, "tool_call_id", None)
                    for action in report.actions:
                        if action.call_id == call_id:
                            action.status = ActionStatus.FAILED
                            action.error = error
                            report.successful_actions -= 1
                            report.failed_actions += 1
                            report.error_summary.append(f"{action.action_type}: {error}")
                            break

    report.end_time = datetime.now()
    report.final_status = "completed" if report.failed_actions == 0 else "completed_with_errors"

    return report
