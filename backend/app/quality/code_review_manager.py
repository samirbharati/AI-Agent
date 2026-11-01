"""
Independent Code Quality & Architectural Reviewer.
Analyzes code maintainability, SOLID patterns, complexity, error handling,
anti-patterns, and architectural standards independently from the Developer Agent.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field

from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)


@dataclass
class ReviewFinding:
    rule_id: str
    severity: str  # blocker, major, minor, suggestion
    file_path: str
    line_number: int | None
    message: str
    suggested_fix: str | None = None


@dataclass
class CodeReviewResult:
    is_approved: bool
    score: int  # 0 to 100
    summary: str
    blockers_count: int
    majors_count: int
    minors_count: int
    findings: list[ReviewFinding] = field(default_factory=list)


class ASTCodeVisitor(ast.NodeVisitor):
    """Inspects Python AST for architectural anti-patterns."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.findings: list[ReviewFinding] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        # Check function length
        lines = (node.end_lineno or node.lineno) - node.lineno
        if lines > 80:
            self.findings.append(
                ReviewFinding(
                    rule_id="ARCH-001",
                    severity="minor",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    message=f"Function '{node.name}' is too long ({lines} lines > 80). Consider refactoring into smaller helpers.",
                    suggested_fix="Extract subroutines to adhere to Single Responsibility Principle.",
                )
            )

        # Check for missing return type annotation
        if not node.name.startswith("_") and node.returns is None:
            self.findings.append(
                ReviewFinding(
                    rule_id="TYPE-001",
                    severity="minor",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    message=f"Public function '{node.name}' lacks return type annotation.",
                    suggested_fix="Add -> None or explicit return type annotation.",
                )
            )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:  # noqa: N802
        # Bare except: except: or except BaseException:
        if node.type is None:
            self.findings.append(
                ReviewFinding(
                    rule_id="ERR-001",
                    severity="major",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    message="Bare 'except:' caught. Silences unexpected exceptions and interrupts.",
                    suggested_fix="Catch specific Exception subclasses or 'except Exception:'.",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # Detect leftover print statements in production code
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.findings.append(
                ReviewFinding(
                    rule_id="LOG-001",
                    severity="suggestion",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    message="Direct 'print()' statement detected in application code. Use logging instead.",
                    suggested_fix="Replace with logger.debug() or logger.info().",
                )
            )
        self.generic_visit(node)


class CodeReviewManager:
    """
    Coordinates static code analysis and structural review across workspace files.
    """

    def __init__(self) -> None:
        self.workspace = get_workspace_service()

    def review_project(self, project_id: str) -> CodeReviewResult:
        """
        Perform deterministic architectural code review on project workspace files.
        """
        all_findings: list[ReviewFinding] = []
        files = self.workspace.list_files(project_id)
        scanned_files = 0

        for f in files:
            if not f.path.endswith(".py"):
                continue
            if ".venv" in f.path or "site-packages" in f.path:
                continue

            try:
                content = self.workspace.read_file(project_id, f.path)
                tree = ast.parse(content, filename=f.path)
                scanned_files += 1
                visitor = ASTCodeVisitor(f.path)
                visitor.visit(tree)
                all_findings.extend(visitor.findings)
            except SyntaxError as exc:
                all_findings.append(
                    ReviewFinding(
                        rule_id="SYN-001",
                        severity="blocker",
                        file_path=f.path,
                        line_number=exc.lineno,
                        message=f"Syntax error in code: {exc.msg}",
                        suggested_fix="Fix syntax error to allow compilation.",
                    )
                )
            except Exception as exc:
                logger.debug("Failed AST review for %s: %s", f.path, exc)

        blockers = sum(1 for f in all_findings if f.severity == "blocker")
        majors = sum(1 for f in all_findings if f.severity == "major")
        minors = sum(1 for f in all_findings if f.severity == "minor")

        # Score calculation: base 100, -25 per blocker, -10 per major, -2 per minor
        penalty = (blockers * 25) + (majors * 10) + (minors * 2)
        score = max(0, min(100, 100 - penalty))

        is_approved = blockers == 0 and majors <= 2 and score >= 75

        summary = (
            f"Code Review: {scanned_files} files reviewed. Found {blockers} blockers, "
            f"{majors} majors, {minors} minors. Quality Score: {score}/100."
        )

        return CodeReviewResult(
            is_approved=is_approved,
            score=score,
            summary=summary,
            blockers_count=blockers,
            majors_count=majors,
            minors_count=minors,
            findings=all_findings,
        )
