from __future__ import annotations
import asyncio
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from repollama.engines.ci_gatekeeper import CIGatekeeper
from repollama.core.enterprise import AuditLogger, RBACManager
from typer.testing import CliRunner
from repollama.cli import app

runner = CliRunner()


def test_rbac_manager() -> None:
    rbac = RBACManager()
    # Architect bypass drift check
    assert rbac.has_permission("Architect", "bypass_drift") is True
    assert rbac.has_permission("architect", "bypass_drift") is True
    # Developer cannot bypass drift check
    assert rbac.has_permission("Developer", "bypass_drift") is False
    assert rbac.has_permission("developer", "bypass_drift") is False
    # Other actions check
    assert rbac.has_permission("Architect", "some_other_action") is False


def test_audit_logger() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "enterprise_audit.log"
        logger = AuditLogger(log_path=log_file)
        
        logger.log_action("Test Action 1")
        logger.log_action("Test Action 2")
        
        assert log_file.exists()
        lines = log_file.read_text().splitlines()
        assert len(lines) == 2
        assert "ACTION: Test Action 1" in lines[0]
        assert "ACTION: Test Action 2" in lines[1]


@pytest.mark.anyio
@patch("repollama.engines.ci_gatekeeper.Repo")
@patch("repollama.engines.ci_gatekeeper.DriftDetector")
@patch("repollama.engines.ci_gatekeeper.DebtEvaluator")
async def test_evaluate_pr_pass(
    mock_debt_evaluator_class: MagicMock,
    mock_drift_detector_class: MagicMock,
    mock_repo_class: MagicMock,
) -> None:
    # Mock DriftDetector
    mock_drift_detector = MagicMock()
    mock_drift_detector.detect_drift.return_value = {
        "src/api.py": {"added": [], "removed": ["os"]}
    }
    mock_drift_detector_class.return_value = mock_drift_detector

    # Mock Repo & Diffs
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo
    mock_base_commit = MagicMock()
    mock_repo.commit.return_value = mock_base_commit
    
    mock_diff = MagicMock()
    mock_diff.change_type = "M"
    mock_diff.b_path = "src/api.py"
    mock_base_commit.diff.return_value = [mock_diff]

    # Mock DebtEvaluator
    mock_debt_evaluator = MagicMock()
    mock_debt_evaluator.evaluate = AsyncMock(return_value=[
        {"file": "src/api.py", "score": 40}
    ])
    mock_debt_evaluator_class.return_value = mock_debt_evaluator

    gatekeeper = CIGatekeeper()
    with tempfile.TemporaryDirectory() as tmpdir:
        report = await gatekeeper.evaluate_pr(tmpdir, "HEAD~1", "HEAD")
        
        assert report["passed"] is True
        assert report["highest_debt_score"] == 40
        assert "src/api.py" in report["drift"]


@pytest.mark.anyio
@patch("repollama.engines.ci_gatekeeper.Repo")
@patch("repollama.engines.ci_gatekeeper.DriftDetector")
@patch("repollama.engines.ci_gatekeeper.DebtEvaluator")
async def test_evaluate_pr_fail_drift(
    mock_debt_evaluator_class: MagicMock,
    mock_drift_detector_class: MagicMock,
    mock_repo_class: MagicMock,
) -> None:
    # Mock DriftDetector (with added dependency)
    mock_drift_detector = MagicMock()
    mock_drift_detector.detect_drift.return_value = {
        "src/api.py": {"added": ["requests"], "removed": []}
    }
    mock_drift_detector_class.return_value = mock_drift_detector

    # Mock Repo & Diffs
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo
    mock_base_commit = MagicMock()
    mock_repo.commit.return_value = mock_base_commit
    
    mock_diff = MagicMock()
    mock_diff.change_type = "M"
    mock_diff.b_path = "src/api.py"
    mock_base_commit.diff.return_value = [mock_diff]

    # Mock DebtEvaluator
    mock_debt_evaluator = MagicMock()
    mock_debt_evaluator.evaluate = AsyncMock(return_value=[
        {"file": "src/api.py", "score": 40}
    ])
    mock_debt_evaluator_class.return_value = mock_debt_evaluator

    gatekeeper = CIGatekeeper()
    with tempfile.TemporaryDirectory() as tmpdir:
        report = await gatekeeper.evaluate_pr(tmpdir, "HEAD~1", "HEAD")
        
        assert report["passed"] is False
        assert report["highest_debt_score"] == 40


