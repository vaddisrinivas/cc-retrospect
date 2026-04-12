"""Persistent localhost dashboard server for cc-retrospect.

Runs on 127.0.0.1:7731 as a background daemon.
- Serves dashboard.html and data.js from ~/.cc-retrospect/
- /api/reload   — regenerate data.js from live session data
- /api/reports  — list saved report snapshots
- /api/config   — GET/POST ~/.cc-retrospect/config.env
"""
from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_INSIGHTS_TTL = 7 * 24 * 3600  # 1 week
_insights_lock = threading.Lock()
_insights_generating = False

PORT = int(os.environ.get("CC_RETROSPECT_PORT", "7731"))
_data_dir: Path = Path.home() / ".cc-retrospect"
logger = logging.getLogger("cc_retrospect.server")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if os.environ.get("CC_RETROSPECT_SERVER_LOG"):
            logger.info(fmt, *args)

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/", "/index.html"):
            self._file(_data_dir / "dashboard.html", "text/html")
        elif p == "/data.js":
            self._file(_data_dir / "data.js", "application/javascript")
        elif p.startswith("/reports/"):
            name = p[9:]
            self._file(_data_dir / "reports" / name, _mime(name))
        elif p == "/api/reports":
            self._json(_list_reports())
        elif p == "/api/config":
            self._json({"config": _read_config()})
        elif p == "/api/reload":
            self._reload()
        elif p == "/api/sessions":
            self._reload_and_respond_sessions()
        elif p == "/api/health":
            self._json({"status": "ok", "port": PORT, "data_dir": str(_data_dir)})
        elif p == "/gif.worker.js":
            worker = Path(__file__).parent / "gif.worker.js"
            self._file(worker, "application/javascript")
        elif p == "/api/insights":
            self._get_insights()
        elif p == "/api/config/structured":
            self._structured_config()
        elif p == "/api/scripts":
            self._list_scripts()
        elif p == "/api/style":
            self._get_style()
        elif p == "/api/chains":
            self._get_chains()
        elif p == "/api/toolcalls":
            self._get_toolcalls()
        else:
            self.send_error(404)

    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/api/config":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            _write_config(body.get("config", ""))
            self._json({"ok": True})
        elif p == "/api/reload":
            self._reload()
        elif p == "/api/insights/generate":
            self._trigger_insights()
        elif p == "/api/config/structured":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            self._update_structured_config(body)
        elif p == "/api/style/sync":
            self._sync_style()
        elif p == "/api/style/generate":
            self._generate_style()
        elif p == "/api/magic-create":
            self._magic_create()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _reload(self):
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from cc_retrospect.dashboard import generate_dashboard
            from cc_retrospect.config import load_config
            cfg = load_config()
            data_json = generate_dashboard(cfg)
            (_data_dir / "data.js").write_text(f"const D = {data_json};\n", encoding="utf-8")
            self._json({"ok": True})
        except (OSError, ImportError, ValueError) as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _reload_and_respond_sessions(self):
        try:
            from cc_retrospect.config import load_config
            from cc_retrospect.cache import load_all_sessions
            cfg = load_config()
            sessions = load_all_sessions(cfg)
            data = [s.model_dump() for s in sessions[-100:]]
            self._json({"sessions": data, "count": len(sessions)})
        except (OSError, ImportError, ValueError) as e:
            self._json({"error": str(e)}, 500)

    def _get_insights(self):
        cache = _data_dir / "insights_cache.json"
        if cache.exists():
            try:
                data = json.loads(cache.read_text())
                age = time.time() - data.get("ts", 0)
                self._json({
                    "status": "cached" if age < _INSIGHTS_TTL else "stale",
                    "content": data.get("content", ""),
                    "age_days": round(age / 86400, 1),
                    "generating": _insights_generating,
                })
                return
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        self._json({"status": "empty", "content": "", "age_days": None, "generating": _insights_generating})

    def _trigger_insights(self):
        global _insights_generating
        with _insights_lock:
            if _insights_generating:
                self._json({"ok": False, "message": "Already generating"})
                return
            _insights_generating = True
        t = threading.Thread(target=_run_insights_background, daemon=True)
        t.start()
        self._json({"ok": True, "message": "Generating insights in background (1-2 min)…"})

    def _structured_config(self):
        try:
            from cc_retrospect.config import load_config
            cfg = load_config()
            data = {
                "pricing": {
                    "opus": cfg.pricing.opus.model_dump(),
                    "sonnet": cfg.pricing.sonnet.model_dump(),
                    "haiku": cfg.pricing.haiku.model_dump(),
                },
                "thresholds": {k: v for k, v in cfg.thresholds.model_dump().items() if k not in ("frustration_keywords", "waste_webfetch_domains")},
                "hints": cfg.hints.model_dump(),
                "budget": {
                    "warning": cfg.budget.warning.model_dump(),
                    "critical": cfg.budget.critical.model_dump(),
                    "severe": cfg.budget.severe.model_dump(),
                },
            }
            self._json(data)
        except (ImportError, OSError, ValueError) as e:
            self._json({"error": str(e)}, 500)

    def _update_structured_config(self, updates: dict):
        """Apply partial config updates by writing them as config.env lines."""
        lines = []
        config_path = _data_dir / "config.env"
        if config_path.exists():
            lines = config_path.read_text(encoding="utf-8").splitlines()

        # Map structured keys to env var format
        for section, values in updates.items():
            if isinstance(values, dict):
                for key, val in values.items():
                    if isinstance(val, dict):
                        for subkey, subval in val.items():
                            env_key = f"{section.upper()}__{key.upper()}__{subkey.upper()}"
                            # Update existing or append
                            found = False
                            for i, line in enumerate(lines):
                                if line.strip().startswith(env_key + "="):
                                    lines[i] = f"{env_key}={subval}"
                                    found = True
                                    break
                            if not found:
                                lines.append(f"{env_key}={subval}")
                    else:
                        env_key = f"{section.upper()}__{key.upper()}"
                        found = False
                        for i, line in enumerate(lines):
                            if line.strip().startswith(env_key + "="):
                                lines[i] = f"{env_key}={val}"
                                found = True
                                break
                        if not found:
                            lines.append(f"{env_key}={val}")

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._json({"ok": True})

    def _get_style(self):
        active = Path.home() / ".claude" / "STYLE.md"
        generated = _data_dir / "STYLE.md"
        data = {
            "active": active.read_text(encoding="utf-8") if active.exists() else "",
            "generated": generated.read_text(encoding="utf-8") if generated.exists() else "",
            "active_path": str(active),
            "generated_path": str(generated),
            "in_sync": active.exists() and generated.exists() and active.read_text() == generated.read_text(),
        }
        self._json(data)

    def _get_chains(self):
        try:
            from cc_retrospect.config import load_config
            from cc_retrospect.cache import load_all_sessions
            cfg = load_config()
            sessions = load_all_sessions(cfg)
            chains = []
            for s in sessions[-100:]:
                session_chains = []
                for tool, length in (getattr(s, "tool_chains", None) or []):
                    session_chains.append({"tool": tool, "length": length})
                if session_chains:
                    chains.append({
                        "session_id": s.session_id,
                        "project": s.project,
                        "date": (s.start_ts or "")[:10],
                        "cost": round(s.total_cost, 2),
                        "chains": session_chains,
                    })
            self._json({"chains": chains})
        except (ImportError, OSError, ValueError) as e:
            self._json({"error": str(e)}, 500)

    def _get_toolcalls(self):
        try:
            from cc_retrospect.config import load_config
            from cc_retrospect.cache import load_all_sessions
            qs = parse_qs(urlparse(self.path).query)
            limit = min(int(qs.get("limit", ["100"])[0]), 200)
            offset = int(qs.get("offset", ["0"])[0])
            tool_filter = qs.get("tool", [None])[0]
            error_only = qs.get("errors", ["0"])[0] == "1"

            cfg = load_config()
            sessions = load_all_sessions(cfg)
            # Only scan recent sessions (last 200) for performance — 53k+ calls is too much
            recent = sorted(
                [s for s in sessions if getattr(s, "tool_calls", None)],
                key=lambda s: s.start_ts or "", reverse=True,
            )[:200]
            tool_names_set = set()
            all_calls = []
            for s in recent:
                for tc in (getattr(s, "tool_calls", None) or []):
                    tool_names_set.add(tc.name)
                    if tool_filter and tc.name != tool_filter:
                        continue
                    if error_only and not tc.is_error:
                        continue
                    all_calls.append({
                        "name": tc.name,
                        "input_summary": (tc.input_summary or "")[:200],
                        "output_snippet": (tc.output_snippet or "")[:100],
                        "is_error": tc.is_error,
                        "ts": tc.ts,
                        "session_id": s.session_id,
                        "project": s.project,
                    })
            all_calls.sort(key=lambda x: x.get("ts", ""), reverse=True)
            total = len(all_calls)
            page = all_calls[offset:offset + limit]
            self._json({"calls": page, "total": total, "offset": offset, "limit": limit, "tool_names": sorted(tool_names_set)})
        except (ImportError, OSError, ValueError, TypeError) as e:
            self._json({"error": str(e)}, 500)

    def _sync_style(self):
        generated = _data_dir / "STYLE.md"
        active = Path.home() / ".claude" / "STYLE.md"
        if generated.exists():
            active.write_text(generated.read_text(encoding="utf-8"), encoding="utf-8")
            self._json({"ok": True, "message": "STYLE.md synced"})
        else:
            self._json({"ok": False, "message": "No generated STYLE.md found. Run /cc-retrospect:learn first."}, 400)

    def _generate_style(self):
        try:
            from cc_retrospect.learn import analyze_user_messages, generate_style
            from cc_retrospect.config import load_config
            cfg = load_config()
            profile = analyze_user_messages(cfg)
            content = generate_style(profile, cfg)
            (_data_dir / "STYLE.md").write_text(content, encoding="utf-8")
            self._json({"ok": True, "content": content})
        except (ImportError, OSError, ValueError) as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _list_scripts(self):
        """List saved generated scripts from ~/.claude/plugins/generated_scripts/."""
        scripts_dir = Path.home() / ".claude" / "plugins" / "generated_scripts"
        if not scripts_dir.exists():
            self._json({"scripts": []})
            return
        out = []
        for f in sorted(scripts_dir.glob("*.sh"), key=lambda p: p.stat().st_mtime, reverse=True):
            # Extract description/when_to_use from script header comments
            description, when_to_use = "", ""
            try:
                for line in f.read_text(encoding="utf-8").splitlines()[:20]:
                    if line.startswith("# Description:"):
                        description = line[14:].strip()
                    elif line.startswith("# When to use:"):
                        when_to_use = line[14:].strip()
                    elif line.startswith("# Use when:"):
                        when_to_use = line[11:].strip()
            except OSError:
                pass
            out.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": time.strftime("%Y-%m-%d", time.localtime(f.stat().st_mtime)),
                "description": description,
                "when_to_use": when_to_use,
            })
        self._json({"scripts": out})

    def _magic_create(self):
        """Use Claude to generate a self-contained script, save it, update STYLE.md."""
        import re
        from cc_retrospect.config import load_config
        cfg = load_config()
        mc = cfg.magic_create
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            calls = body.get("calls", [])
            user_prompt = body.get("prompt", "").strip()
            scope = body.get("scope", "selected")
            projects = body.get("projects", [])
            script_name = body.get("script_name", "").strip()

            if not calls:
                self._json({"ok": False, "error": "No tool calls provided"}, 400)
                return

            # Parse tool call inputs for clean display
            def _parse_call(c):
                name = c.get("name", "")
                raw = c.get("input_summary", "") or ""
                try:
                    parsed = json.loads(raw)
                    if name == "Bash":
                        return parsed.get("command", raw)
                    elif name in ("Edit", "Read", "Write"):
                        return parsed.get("file_path", raw)
                    elif name == "Glob":
                        return parsed.get("pattern", raw)
                    elif name == "Grep":
                        return f"grep '{parsed.get('pattern','')}' in {parsed.get('path','.')}"
                    elif name == "WebFetch":
                        return parsed.get("url", raw)
                    else:
                        return raw[:120]
                except (json.JSONDecodeError, AttributeError):
                    return raw[:120]

            call_lines = []
            for i, c in enumerate(calls[:mc.max_calls], 1):
                summary = _parse_call(c)
                output = (c.get("output_snippet") or "")[:80]
                err = " [ERROR]" if c.get("is_error") else ""
                proj_tag = f" ({c.get('project','').split('-')[-1]})" if scope == "cross" else ""
                call_lines.append(
                    f"{i:2}. [{c.get('name','')}]{err}{proj_tag} {summary}"
                    + (f"\n    → {output}" if output else "")
                )

            calls_block = "\n".join(call_lines)
            goal = user_prompt or "Create a reusable, self-contained script that automates this workflow"

            # Scope-specific instructions
            if scope == "cross":
                proj_context = f"These calls span multiple projects: {', '.join(projects[:6]) or 'various'}."
                portability = (
                    "- Make the script fully portable: no hardcoded project paths, use $PWD/$1 for targets\n"
                    "- Add a --project or positional arg so it works across repos\n"
                    "- Use relative paths or CLI args for anything project-specific"
                )
            elif scope == "project":
                proj_context = f"These calls are from project(s): {', '.join(projects[:3]) or 'one project'}."
                portability = (
                    "- Replace hardcoded absolute paths with $HOME, $PROJECT_ROOT, or script-relative vars\n"
                    "- Add a PROJECT_ROOT variable at the top defaulting to the script's location"
                )
            else:
                proj_context = ""
                portability = "- Replace hardcoded paths with $HOME or variables where sensible"

            prompt = f"""You are a senior DevOps engineer. A developer captured these tool calls from their Claude Code session history and wants them automated as a reusable script.

{proj_context}

## Tool Call History ({len(calls)} calls, scope: {scope})
```
{calls_block}
```

## Goal
{goal}

## Requirements for the script
- Single self-contained bash script (Python only if bash is clearly wrong)
- `set -euo pipefail` + `trap` for cleanup if needed
- Usage/help block if script takes arguments
- Inline comments on every non-obvious step
{portability}
- Check required dependencies (command -v) at startup
- Make it idempotent where possible
- End with a clear success echo

## Output format
Respond with ONLY a JSON object — no markdown, no explanation:
{{
  "description": "<one sentence: what the script does>",
  "when_to_use": "<one sentence: when/why someone would run this>",
  "script": "<full raw bash script as a string, \\n for newlines>"
}}"""

            cmd = ["claude", "-p", prompt, "--output-format", "json"]
            if mc.model:
                cmd += ["--model", mc.model]
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=mc.timeout_seconds,
                env={**os.environ, "NO_COLOR": "1"},
            )
            if result.returncode != 0:
                self._json({"ok": False, "error": result.stderr.strip() or "claude failed"}, 500)
                return

            outer = json.loads(result.stdout)
            raw_result = outer.get("result", "").strip()

            # Parse structured JSON from Claude's result field
            try:
                # Strip markdown fences if Claude wrapped it anyway
                clean = re.sub(r"^```(?:json)?\n?", "", raw_result)
                clean = re.sub(r"\n?```$", "", clean).strip()
                payload = json.loads(clean)
                description = payload.get("description", "").strip()
                when_to_use = payload.get("when_to_use", "").strip()
                script = payload.get("script", "").strip()
            except (json.JSONDecodeError, KeyError):
                # Fallback: treat the whole result as raw script, parse comment headers
                ansi = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
                script = ansi.sub("", raw_result).strip()
                script = re.sub(r"^```(?:bash|sh|python)?\n", "", script)
                script = re.sub(r"\n```$", "", script).strip()
                description, when_to_use = "", ""
                for line in script.splitlines()[:15]:
                    if line.startswith("# Description:"):
                        description = line[14:].strip()
                    elif line.startswith("# When to use:") or line.startswith("# Use when:"):
                        when_to_use = line.split(":", 1)[1].strip() if ":" in line else ""

            if not script:
                self._json({"ok": False, "error": "Claude returned empty script"}, 500)
                return

            # Prepend description/when_to_use as header comments if present
            if description or when_to_use:
                header_lines = []
                if description:
                    header_lines.append(f"# Description: {description}")
                if when_to_use:
                    header_lines.append(f"# When to use: {when_to_use}")
                # Insert after shebang line if present
                lines = script.splitlines()
                if lines and lines[0].startswith("#!"):
                    script = lines[0] + "\n" + "\n".join(header_lines) + "\n" + "\n".join(lines[1:])
                else:
                    script = "\n".join(header_lines) + "\n" + script

            # Save to configured scripts directory
            scripts_dir = mc.save_dir
            scripts_dir.mkdir(parents=True, exist_ok=True)

            # Derive filename from script_name or goal
            if not script_name:
                slug = re.sub(r"[^a-z0-9]+", "-", goal.lower())[:40].strip("-")
                script_name = slug + ".sh"
            elif not script_name.endswith((".sh", ".py")):
                script_name += ".sh"

            # Avoid collisions
            save_path = scripts_dir / script_name
            stem = save_path.stem
            idx = 1
            while save_path.exists():
                save_path = scripts_dir / f"{stem}-{idx}{save_path.suffix}"
                idx += 1

            save_path.write_text(script, encoding="utf-8")
            save_path.chmod(0o755)

            # Append one line to STYLE.md
            style_line = ""
            if description or when_to_use:
                parts = []
                if description:
                    parts.append(description)
                if when_to_use:
                    parts.append(f"Use when: {when_to_use}")
                style_line = f"- `{save_path.name}` — {'. '.join(parts)}"

                active_style = Path.home() / ".claude" / "STYLE.md"
                try:
                    content = active_style.read_text(encoding="utf-8") if active_style.exists() else ""
                    # Add Generated Scripts section if not present
                    if "## Generated Scripts" not in content:
                        content = content.rstrip() + "\n\n## Generated Scripts\n"
                    content = content.rstrip() + "\n" + style_line + "\n"
                    active_style.write_text(content, encoding="utf-8")
                    # Also sync back to cc-retrospect copy
                    (_data_dir / "STYLE.md").write_text(content, encoding="utf-8")
                except OSError:
                    pass

            self._json({
                "ok": True,
                "script": script,
                "saved_path": str(save_path),
                "script_name": save_path.name,
                "style_line": style_line,
                "description": description,
                "when_to_use": when_to_use,
            })
        except subprocess.TimeoutExpired:
            self._json({"ok": False, "error": f"Claude timed out ({mc.timeout_seconds}s). Try fewer calls or increase MAGIC_CREATE__TIMEOUT_SECONDS."}, 504)
        except FileNotFoundError:
            self._json({"ok": False, "error": "claude CLI not found — is Claude Code installed?"}, 503)
        except (OSError, json.JSONDecodeError, subprocess.SubprocessError) as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _file(self, path: Path, mime: str):
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def _run_insights_background() -> None:
    """Run `claude -p /cc-retrospect` and cache the output. Runs in a daemon thread."""
    global _insights_generating
    cache = _data_dir / "insights_cache.json"
    try:
        import re
        result = subprocess.run(
            ["claude", "-p", "/cc-retrospect"],
            capture_output=True, text=True, timeout=300,
            env={**os.environ, "NO_COLOR": "1"},
        )
        raw = result.stdout.strip() or result.stderr.strip()
        # Strip ANSI escape codes
        ansi = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        content = ansi.sub("", raw).strip()
        if content:
            cache.write_text(json.dumps({"content": content, "ts": time.time()}), encoding="utf-8")
            logger.info("Insights cached (%d chars)", len(content))
            # Also persist to dated insights file
            insights_dir = _data_dir / "insights"
            insights_dir.mkdir(exist_ok=True)
            dated_path = insights_dir / f"{time.strftime('%Y-%m-%d')}.json"
            dated_path.write_text(json.dumps({
                "content": content,
                "ts": time.time(),
                "source": "claude-ai",
            }), encoding="utf-8")
        else:
            logger.warning("claude -p returned empty output")
    except subprocess.TimeoutExpired:
        logger.warning("claude -p timed out after 5 min")
    except FileNotFoundError:
        logger.warning("claude CLI not found — insights unavailable")
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("Insights generation failed: %s", e)
    finally:
        with _insights_lock:
            _insights_generating = False


