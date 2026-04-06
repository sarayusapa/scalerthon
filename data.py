"""
Synthetic bug report dataset for the Nexus Platform — a fictional data analytics SaaS.

Issues span 4 severity levels and include duplicate groups for medium/hard tasks.
All ground-truth answers (severity, duplicate sets, expected labels, response keywords)
are embedded here so graders are fully deterministic.
"""

from typing import Dict, List, Any

# ── SEVERITY ordering (for partial-credit distance scoring) ───────────────────
SEVERITY_ORDER = ["critical", "high", "medium", "low"]

# ── AVAILABLE LABELS ──────────────────────────────────────────────────────────
AVAILABLE_LABELS = [
    "bug", "security", "data-loss", "performance", "ui", "ux",
    "api", "authentication", "database", "memory-leak", "crash",
    "export", "notifications", "mobile", "documentation", "enhancement",
    "duplicate", "wontfix", "needs-investigation", "regression",
    "file-upload", "dashboard", "reporting", "billing", "integrations",
]

# ── CORE ISSUE BANK ───────────────────────────────────────────────────────────
# Each issue has ground-truth severity and labels for grading.

ISSUE_BANK: Dict[str, Dict[str, Any]] = {
    # ── CRITICAL ──────────────────────────────────────────────────────────────
    "NX-001": {
        "id": "NX-001",
        "title": "SQL injection vulnerability in report search API",
        "description": (
            "The `/api/reports/search?q=` endpoint does not sanitize user input. "
            "Passing `' OR '1'='1` returns all reports regardless of user permissions. "
            "A malicious actor can exfiltrate the entire reports database without authentication."
        ),
        "reporter": "security_researcher_ext",
        "created_at": "2024-03-01",
        "component": "api",
        "reproduction_steps": "curl \"https://app.nexus.io/api/reports/search?q=' OR '1'='1\"",
        "environment_info": "All environments (prod confirmed)",
        "severity": "critical",
        "labels": ["bug", "security", "api"],
    },
    "NX-002": {
        "id": "NX-002",
        "title": "Production data corrupted after v3.2 schema migration",
        "description": (
            "After running the v3.2 database migration on 2024-02-28, approximately 12,000 rows "
            "in the `pipeline_runs` table have NULL values in the `completed_at` column where "
            "valid timestamps previously existed. Affected customers report incorrect billing "
            "calculations and missing audit logs."
        ),
        "reporter": "ops_team",
        "created_at": "2024-02-28",
        "component": "database",
        "reproduction_steps": "SELECT COUNT(*) FROM pipeline_runs WHERE completed_at IS NULL AND created_at < '2024-02-28'",
        "environment_info": "Production only",
        "severity": "critical",
        "labels": ["bug", "data-loss", "database", "regression"],
    },
    "NX-003": {
        "id": "NX-003",
        "title": "JWT tokens from deleted accounts still grant API access",
        "description": (
            "When an admin deletes a user account, their existing JWT tokens remain valid until "
            "natural expiry (24h). A terminated employee can continue accessing all company data "
            "via the API for up to 24 hours after account deletion. Token revocation is not implemented."
        ),
        "reporter": "cto_internal",
        "created_at": "2024-03-05",
        "component": "authentication",
        "reproduction_steps": "1. Create user. 2. Obtain JWT. 3. Delete user via admin panel. 4. Use old JWT — still works.",
        "environment_info": "All environments",
        "severity": "critical",
        "labels": ["bug", "security", "authentication"],
    },
    "NX-004": {
        "id": "NX-004",
        "title": "Scheduled exports silently drop rows when queue exceeds 10k jobs",
        "description": (
            "During peak hours, when the export queue depth exceeds 10,000 jobs, the worker "
            "process silently discards rows from CSV exports to stay within a hardcoded memory "
            "cap. Customers receive 'successful' export emails with incomplete data. No error is logged."
        ),
        "reporter": "enterprise_customer_A",
        "created_at": "2024-03-10",
        "component": "export",
        "reproduction_steps": "Trigger 10,001 concurrent export jobs; inspect row counts in output CSVs.",
        "environment_info": "Production (observed on first Monday of every month)",
        "severity": "critical",
        "labels": ["bug", "data-loss", "export"],
    },

    # ── HIGH ──────────────────────────────────────────────────────────────────
    "NX-010": {
        "id": "NX-010",
        "title": "Application crashes (OOM) when uploading CSV files larger than 500 MB",
        "description": (
            "Uploading any CSV file larger than approximately 500 MB via the web UI causes the "
            "application server to throw an OutOfMemoryError and crash. The upload appears to "
            "buffer the entire file in memory before processing. Server restarts automatically "
            "but the upload is lost and the user receives a generic 502 error."
        ),
        "reporter": "data_team_lead",
        "created_at": "2024-02-10",
        "component": "file-upload",
        "reproduction_steps": "Upload a 600 MB CSV. Observe server log: java.lang.OutOfMemoryError: Java heap space",
        "environment_info": "All environments, JVM heap set to 2GB",
        "severity": "high",
        "labels": ["bug", "crash", "file-upload", "memory-leak"],
    },
    "NX-011": {
        "id": "NX-011",
        "title": "Memory usage grows unbounded in streaming pipeline connector",
        "description": (
            "The Kafka streaming connector leaks memory at approximately 50 MB/hour when "
            "processing high-throughput topics (>100k msgs/sec). After ~8 hours of operation "
            "the pod is OOMKilled. Heapdump analysis points to message offset cache not being "
            "evicted. Requires daily pod restarts as a workaround."
        ),
        "reporter": "platform_engineer",
        "created_at": "2024-02-15",
        "component": "integrations",
        "reproduction_steps": "Run Kafka connector for 8h at >100k msg/sec throughput and monitor RSS.",
        "environment_info": "Kubernetes, all cloud providers",
        "severity": "high",
        "labels": ["bug", "memory-leak", "integrations", "performance"],
    },
    "NX-012": {
        "id": "NX-012",
        "title": "Dashboard chart widgets fail to render for datasets > 1M rows",
        "description": (
            "When a dashboard is connected to a dataset with more than 1 million rows, all "
            "chart widgets display a spinner indefinitely. The browser console shows: "
            "'RangeError: Maximum call stack size exceeded' in chart-renderer.js. "
            "Smaller datasets work fine. This affects ~30% of enterprise customers."
        ),
        "reporter": "product_team",
        "created_at": "2024-02-20",
        "component": "dashboard",
        "reproduction_steps": "Connect any chart widget to a table with >1M rows.",
        "environment_info": "Chrome 121, Firefox 122, Safari 17 — all affected",
        "severity": "high",
        "labels": ["bug", "dashboard", "ui", "performance"],
    },
    "NX-013": {
        "id": "NX-013",
        "title": "Critical alert email notifications not being delivered",
        "description": (
            "Since the SendGrid API key rotation on 2024-02-25, email notifications for "
            "CRITICAL severity pipeline alerts are not being sent. The notification service "
            "logs show 401 Unauthorized errors from SendGrid but silently swallows them "
            "rather than retrying or alerting ops. Customers are missing SLA breach warnings."
        ),
        "reporter": "sre_team",
        "created_at": "2024-02-26",
        "component": "notifications",
        "reproduction_steps": "Trigger a critical pipeline alert; check email — nothing arrives. Check logs for SendGrid 401.",
        "environment_info": "Production only",
        "severity": "high",
        "labels": ["bug", "notifications", "api", "regression"],
    },
    "NX-014": {
        "id": "NX-014",
        "title": "Billing calculation incorrect for pro-rated mid-cycle plan upgrades",
        "description": (
            "When a customer upgrades from Starter to Pro mid-billing-cycle, the system "
            "charges the full Pro price instead of the pro-rated amount. Approximately "
            "230 customers were overcharged in February. Finance has already processed "
            "manual refunds but the bug is still present."
        ),
        "reporter": "billing_team",
        "created_at": "2024-03-02",
        "component": "billing",
        "reproduction_steps": "Upgrade plan on day 15 of a 30-day cycle; inspect next invoice.",
        "environment_info": "Production only",
        "severity": "high",
        "labels": ["bug", "billing", "regression"],
    },

    # ── MEDIUM ────────────────────────────────────────────────────────────────
    "NX-020": {
        "id": "NX-020",
        "title": "Filtered report queries are 10-40x slower after index rebuild",
        "description": (
            "After the maintenance window on 2024-02-18, queries that filter reports by "
            "date range are 10-40x slower (2s → 45s for typical queries). "
            "EXPLAIN ANALYZE shows a seq scan despite the index existing. "
            "A workaround is to run ANALYZE on the affected table manually."
        ),
        "reporter": "backend_dev",
        "created_at": "2024-02-19",
        "component": "database",
        "reproduction_steps": "SELECT * FROM reports WHERE created_at BETWEEN '2024-01-01' AND '2024-02-01' — observe query time.",
        "environment_info": "PostgreSQL 15.2, production",
        "severity": "medium",
        "labels": ["bug", "database", "performance", "regression"],
    },
    "NX-021": {
        "id": "NX-021",
        "title": "Date picker shows incorrect UTC offset for IST (Indian Standard Time) users",
        "description": (
            "Users with their timezone set to IST (UTC+5:30) see the date picker "
            "displaying UTC+5:00 instead of the correct UTC+5:30. This causes scheduled "
            "pipelines to run 30 minutes earlier than configured. Workaround: set timezone "
            "to 'Kolkata' explicitly."
        ),
        "reporter": "customer_support",
        "created_at": "2024-02-22",
        "component": "ui",
        "reproduction_steps": "Set account timezone to IST; create a scheduled pipeline; observe execution time offset.",
        "environment_info": "All browsers, all OSes",
        "severity": "medium",
        "labels": ["bug", "ui", "ux"],
    },
    "NX-022": {
        "id": "NX-022",
        "title": "Export to PDF button missing on mobile devices",
        "description": (
            "The 'Export to PDF' button in the report toolbar is not visible on mobile "
            "viewports (< 768px). The button is present in the DOM but has display:none "
            "applied via a media query with no alternative access path. Mobile users "
            "cannot export reports."
        ),
        "reporter": "mobile_user_feedback",
        "created_at": "2024-02-25",
        "component": "ui",
        "reproduction_steps": "Open any report on a mobile device or resize browser to < 768px; toolbar missing PDF export.",
        "environment_info": "iOS Safari, Android Chrome",
        "severity": "medium",
        "labels": ["bug", "mobile", "ui", "export"],
    },
    "NX-023": {
        "id": "NX-023",
        "title": "Live search results don't update until full page reload",
        "description": (
            "The global search bar (Cmd+K) shows stale results after new content is added. "
            "Search index is only refreshed on full page reload. If a user creates a new "
            "dashboard and immediately searches for it, it won't appear. Refreshing fixes it."
        ),
        "reporter": "power_user",
        "created_at": "2024-03-01",
        "component": "ui",
        "reproduction_steps": "Create a new dashboard; immediately Cmd+K search for it — not found. Reload page; search again — found.",
        "environment_info": "All browsers",
        "severity": "medium",
        "labels": ["bug", "ui", "ux"],
    },
    "NX-024": {
        "id": "NX-024",
        "title": "Bulk delete confirmation modal does not close after action completes",
        "description": (
            "After confirming a bulk delete in the data source manager, the confirmation "
            "modal remains open even though the deletion succeeded. The user must manually "
            "close it. This is a minor UX annoyance but has caused some users to attempt "
            "the deletion twice, leading to a 'not found' error."
        ),
        "reporter": "qa_team",
        "created_at": "2024-03-03",
        "component": "ui",
        "reproduction_steps": "Select 3+ data sources; click Bulk Delete; confirm; observe modal stays open.",
        "environment_info": "Chrome 121",
        "severity": "medium",
        "labels": ["bug", "ui", "ux"],
    },
    "NX-025": {
        "id": "NX-025",
        "title": "API rate limit headers missing on 429 responses",
        "description": (
            "When the API returns a 429 Too Many Requests response, the standard "
            "Retry-After and X-RateLimit-* headers are absent. This forces client "
            "developers to implement fixed backoff instead of respecting server-side "
            "rate limit windows, resulting in thundering herd on resumption."
        ),
        "reporter": "api_integrations_partner",
        "created_at": "2024-03-07",
        "component": "api",
        "reproduction_steps": "Exceed API rate limit; inspect response headers — Retry-After missing.",
        "environment_info": "All environments",
        "severity": "medium",
        "labels": ["bug", "api"],
    },

    # ── LOW ───────────────────────────────────────────────────────────────────
    "NX-030": {
        "id": "NX-030",
        "title": "Typo: 'occured' should be 'occurred' in pipeline error message",
        "description": "Error message reads: 'An unexpected error has occured. Please try again.' — 'occured' is misspelled.",
        "reporter": "attentive_user",
        "created_at": "2024-03-08",
        "component": "ui",
        "reproduction_steps": "Trigger a pipeline failure; observe error toast.",
        "environment_info": "All environments",
        "severity": "low",
        "labels": ["bug", "ui", "documentation"],
    },
    "NX-031": {
        "id": "NX-031",
        "title": "Footer links open in same tab instead of new tab",
        "description": "All links in the footer (Privacy Policy, Terms of Service, Status Page) open in the same browser tab rather than a new tab, interrupting the user's workflow.",
        "reporter": "ux_reviewer",
        "created_at": "2024-03-09",
        "component": "ui",
        "reproduction_steps": "Click any footer link; observe it opens in same tab.",
        "environment_info": "All browsers",
        "severity": "low",
        "labels": ["bug", "ui", "ux"],
    },
    "NX-032": {
        "id": "NX-032",
        "title": "Dark mode: settings panel header uses wrong background color",
        "description": (
            "In dark mode, the settings panel header retains a light grey (#F5F5F5) background "
            "instead of using the dark theme token (#1E1E1E). All other panels are correctly themed."
        ),
        "reporter": "design_team",
        "created_at": "2024-03-10",
        "component": "ui",
        "reproduction_steps": "Enable dark mode; open Settings; observe header background inconsistency.",
        "environment_info": "All browsers",
        "severity": "low",
        "labels": ["bug", "ui"],
    },
    "NX-033": {
        "id": "NX-033",
        "title": "Tooltip delay is 1500ms — should be 300ms per design spec",
        "description": "All UI tooltips have a 1500ms hover delay. The design system spec defines 300ms. This makes the UI feel sluggish.",
        "reporter": "design_system_team",
        "created_at": "2024-03-11",
        "component": "ui",
        "reproduction_steps": "Hover over any button with a tooltip; time the delay.",
        "environment_info": "All environments",
        "severity": "low",
        "labels": ["bug", "ui", "ux"],
    },

    # ── DUPLICATE GROUP A: Large file OOM (same root as NX-010) ───────────────
    "NX-040": {
        "id": "NX-040",
        "title": "Server 502 error when importing large datasets",
        "description": (
            "Every time I try to import my dataset (it's about 700 MB), I get a 502 Bad "
            "Gateway error after about 30 seconds. The import dialog says it's processing "
            "but then just fails with no useful message. Smaller files (under 200 MB) work fine."
        ),
        "reporter": "analyst_user_1",
        "created_at": "2024-02-12",
        "component": "file-upload",
        "reproduction_steps": "Upload a file > 500 MB via the Import Data dialog.",
        "environment_info": "Chrome 121, MacOS 14",
        "severity": "high",
        "labels": ["bug", "crash", "file-upload"],
    },
    "NX-041": {
        "id": "NX-041",
        "title": "Nexus crashes when I upload my Q4 sales data",
        "description": (
            "I have a CSV file with Q4 sales data, about 650 MB. Every single time I try to "
            "upload it the whole app goes down for a few minutes. I see 'Service Unavailable' "
            "in the browser. This is urgent — I need this data loaded for a board presentation tomorrow."
        ),
        "reporter": "sales_director",
        "created_at": "2024-02-14",
        "component": "file-upload",
        "reproduction_steps": "Upload any CSV >= 600MB.",
        "environment_info": "Safari 17, MacOS 14.2",
        "severity": "high",
        "labels": ["bug", "crash", "file-upload"],
    },

    # ── DUPLICATE GROUP B: Kafka memory leak (same root as NX-011) ────────────
    "NX-042": {
        "id": "NX-042",
        "title": "Kafka connector pod gets OOMKilled nightly",
        "description": (
            "Our Kafka connector pod is being killed every night with OOMKilled status in "
            "Kubernetes. We have to restart it every morning. Memory monitoring shows it "
            "steadily grows from ~200 MB at startup to over 2 GB over 8-10 hours. "
            "Topic is running at about 80k messages/sec."
        ),
        "reporter": "devops_lead",
        "created_at": "2024-02-17",
        "component": "integrations",
        "reproduction_steps": "Deploy Kafka connector; monitor memory with kubectl top pod for 8+ hours.",
        "environment_info": "GKE 1.28, k8s OOMKill",
        "severity": "high",
        "labels": ["bug", "memory-leak", "integrations"],
    },
    "NX-043": {
        "id": "NX-043",
        "title": "Stream connector memory keeps growing — possible leak in offset cache",
        "description": (
            "I've been profiling our streaming connector and noticed that the offset tracking "
            "cache never gets cleared. The HashMap holding message offsets just keeps growing "
            "indefinitely. After a thread dump at hour 9, the cache had over 4 million entries. "
            "This seems to be the root cause of the pod OOM issue others have reported."
        ),
        "reporter": "senior_engineer",
        "created_at": "2024-02-19",
        "component": "integrations",
        "reproduction_steps": "Attach a profiler to the connector process; inspect KafkaOffsetCache size over time.",
        "environment_info": "All environments",
        "severity": "high",
        "labels": ["bug", "memory-leak", "integrations", "needs-investigation"],
    },

    # ── DUPLICATE GROUP C: Dashboard chart rendering (same root as NX-012) ────
    "NX-044": {
        "id": "NX-044",
        "title": "Charts just spin forever on our main analytics dashboard",
        "description": (
            "Since upgrading to the Business plan and connecting our full dataset, "
            "every chart on our main analytics dashboard just shows a loading spinner. "
            "We waited 20 minutes and they never loaded. The dataset has about 1.2 million rows. "
            "Dashboard worked fine when we were on the Starter plan with a smaller dataset sample."
        ),
        "reporter": "biz_analyst",
        "created_at": "2024-02-22",
        "component": "dashboard",
        "reproduction_steps": "Connect dashboard to a dataset with > 1M rows; open dashboard.",
        "environment_info": "Chrome 121, Windows 11",
        "severity": "high",
        "labels": ["bug", "dashboard", "ui"],
    },
}