@pytest.mark.anyio
@patch("repollama.engines.ci_gatekeeper.Repo")
@patch("repollama.engines.ci_gatekeeper.DriftDetector")
@patch("repollama.engines.ci_gatekeeper.DebtEvaluator")
async def test_evaluate_pr_fail_debt(
    mock_debt_evaluator_class: MagicMock,
    mock_drift_detector_class: MagicMock,
    mock_repo_class: MagicMock,
) -> None:
    # Mock DriftDetector
    mock_drift_detector = MagicMock()
    mock_drift_detector.detect_drift.return_value = {}
    mock_drift_detector_class.return_value = mock_drift_detector

    # Mock Repo & Diffs
    mock_repo = MagicMock()
    mock_repo_class.return_value = mock_repo
    mock_base_commit = MagicMock()
    mock_repo.commit.return_value = mock_base_commit
    
    mock_diff = MagicMock()
    mock_diff.change_type = "M"
    mock_diff.b_path = "src/api.py"
    mock_base_commit.diff.return_value = [mock_diff]

    # Mock DebtEvaluator (with debt score > 80)
    mock_debt_evaluator = MagicMock()
    mock_debt_evaluator.evaluate = AsyncMock(return_value=[
        {"file": "src/api.py", "score": 85}
    ])
    mock_debt_evaluator_class.return_value = mock_debt_evaluator

    gatekeeper = CIGatekeeper()
    with tempfile.TemporaryDirectory() as tmpdir:
        report = await gatekeeper.evaluate_pr(tmpdir, "HEAD~1", "HEAD")
        
        assert report["passed"] is False
        assert report["highest_debt_score"] == 85


@patch("repollama.engines.ci_gatekeeper.CIGatekeeper.evaluate_pr", new_callable=AsyncMock)
def test_cli_ci_check_pass(mock_evaluate_pr: AsyncMock) -> None:
    mock_evaluate_pr.return_value = {
        "passed": True,
        "drift": {},
        "highest_debt_score": 40,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["ci-check", tmpdir])
        assert result.exit_code == 0
        assert "PASS" in result.output
        assert "Highest Debt Score: 40 / 80" in result.output


@patch("repollama.engines.ci_gatekeeper.CIGatekeeper.evaluate_pr", new_callable=AsyncMock)
def test_cli_ci_check_fail(mock_evaluate_pr: AsyncMock) -> None:
    mock_evaluate_pr.return_value = {
        "passed": False,
        "drift": {},
        "highest_debt_score": 85,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["ci-check", tmpdir])
        assert result.exit_code == 1
        assert "FAIL" in result.output
        assert "Highest Debt Score: 85 / 80" in result.output


@patch("repollama.engines.ci_gatekeeper.CIGatekeeper.evaluate_pr", new_callable=AsyncMock)
def test_cli_ci_check_bypass_architect(mock_evaluate_pr: AsyncMock) -> None:
    # Has drift but low debt
    mock_evaluate_pr.return_value = {
        "passed": False,
        "drift": {"src/api.py": {"added": ["requests"], "removed": []}},
        "highest_debt_score": 40,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        # Architect bypasses drift check, so exit code should be 0!
        result = runner.invoke(app, ["ci-check", tmpdir, "--role", "architect"])
        assert result.exit_code == 0
        assert "PASS" in result.output
        assert "Bypassed Drift Check via Architect role" in result.output

        # Developer cannot bypass drift check, so exit code should be 1!
        result_dev = runner.invoke(app, ["ci-check", tmpdir, "--role", "developer"])
        assert result_dev.exit_code == 1
        assert "FAIL" in result_dev.output


def test_cli_init_ci(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init-ci"])
    assert result.exit_code == 0
    assert "Successfully initialized" in result.output
    
    workflow_file = tmp_path / ".github" / "workflows" / "repollama_gate.yml"
    assert workflow_file.exists()
    content = workflow_file.read_text()
    assert "repollama ci-check" in content