def _mime(name: str) -> str:
    if name.endswith(".js"):
        return "application/javascript"
    if name.endswith(".html"):
        return "text/html"
    return "text/plain"


def _list_reports() -> list[dict]:
    reports_dir = _data_dir / "reports"
    if not reports_dir.exists():
        return []
    out = []
    for f in sorted(reports_dir.glob("dashboard-*.html"), reverse=True):
        stamp = f.stem.replace("dashboard-", "")
        data_name = f"data-{stamp}.js"
        out.append({
            "name": f.stem,
            "date": stamp.replace("_", " ").replace("-", "/", 2),
            "html_url": f"/reports/{f.name}",
            "data_url": f"/reports/{data_name}" if (reports_dir / data_name).exists() else None,
        })
    return out


def _read_config() -> str:
    p = _data_dir / "config.env"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return (
        "# cc-retrospect config\n"
        "# Pricing ($ per million tokens)\n"
        "# PRICING__SONNET__INPUT_PER_MTOK=3.0\n"
        "# PRICING__SONNET__OUTPUT_PER_MTOK=15.0\n"
        "# PRICING__OPUS__INPUT_PER_MTOK=15.0\n"
        "# PRICING__OPUS__OUTPUT_PER_MTOK=75.0\n\n"
        "# Budget thresholds ($)\n"
        "# BUDGET__WARNING__THRESHOLD=75\n"
        "# BUDGET__CRITICAL__THRESHOLD=200\n"
        "# BUDGET__SEVERE__THRESHOLD=400\n"
    )


def _write_config(content: str):
    (_data_dir / "config.env").write_text(content, encoding="utf-8")


def pid_file() -> Path:
    return _data_dir / "dashboard.pid"


def is_running() -> bool:
    p = pid_file()
    if not p.exists():
        return False
    try:
        pid = int(p.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        p.unlink(missing_ok=True)
        return False


def start_server():
    """Fork a daemon server process. Returns immediately."""
    import subprocess
    _data_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [sys.executable, __file__, str(_data_dir)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    pid_file().write_text(str(proc.pid))


def stop_server():
    """Kill the running server if any."""
    p = pid_file()
    if not p.exists():
        return
    try:
        pid = int(p.read_text().strip())
        os.kill(pid, signal.SIGTERM)
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        pass
    p.unlink(missing_ok=True)


def ensure_running():
    """Start server if not already running."""
    if not is_running():
        start_server()
        import time; time.sleep(0.6)  # brief wait for bind


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _data_dir = Path(sys.argv[1])
    httpd = HTTPServer(("127.0.0.1", PORT), _Handler)
    def _shutdown(sig, frame):
        httpd.shutdown()
        pid_file().unlink(missing_ok=True)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    httpd.serve_forever()