# ── TASK SCENARIOS ─────────────────────────────────────────────────────────────
#
# TASK 1 — bug_classify:  Agent sees ONE issue, must call classify(severity).
# TASK 2 — duplicate_detection: Agent sees new_issue + backlog; must find duplicates.
# TASK 3 — full_triage: Agent must classify + find dupes + draft response + assign labels.

BUG_CLASSIFY_SCENARIOS = [
    # (issue_id, correct_severity)
    {"issue_id": "NX-001", "correct_severity": "critical"},
    {"issue_id": "NX-003", "correct_severity": "critical"},
    {"issue_id": "NX-010", "correct_severity": "high"},
    {"issue_id": "NX-012", "correct_severity": "high"},
    {"issue_id": "NX-013", "correct_severity": "high"},
    {"issue_id": "NX-014", "correct_severity": "high"},
    {"issue_id": "NX-020", "correct_severity": "medium"},
    {"issue_id": "NX-021", "correct_severity": "medium"},
    {"issue_id": "NX-022", "correct_severity": "medium"},
    {"issue_id": "NX-030", "correct_severity": "low"},
    {"issue_id": "NX-031", "correct_severity": "low"},
    {"issue_id": "NX-032", "correct_severity": "low"},
]

DUPLICATE_DETECTION_SCENARIOS = [
    {
        "new_issue_id": "NX-040",   # Large file upload crash (duplicate of NX-010)
        "backlog_ids": [
            "NX-001", "NX-011", "NX-010", "NX-020",
            "NX-041", "NX-022", "NX-030", "NX-044",
        ],
        "actual_duplicates": ["NX-010", "NX-041"],  # NX-040 dupes these two
    },
    {
        "new_issue_id": "NX-042",   # Kafka OOM (duplicate of NX-011)
        "backlog_ids": [
            "NX-010", "NX-043", "NX-011", "NX-020",
            "NX-012", "NX-031", "NX-001", "NX-023",
        ],
        "actual_duplicates": ["NX-011", "NX-043"],  # NX-042 dupes these two
    },
    {
        "new_issue_id": "NX-044",   # Dashboard infinite spinner (duplicate of NX-012)
        "backlog_ids": [
            "NX-011", "NX-020", "NX-012", "NX-021",
            "NX-040", "NX-001", "NX-033", "NX-013",
        ],
        "actual_duplicates": ["NX-012"],  # NX-044 dupes only NX-012
    },
]

