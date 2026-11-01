"""
Quality Certification & Release Report Generator.
Renders evidence-based quality verification reports in Markdown and standalone HTML/PDF.
"""

from __future__ import annotations

import logging
import os

from app.quality.schemas import QualityCertificationReport
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)


def generate_markdown_summary(report: QualityCertificationReport) -> str:
    """Produce structured markdown summary of the quality certification."""
    passed_gates = sum(1 for g in report.gates if g.status.value == "passed")
    total_gates = len(report.gates)

    md = [
        "# AGENTFORGE QUALITY CERTIFICATION REPORT",
        f"**Project ID:** `{report.project_id}`  ",
        f"**Build ID:** `{report.build_id}`  ",
        f"**Date:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        f"**Overall Decision:** **{report.overall_status.value}**  ",
        f"**Quality Score:** **{report.quality_score}/100**  ",
        f"**Gates Passed:** {passed_gates}/{total_gates}  ",
        "",
        "---",
        "## 1. Quality Gates Evaluation",
        "",
        "| # | Gate Name | Status | Evaluated Value | Notes |",
        "|---|-----------|--------|-----------------|-------|",
    ]

    for g in report.gates:
        status_icon = "✅ PASSED" if g.status.value == "passed" else ("⛔ BLOCKED" if g.status.value == "blocked" else "❌ FAILED")
        md.append(f"| {g.gate_number} | {g.gate_name} | {status_icon} | {g.evaluated_value} | {g.reason} |")

    md.extend([
        "",
        "---",
        "## 2. Test Execution Breakdown",
        f"- **Unit Tests:** {report.unit_summary.passed}/{report.unit_summary.total_tests} passed ({report.unit_summary.coverage_percent:.1f}% coverage)",
        f"- **Integration Tests:** {report.integration_summary.passed}/{report.integration_summary.total_scenarios} scenarios passed",
        f"- **API Contracts:** {report.api_summary.passed}/{report.api_summary.total_endpoints} endpoints passed ({report.api_summary.contract_violations} violations)",
        "",
        "---",
        "## 3. Security Breaker Audit",
        f"- **Total Vulnerabilities:** {report.security_summary.total_vulnerabilities}",
        f"- **Critical:** {report.security_summary.critical_count} | **High:** {report.security_summary.high_count} | **Medium:** {report.security_summary.medium_count} | **Low:** {report.security_summary.low_count}",
        f"- **Exposed Secrets:** {report.security_summary.exposed_secrets_count}",
        "",
        "---",
        "## 4. Performance & Scalability",
        f"- **P95 Latency:** {report.performance_metrics.p95_latency_ms} ms",
        f"- **P99 Latency:** {report.performance_metrics.p99_latency_ms} ms",
        f"- **Throughput:** {report.performance_metrics.requests_per_second} req/sec",
        f"- **Max Load Tested:** {len(report.load_test_stages)} stages executed",
    ])

    return "\n".join(md)


