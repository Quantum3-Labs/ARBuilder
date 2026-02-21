#!/usr/bin/env python3
"""
Source Maintenance Pipeline for ARBuilder.

Four maintenance operations:
  A. SDK Monitor     — Check crates.io/npm for new SDK releases, flag outdated repos
  B. Discover Repos  — Search GitHub for new community projects using Stylus/Arbitrum SDK
  C. Health Check    — Re-verify all config repos, flag broken/deprecated
  D. Remediate       — Auto-remove critical (archived/deleted) repos from config

Usage:
    # Check for SDK version updates
    python scripts/maintain_sources.py monitor

    # Discover new community repos
    python scripts/maintain_sources.py discover

    # Run health check on all configured repos
    python scripts/maintain_sources.py health

    # Auto-remove archived/deleted repos from config
    python scripts/maintain_sources.py remediate

    # Run all maintenance tasks (monitor + discover + health)
    python scripts/maintain_sources.py all

    # Output JSON report
    python scripts/maintain_sources.py all --output reports/maintenance.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from scraper.config import (  # noqa: E402
    MAIN_STYLUS_SDK_VERSION,
    MIN_STYLUS_SDK_VERSION,
    get_all_config_repo_urls,
    get_config_repo_info,
)
from scraper.version_extractor import (  # noqa: E402
    compare_versions,
    get_latest_sdk_version_sync,
)

load_dotenv()

console = Console()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"
NPM_REGISTRY = "https://registry.npmjs.org"
CRATES_IO_API = "https://crates.io/api/v1/crates"


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ARBuilder/1.0"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


# ──────────────────────────────────────────────────────────────
# A. SDK VERSION MONITOR
# ──────────────────────────────────────────────────────────────


def monitor_sdk_versions() -> dict:
    """Check crates.io and npm for latest SDK versions, compare to config."""
    console.print("\n[bold blue]═══ SDK Version Monitor ═══[/bold blue]")
    results = {"stylus_sdk": {}, "arbitrum_sdk": {}, "outdated_repos": []}

    # Check stylus-sdk on crates.io
    console.print("[blue]Checking crates.io for stylus-sdk...[/blue]")
    latest_stylus = get_latest_sdk_version_sync()
    if latest_stylus:
        results["stylus_sdk"] = {
            "latest": latest_stylus,
            "config_main": MAIN_STYLUS_SDK_VERSION,
            "config_min": MIN_STYLUS_SDK_VERSION,
            "config_up_to_date": compare_versions(MAIN_STYLUS_SDK_VERSION, latest_stylus) >= 0,
        }
        if compare_versions(latest_stylus, MAIN_STYLUS_SDK_VERSION) > 0:
            console.print(
                f"[yellow]WARNING: New stylus-sdk {latest_stylus} available "
                f"(config has {MAIN_STYLUS_SDK_VERSION})[/yellow]"
            )
        else:
            console.print(f"[green]stylus-sdk {latest_stylus} — config is current[/green]")

    # Check @arbitrum/sdk on npm
    console.print("[blue]Checking npm for @arbitrum/sdk...[/blue]")
    latest_arb_sdk = _check_npm_version("@arbitrum/sdk")
    if latest_arb_sdk:
        results["arbitrum_sdk"] = {"latest": latest_arb_sdk}
        console.print(f"[green]@arbitrum/sdk latest: {latest_arb_sdk}[/green]")

    # Check each configured repo against latest
    config_info = get_config_repo_info()
    for url, info in config_info.items():
        sdk_ver = info.get("sdk_version", "")
        if not sdk_ver or sdk_ver == "N/A":
            continue

        repo_name = url.split("/")[-2] + "/" + url.split("/")[-1]

        # Stylus repos
        if info["category"] == "stylus" and latest_stylus:
            if compare_versions(sdk_ver, latest_stylus) < 0:
                behind = _version_distance(sdk_ver, latest_stylus)
                entry = {
                    "repo": repo_name,
                    "url": url,
                    "current_version": sdk_ver,
                    "latest_version": latest_stylus,
                    "sdk_type": "stylus-sdk",
                    "behind": behind,
                }
                results["outdated_repos"].append(entry)
                console.print(
                    f"[yellow]  {repo_name}: {sdk_ver} → {latest_stylus} ({behind})[/yellow]"
                )

        # Arbitrum SDK repos
        if info["category"] in ("arbitrum_sdk", "orbit_sdk") and latest_arb_sdk:
            if compare_versions(sdk_ver, latest_arb_sdk) < 0:
                behind = _version_distance(sdk_ver, latest_arb_sdk)
                entry = {
                    "repo": repo_name,
                    "url": url,
                    "current_version": sdk_ver,
                    "latest_version": latest_arb_sdk,
                    "sdk_type": "@arbitrum/sdk",
                    "behind": behind,
                }
                results["outdated_repos"].append(entry)
                console.print(
                    f"[yellow]  {repo_name}: {sdk_ver} → {latest_arb_sdk} ({behind})[/yellow]"
                )

    if not results["outdated_repos"]:
        console.print("[green]All repos are up to date with latest SDK versions.[/green]")

    return results


def _check_npm_version(package: str) -> Optional[str]:
    """Get latest version of an npm package."""
    try:
        # URL-encode scoped packages
        encoded = package.replace("/", "%2F")
        with httpx.Client() as client:
            resp = client.get(
                f"{NPM_REGISTRY}/{encoded}",
                headers={"User-Agent": "ARBuilder/1.0"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("dist-tags", {}).get("latest")
    except Exception as e:
        console.print(f"[red]Failed to check npm for {package}: {e}[/red]")
        return None


def _version_distance(current: str, latest: str) -> str:
    """Human-readable description of how far behind a version is."""
    try:
        c = current.lstrip("^~>=<").split(".")
        lat = latest.lstrip("^~>=<").split(".")
        c_major, c_minor, c_patch = int(c[0]), int(c[1]), int(c[2]) if len(c) > 2 else 0
        l_major, l_minor, l_patch = int(lat[0]), int(lat[1]), int(lat[2]) if len(lat) > 2 else 0

        if c_major != l_major:
            return f"{l_major - c_major} major version(s) behind"
        if c_minor != l_minor:
            return f"{l_minor - c_minor} minor version(s) behind"
        return f"{l_patch - c_patch} patch version(s) behind"
    except (ValueError, IndexError):
        return "unknown distance"


# ──────────────────────────────────────────────────────────────
# B. REPO DISCOVERY
# ──────────────────────────────────────────────────────────────

DISCOVERY_QUERIES = [
    # Stylus repos
    {"q": "stylus-sdk language:Rust", "label": "Stylus (Rust)"},
    {"q": "stylus-sdk in:file filename:Cargo.toml", "label": "Stylus (Cargo.toml)"},
    # Arbitrum SDK repos
    {"q": "arbitrum/sdk language:TypeScript", "label": "Arbitrum SDK (TS)"},
    {"q": "arbitrum-sdk in:file filename:package.json", "label": "Arbitrum SDK (package.json)"},
    # Scaffold-stylus forks
    {"q": "scaffold-stylus in:name", "label": "Scaffold Stylus forks"},
]


def discover_repos(min_stars: int = 1) -> dict:
    """Search GitHub for new repos using Stylus/Arbitrum SDK."""
    console.print("\n[bold blue]═══ Repo Discovery ═══[/bold blue]")
    known_urls = get_all_config_repo_urls()
    # Normalize known URLs for comparison
    known_normalized = {_normalize_url(u) for u in known_urls}

    candidates = {}
    results = {"candidates": [], "already_known": 0, "total_searched": 0}

    for query_info in DISCOVERY_QUERIES:
        query = query_info["q"]
        label = query_info["label"]
        console.print(f"\n[blue]Searching: {label}[/blue]")

        repos = _github_search_repos(query, min_stars=min_stars)
        results["total_searched"] += len(repos)

        for repo in repos:
            url = repo["html_url"]
            norm_url = _normalize_url(url)
            if norm_url in known_normalized:
                results["already_known"] += 1
                continue
            if norm_url in candidates:
                continue  # Dedup across queries

            candidates[norm_url] = {
                "url": url,
                "name": repo["full_name"],
                "description": repo.get("description", "") or "",
                "stars": repo["stargazers_count"],
                "updated_at": repo["updated_at"],
                "language": repo.get("language", ""),
                "archived": repo.get("archived", False),
                "found_via": label,
            }

    # Sort by stars descending
    sorted_candidates = sorted(candidates.values(), key=lambda x: x["stars"], reverse=True)

    # Filter out archived repos
    active_candidates = [c for c in sorted_candidates if not c["archived"]]

    results["candidates"] = active_candidates

    # Print results
    if active_candidates:
        table = Table(title="New Candidate Repos")
        table.add_column("Repo", style="cyan")
        table.add_column("Stars", justify="right")
        table.add_column("Language")
        table.add_column("Updated")
        table.add_column("Found Via")

        for c in active_candidates[:30]:  # Top 30
            table.add_row(
                c["name"],
                str(c["stars"]),
                c["language"],
                c["updated_at"][:10],
                c["found_via"],
            )

        console.print(table)
        console.print(f"\n[green]{len(active_candidates)} new candidates found[/green]")
        console.print(
            f"[dim]({results['already_known']} already in config, "
            f"{len(sorted_candidates) - len(active_candidates)} archived)[/dim]"
        )
    else:
        console.print("[yellow]No new candidates found.[/yellow]")

    # Print next steps
    if active_candidates:
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Review candidates above")
        console.print("  2. Verify with: python scripts/verify_source.py <url> --steps 1,2,4")
        console.print("  3. If passes, add to scraper/config.py")

    return results


def _github_search_repos(query: str, min_stars: int = 1, per_page: int = 30) -> list:
    """Search GitHub repos. Returns list of repo dicts."""
    try:
        with httpx.Client() as client:
            params = {
                "q": f"{query} stars:>={min_stars}",
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
            }
            resp = client.get(
                f"{GITHUB_API}/search/repositories",
                params=params,
                headers=_github_headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            console.print("[red]GitHub API rate limit hit. Set GITHUB_TOKEN env var.[/red]")
        else:
            console.print(f"[red]GitHub search failed: {e}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]GitHub search error: {e}[/red]")
        return []


def _normalize_url(url: str) -> str:
    """Normalize GitHub URL for comparison."""
    return url.rstrip("/").lower().replace("https://", "").replace("http://", "")


# ──────────────────────────────────────────────────────────────
# C. HEALTH CHECK
# ──────────────────────────────────────────────────────────────


def health_check() -> dict:
    """Check GitHub health of all configured repos (no compilation, just API)."""
    console.print("\n[bold blue]═══ Health Check ═══[/bold blue]")
    config_info = get_config_repo_info()
    results = {"repos": [], "healthy": 0, "warnings": 0, "critical": 0}

    for url, info in config_info.items():
        parts = url.rstrip("/").split("/")
        owner, repo = parts[-2], parts[-1]
        repo_name = f"{owner}/{repo}"

        console.print(f"[blue]Checking {repo_name}...[/blue]")
        health = _check_repo_health(owner, repo)
        health["url"] = url
        health["config_info"] = info

        # Classify
        if health.get("archived") or health.get("not_found"):
            health["status"] = "critical"
            results["critical"] += 1
            console.print(
                "  [red]CRITICAL: "
                f"{'archived' if health.get('archived') else '404 not found'}"
                "[/red]"
            )
        elif health.get("days_since_update", 0) > 365:
            health["status"] = "warning"
            results["warnings"] += 1
            console.print(
                f"  [yellow]WARNING: {health['days_since_update']} days since last update[/yellow]"
            )
        else:
            health["status"] = "healthy"
            results["healthy"] += 1
            days = health.get("days_since_update", "?")
            stars = health.get("stars", "?")
            console.print(f"  [green]OK ({days} days ago, {stars} stars)[/green]")

        results["repos"].append(health)

        # Rate limit: ~0.5s between requests
        time.sleep(0.5)

    # Summary table
    table = Table(title="Health Check Summary")
    table.add_column("Repo", style="cyan")
    table.add_column("Status")
    table.add_column("Stars", justify="right")
    table.add_column("Last Update")
    table.add_column("Issues")

    for r in results["repos"]:
        status_style = {"healthy": "green", "warning": "yellow", "critical": "red"}.get(
            r["status"], "white"
        )
        issues = []
        if r.get("archived"):
            issues.append("archived")
        if r.get("not_found"):
            issues.append("404")
        if r.get("days_since_update", 0) > 365:
            issues.append(f"stale ({r['days_since_update']}d)")

        table.add_row(
            r.get("full_name", r["url"].split("/")[-1]),
            f"[{status_style}]{r['status'].upper()}[/{status_style}]",
            str(r.get("stars", "?")),
            r.get("updated_at", "?")[:10] if r.get("updated_at") else "?",
            ", ".join(issues) if issues else "-",
        )

    console.print(table)
    console.print(
        f"\n[green]{results['healthy']} healthy[/green] | "
        f"[yellow]{results['warnings']} warnings[/yellow] | "
        f"[red]{results['critical']} critical[/red]"
    )

    # Action items for critical repos
    critical_repos = [r for r in results["repos"] if r["status"] == "critical"]
    if critical_repos:
        console.print("\n[bold red]Action required:[/bold red]")
        for r in critical_repos:
            console.print(f"  - Remove or replace: {r.get('full_name', r['url'])}")

    return results


def _check_repo_health(owner: str, repo: str) -> dict:
    """Check a single repo's health via GitHub API."""
    try:
        with httpx.Client() as client:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}",
                headers=_github_headers(),
                timeout=10.0,
            )
            if resp.status_code == 404:
                return {"full_name": f"{owner}/{repo}", "not_found": True}

            resp.raise_for_status()
            data = resp.json()

            updated_at = data.get("pushed_at", data.get("updated_at", ""))
            days_since = 0
            if updated_at:
                updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                days_since = (datetime.now(updated_dt.tzinfo) - updated_dt).days

            return {
                "full_name": data["full_name"],
                "stars": data["stargazers_count"],
                "forks": data["forks_count"],
                "open_issues": data["open_issues_count"],
                "archived": data.get("archived", False),
                "updated_at": updated_at,
                "days_since_update": days_since,
                "default_branch": data.get("default_branch", "main"),
                "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
            }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            console.print(f"[red]Rate limited checking {owner}/{repo}[/red]")
            return {"full_name": f"{owner}/{repo}", "rate_limited": True}
        return {"full_name": f"{owner}/{repo}", "error": str(e)}
    except Exception as e:
        return {"full_name": f"{owner}/{repo}", "error": str(e)}