FULL_TRIAGE_SCENARIOS = [
    {
        "issue_id": "NX-043",
        "correct_severity": "high",
        "backlog_ids": [
            "NX-010", "NX-042", "NX-011", "NX-020",
            "NX-012", "NX-031", "NX-001", "NX-023",
        ],
        "actual_duplicates": ["NX-011", "NX-042"],  # NX-043 dupes these
        "expected_labels": ["bug", "memory-leak", "integrations", "needs-investigation"],
        "response_quality_keywords": ["investigate", "memory", "offset", "cache", "profil", "leak", "thank"],
        "description": (
            "Hard: agent must correctly classify a nuanced high-severity issue, "
            "identify two non-obvious duplicates described with different terminology, "
            "draft a technically accurate response, and assign domain-specific labels."
        ),
    },
    {
        "issue_id": "NX-041",
        "correct_severity": "high",
        "backlog_ids": [
            "NX-010", "NX-011", "NX-040", "NX-020",
            "NX-012", "NX-022", "NX-030", "NX-001",
        ],
        "actual_duplicates": ["NX-010", "NX-040"],
        "expected_labels": ["bug", "crash", "file-upload"],
        "response_quality_keywords": ["upload", "file", "size", "memory", "workaround", "investigating", "thank"],
        "description": (
            "Hard: large-file crash with two stylistically different duplicate reports."
        ),
    },
]