def generate_html_report(report: QualityCertificationReport) -> str:
    """Generate standalone dark-mode styled HTML certification report."""
    status_color = "#22C55E" if report.overall_status.value == "APPROVED" else ("#F59E0B" if report.overall_status.value == "CONDITIONALLY_APPROVED" else "#EF4444")
    passed_gates = sum(1 for g in report.gates if g.status.value == "passed")

    gates_rows = ""
    for g in report.gates:
        bg = "#166534" if g.status.value == "passed" else ("#991B1B" if g.status.value == "failed" else "#854D0E")
        gates_rows += f"""
        <tr style="border-bottom: 1px solid #1E293B;">
            <td style="padding: 12px; font-weight: bold; color: #94A3B8;">{g.gate_number}</td>
            <td style="padding: 12px; font-weight: 500; color: #F1F5F9;">{g.gate_name}</td>
            <td style="padding: 12px;"><span style="background: {bg}; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{g.status.value}</span></td>
            <td style="padding: 12px; font-family: monospace; color: #38BDF8;">{g.evaluated_value}</td>
            <td style="padding: 12px; color: #94A3B8; font-size: 13px;">{g.reason}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgentForge Quality Report - {report.project_id}</title>
    <style>
        body {{
            background-color: #080B12;
            color: #E2E8F0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 32px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: #0D1320;
            border: 1px solid #1E293B;
            border-radius: 8px;
            padding: 32px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1E293B;
            padding-bottom: 24px;
            margin-bottom: 24px;
        }}
        .badge {{
            background-color: {status_color};
            color: #000;
            font-weight: 800;
            padding: 8px 16px;
            border-radius: 6px;
            letter-spacing: 0.05em;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }}
        .metric-card {{
            background-color: #111827;
            border: 1px solid #1F2937;
            padding: 16px;
            border-radius: 6px;
        }}
        .metric-card h4 {{ margin: 0 0 8px 0; color: #94A3B8; font-size: 12px; text-transform: uppercase; }}
        .metric-card div {{ font-size: 24px; font-weight: 700; color: #38BDF8; font-family: monospace; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }}
        th {{ text-align: left; padding: 12px; background-color: #111827; color: #94A3B8; font-size: 12px; text-transform: uppercase; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 style="margin: 0; font-size: 22px; color: #F8FAFC;">AgentForge Quality Certification</h1>
                <p style="margin: 4px 0 0 0; color: #64748B; font-size: 13px;">Project: <strong>{report.project_id}</strong> | Build: {report.build_id}</p>
            </div>
            <div class="badge">{report.overall_status.value}</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <h4>Quality Score</h4>
                <div>{report.quality_score}/100</div>
            </div>
            <div class="metric-card">
                <h4>Gates Passed</h4>
                <div>{passed_gates}/{len(report.gates)}</div>
            </div>
            <div class="metric-card">
                <h4>Unit Coverage</h4>
                <div>{report.unit_summary.coverage_percent:.1f}%</div>
            </div>
            <div class="metric-card">
                <h4>P95 Latency</h4>
                <div>{report.performance_metrics.p95_latency_ms} ms</div>
            </div>
        </div>

        <h3 style="color: #F8FAFC; margin-bottom: 8px;">10 Evidence-Based Quality Gates</h3>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Gate Name</th>
                    <th>Status</th>
                    <th>Evaluated Result</th>
                    <th>Evidence / Reason</th>
                </tr>
            </thead>
            <tbody>
                {gates_rows}
            </tbody>
        </table>

        <div style="margin-top: 32px; border-top: 1px solid #1E293B; padding-top: 16px; display: flex; justify-content: space-between; font-size: 12px; color: #64748B;">
            <div>Generated by AgentForge Quality Engineering System</div>
            <div>{report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
        </div>
    </div>
</body>
</html>"""


class ReportGenerator:
    """
    Renders and stores formal product quality reports in project workspace.
    """

    def __init__(self) -> None:
        self.workspace = get_workspace_service()

    def generate_and_save_reports(
        self,
        report: QualityCertificationReport,
    ) -> tuple[str, str | None]:
        """
        Produce HTML and optional PDF, save to project workspace under .agentforge/quality_reports/.
        Returns relative paths: (html_rel_path, pdf_rel_path)
        """
        html_content = generate_html_report(report)
        md_summary = generate_markdown_summary(report)
        report.summary_markdown = md_summary

        report_dir = ".agentforge/quality_reports"
        html_file = f"{report_dir}/{report.build_id}.html"
        self.workspace.write_file(report.project_id, html_file, html_content)

        pdf_file: str | None = None
        # Attempt PDF generation if weasyprint is installed
        try:
            import weasyprint  # type: ignore[import-untyped]

            abs_project_path = self.workspace.get_project_path(report.project_id)
            abs_pdf_dir = os.path.join(abs_project_path, ".agentforge", "quality_reports")
            os.makedirs(abs_pdf_dir, exist_ok=True)
            abs_pdf_path = os.path.join(abs_pdf_dir, f"{report.build_id}.pdf")
            weasyprint.HTML(string=html_content).write_pdf(abs_pdf_path)
            pdf_file = f"{report_dir}/{report.build_id}.pdf"
            logger.info("Generated PDF quality report at %s", pdf_file)
        except ImportError:
            logger.debug("weasyprint not installed; skipped PDF generation.")
        except Exception as exc:
            logger.warning("Failed generating PDF report: %s", exc)

        report.html_report_path = html_file
        report.pdf_report_path = pdf_file

        return html_file, pdf_file
