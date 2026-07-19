from __future__ import annotations
import datetime
from pathlib import Path


class AuditLogger:
    """A utility for appending enterprise audit logs."""

    def __init__(self, log_path: str | Path = ".repollama_data/enterprise_audit.log") -> None:
        """Initialize the AuditLogger.

        Args:
            log_path (str | Path): The path to the audit log file.
        """
        self.log_path = Path(log_path)

    def log_action(self, action: str) -> None:
        """Log a timestamped action to the audit log file.

        Args:
            action (str): The action description to log.
        """
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] ACTION: {action}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(log_line)


class RBACManager:
    """Role-Based Access Control manager mock."""

    def has_permission(self, user_role: str, action: str) -> bool:
        """Determine if a user role has permission to perform an action.

        For example, roles like Architect can bypass drift checks, while
        Developer roles cannot.

        Args:
            user_role (str): The role of the user (e.g. 'Architect', 'Developer').
            action (str): The action to check permission for (e.g. 'bypass_drift').

        Returns:
            bool: True if the role has permission, False otherwise.
        """
        role_lower = user_role.lower()
        if action == "bypass_drift":
            return role_lower == "architect"
        return False