# ──────────────────────────────────────────────────────────────
# D. AUTO-REMEDIATION
# ──────────────────────────────────────────────────────────────


def remediate() -> dict:
    """Auto-remove critical (archived/deleted) repos from config.

    Runs a health check first, then removes any critical repos from
    scraper/config.py. Abandoned repos (>365 days stale) are flagged
    but NOT auto-removed — they may be complete/stable projects.
    """
    console.print("\n[bold blue]═══ Auto-Remediation ═══[/bold blue]")
    results = {"removed": [], "flagged": [], "config_modified": False}

    # Run health check to find critical repos
    health_results = health_check()
    critical_repos = [r for r in health_results["repos"] if r["status"] == "critical"]
    abandoned_repos = [
        r
        for r in health_results["repos"]
        if r["status"] == "warning" and r.get("days_since_update", 0) > 365
    ]

    if not critical_repos and not abandoned_repos:
        console.print("[green]No critical or abandoned repos found. Config is clean.[/green]")
        return results

    # Flag abandoned repos (don't auto-remove — they may be complete projects)
    for repo in abandoned_repos:
        url = repo.get("url", "")
        name = repo.get("full_name", url.split("/")[-1])
        days = repo.get("days_since_update", 0)
        results["flagged"].append(
            {
                "url": url,
                "name": name,
                "reason": f"abandoned ({days} days since last update)",
            }
        )
        console.print(
            f"  [yellow]FLAGGED: {name} — {days} days "
            "since last update (manual review needed)"
            "[/yellow]"
        )

    if not critical_repos:
        console.print("[green]No critical repos to remove.[/green]")
        return results

    # Remove critical repos from config.py
    config_path = PROJECT_ROOT / "scraper" / "config.py"
    config_text = config_path.read_text()
    original_text = config_text

    for repo in critical_repos:
        url = repo.get("url", "")
        name = repo.get("full_name", url.split("/")[-1])
        reason = "archived" if repo.get("archived") else "deleted (404)"

        if not url:
            continue

        # Remove the dict entry containing this URL from PROJECT_EXAMPLES
        # Match pattern: {  ...  "url": "https://github.com/owner/repo",  ...  },
        escaped_url = re.escape(url)
        pattern = re.compile(
            r'\s*\{[^}]*"url":\s*"' + escaped_url + r'"[^}]*\},?\n?',
            re.DOTALL,
        )
        new_text, count = pattern.subn("", config_text)

        # Also try M3_GITHUB_REPOS format (plain URL strings in a list)
        if count == 0:
            pattern2 = re.compile(
                r'\s*"' + escaped_url + r'",?\n?',
            )
            new_text, count = pattern2.subn("", config_text)

        if count > 0:
            config_text = new_text
            results["removed"].append(
                {
                    "url": url,
                    "name": name,
                    "reason": reason,
                }
            )
            console.print(f"  [red]REMOVED: {name} — {reason}[/red]")

    # Write back if modified
    if config_text != original_text:
        config_path.write_text(config_text)
        results["config_modified"] = True
        removed_count = len(results["removed"])
        console.print(
            f"\n[bold red]Removed {removed_count} critical repo(s) from config.py[/bold red]"
        )
    else:
        console.print("[green]No changes needed to config.py[/green]")

    return results


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="ARBuilder source maintenance pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  monitor     Check for new SDK releases, flag outdated repos
  discover    Search GitHub for new community repos
  health      Health check all configured repos (GitHub API only)
  remediate   Auto-remove archived/deleted repos from config
  all         Run all maintenance tasks (monitor + discover + health)

Examples:
  python scripts/maintain_sources.py monitor
  python scripts/maintain_sources.py discover --min-stars 5
  python scripts/maintain_sources.py health --output reports/health.json
  python scripts/maintain_sources.py all --output reports/maintenance.json
        """,
    )
    parser.add_argument("command", choices=["monitor", "discover", "health", "remediate", "all"])
    parser.add_argument("--output", "-o", help="Output JSON report to file")
    parser.add_argument(
        "--min-stars", type=int, default=1, help="Minimum stars for discovery (default: 1)"
    )
    args = parser.parse_args()

    report = {
        "timestamp": datetime.now().isoformat(),
        "command": args.command,
    }

    if args.command in ("monitor", "all"):
        report["sdk_monitor"] = monitor_sdk_versions()

    if args.command in ("discover", "all"):
        report["discovery"] = discover_repos(min_stars=args.min_stars)

    if args.command in ("health", "all"):
        report["health"] = health_check()

    if args.command == "remediate":
        report["remediation"] = remediate()

    # Output report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        console.print(f"\n[green]Report saved to {output_path}[/green]")


if __name__ == "__main__":
    main()
