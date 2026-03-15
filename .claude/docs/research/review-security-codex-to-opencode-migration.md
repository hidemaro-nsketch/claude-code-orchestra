# Security Review: Codex to OpenCode CLI Migration

**Reviewer**: Security Reviewer (Subagent)
**Date**: 2026-03-15
**Scope**: Full security review of Codex -> OpenCode CLI migration across ~46 files

---

## Executive Summary

The migration is **clean from a naming perspective** -- zero residual "codex" references remain in the codebase. The permission model is correctly updated. However, several pre-existing security concerns were identified that warrant attention.

**Overall Risk**: Low (migration-specific) / Medium (pre-existing issues)

---

## 1. Settings & Permissions (`.claude/settings.json`)

### PASS: Permission Migration Complete

- `Bash(opencode:*)` correctly present at line 200
- No residual `Bash(codex:*)` found
- Hook paths correctly reference `check-opencode-before-write.py`, `check-opencode-after-plan.py`, `error-to-opencode.py`

### Finding S-1: Overly Broad Bash Permissions

- **Severity**: Medium
- **File**: `.claude/settings.json`, lines 144-208
- **Description**: The `allow` list grants broad `Bash(*)` wildcards for many commands including `Bash(pkill:*)`, `Bash(chmod:*)`, `Bash(curl:*)`, `Bash(wget:*)`, `Bash(sed:*)`, `Bash(awk:*)`, `Bash(xargs:*)`. Combined with `Bash(opencode:*)`, an agent could theoretically construct commands that chain these to perform unintended operations.
- **Recommended Fix**: Consider restricting `pkill` permissions (could kill arbitrary processes). `chmod` could alter file permissions on sensitive files. Evaluate whether `curl`/`wget` need wildcard access or could be restricted to specific domains.

### Finding S-2: Deny List Covers Only Two Destructive rm Commands

- **Severity**: Low
- **File**: `.claude/settings.json`, lines 220-221
- **Description**: The deny list blocks `rm -rf /` and `rm -rf ~` but does not block other destructive patterns like `rm -rf .` or `rm -rf *`. These could wipe the project directory.
- **Recommended Fix**: Add `Bash(rm -rf .)` and `Bash(rm -rf *)` to the deny list, or consider a more comprehensive pattern.

### PASS: Sensitive File Deny Rules

- `.env`, `.env.*`, `*.pem`, `*.key`, `*credentials*`, `*secret*`, `~/.ssh/**`, `~/.aws/**`, `~/.config/gcloud/**` are all correctly denied for Read operations.

---

## 2. Hook Scripts Analysis

### PASS: No Residual "codex" References

All 10 hook scripts in `.claude/hooks/` have been verified -- zero references to "codex" remain.

### PASS: No Unsafe Subprocess Usage

No `shell=True`, `os.system()`, `eval()`, or `exec()` calls found in any hook script. All hooks use `json.load(sys.stdin)` for input parsing, which is safe.

### PASS: Error Handling

All hooks follow the pattern of catching exceptions and exiting with code 0 (non-blocking), which is correct -- hooks should never block the main workflow.

### Finding H-1: Predictable State File in /tmp

- **Severity**: Medium
- **File**: `.claude/hooks/post-implementation-review.py`, line 31
- **Description**: `STATE_FILE = "/tmp/claude-code-implementation-state.json"` uses a predictable path in `/tmp`. On multi-user systems, another user could create a symlink at this path pointing to a sensitive file, potentially causing the hook to overwrite it (symlink attack). The file also has no access control.
- **Recommended Fix**: Use `tempfile.mkdtemp()` or place the state file under the project directory (e.g., `.claude/state/implementation-state.json`) with appropriate `.gitignore` entry. Alternatively, use `os.open()` with `O_CREAT | O_EXCL` to prevent symlink attacks.

### Finding H-2: No Input Sanitization on Hook Command Output

- **Severity**: Low
- **File**: `.claude/hooks/agent-router.py`, lines 133-136, 147-150
- **Description**: The `trigger` variable extracted from user input is embedded directly into the JSON output string via f-string. While `json.dumps()` handles escaping, the `trigger` value comes from a hardcoded list (not user input), so this is not exploitable. However, the pattern could be risky if triggers were dynamically sourced.
- **Recommended Fix**: No immediate action needed. Document that trigger lists must remain hardcoded.

### PASS: OpenCode/Gemini Command Skip Logic

`error-to-opencode.py` correctly skips commands containing `"opencode "` or `"gemini "` in `SKIP_COMMANDS` (line 59-61), preventing recursive debugging suggestions.

---

## 3. Agent Definitions

### PASS: opencode-debugger.md

- Correctly references `opencode run -m github-copilot/gpt-5.4`
- Does not apply fixes directly (returns recommendations to orchestrator)
- Has limited tools: `Read, Bash, Grep, Glob` (no Write/Edit, which is correct for a debugger)
- Uses model `sonnet` (not the main Opus, appropriate for subagent cost control)

### PASS: general-purpose.md

- Correctly references `opencode run -m github-copilot/gpt-5.4`
- Has full tool access including `Write` and `Edit` (appropriate for its role)
- No hardcoded secrets or unsafe patterns

### Finding A-1: No Availability Check for OpenCode/Gemini CLI

- **Severity**: Low
- **File**: `.claude/agents/opencode-debugger.md`, `.claude/agents/general-purpose.md`
- **Description**: Agent definitions instruct subagents to call `opencode run ...` and `gemini -p ...` but include no guidance on handling the case where these CLIs are not installed or not authenticated. The `2>/dev/null` stderr suppression could mask authentication failures.
- **Recommended Fix**: Add a note in agent definitions to check `which opencode` / `which gemini` before calling, and handle the "command not found" case gracefully. Consider a health check step at the beginning of subagent tasks.

---

## 4. Residual Codex References

### PASS: Zero Residual References

Comprehensive grep across all `.py`, `.md`, `.json`, `.toml`, `.jsonc` files returned **no matches** for "codex" (case-insensitive). The glob search for filenames containing "codex" also returned **no matches**.

The migration is complete from a naming perspective.

---

## 5. OpenCode Configuration (`.opencode/`)

### PASS: No Hardcoded Secrets

- `config.toml`: Contains only model configuration, web search toggle, and skill paths. No API keys, tokens, or credentials.
- `opencode.jsonc`: Contains MCP server configuration for Linear. The Linear MCP URL is a public endpoint (`https://mcp.linear.app/mcp`), not a credential.
- `AGENTS.md`: Pure documentation, no secrets.

### Finding O-1: OpenCode approval_policy Set to "on-request"

- **Severity**: Low
- **File**: `.opencode/config.toml`, line 12
- **Description**: `approval_policy = "on-request"` means OpenCode will execute actions without requiring approval when called programmatically. This is by design for automated subagent use, but worth documenting as an intentional decision.
- **Recommended Fix**: Add a comment in `config.toml` explaining why this policy is chosen and the security implications.

### Finding O-2: Linear MCP via npx Without Version Pinning

- **Severity**: Medium
- **File**: `opencode.jsonc`, line 7
- **Description**: `["npx", "-y", "mcp-remote", "https://mcp.linear.app/mcp"]` uses `npx -y` which auto-installs the latest version of `mcp-remote` without version pinning. A supply chain attack on the `mcp-remote` package could introduce malicious code.
- **Recommended Fix**: Pin the version: `npx -y mcp-remote@<specific-version>`. Alternatively, install `mcp-remote` as a project dependency with a locked version.

---

## 6. CLI Command Safety

### Finding C-1: Shell Command Substitution in Templates

- **Severity**: Medium
- **File**: `.claude/skills/opencode-system/references/code-review-task.md`, line 75
- **File**: `.claude/skills/opencode-system/references/refactoring-task.md`, line 70
- **Description**: Template examples use `$(git diff HEAD~1)` and `$(cat src/services/llm_client.py)` inside `opencode run "..."` command strings. If a file path or git diff output contains shell metacharacters (backticks, `$()`, etc.), this could lead to unintended command execution. These are documentation templates (not executed code), but agents following these templates literally could be vulnerable.
- **Recommended Fix**: Add a security note in the templates warning about shell metacharacters. Suggest using heredoc syntax or piping via stdin instead:
  ```bash
  git diff HEAD~1 | opencode run -m github-copilot/gpt-5.4 "Review this diff from stdin" 2>/dev/null
  ```

### Finding C-2: danger-full-access Mentioned in Troubleshooting

- **Severity**: Low
- **File**: `.claude/skills/opencode-system/references/troubleshooting.md`, line 71
- **Description**: The troubleshooting guide mentions `danger-full-access` as a solution for sandbox network restrictions. While marked with "cautiously", an agent following this guide could escalate to full access mode.
- **Recommended Fix**: Add a stronger warning: "NEVER use `danger-full-access` in automated/subagent contexts. Only for manual debugging with explicit user approval."

### PASS: All `opencode run` Commands Use `2>/dev/null`

All template invocations consistently redirect stderr, preventing reasoning output from polluting the command output. This is correct and consistent.

### PASS: No Direct Shell Injection Vectors in Hooks

All hook scripts parse input via `json.load(sys.stdin)` and never construct shell commands from user input. The `lint-on-save.py` hook uses `subprocess.run()` with a list argument (not a string), which prevents shell injection.

---

## Summary Table

| ID | Severity | File | Description |
|----|----------|------|-------------|
| S-1 | Medium | settings.json | Overly broad Bash permissions (pkill, chmod, curl wildcards) |
| S-2 | Low | settings.json | Incomplete destructive rm denial patterns |
| H-1 | Medium | post-implementation-review.py:31 | Predictable /tmp state file (symlink attack risk) |
| H-2 | Low | agent-router.py | Trigger values in JSON output (currently safe, pattern risk) |
| A-1 | Low | Agent definitions | No CLI availability check before calling opencode/gemini |
| O-1 | Low | .opencode/config.toml:12 | approval_policy "on-request" undocumented rationale |
| O-2 | Medium | opencode.jsonc:7 | npx mcp-remote without version pinning (supply chain risk) |
| C-1 | Medium | code-review-task.md:75, refactoring-task.md:70 | Shell command substitution in opencode templates |
| C-2 | Low | troubleshooting.md:71 | danger-full-access mentioned without strong warning |

---

## Migration-Specific Verdict

**The Codex-to-OpenCode migration is CLEAN:**

1. Zero residual "codex" references in any tracked file type
2. All hook file paths correctly updated in settings.json
3. Permission `Bash(opencode:*)` correctly replaces `Bash(codex:*)`
4. All agent definitions consistently reference `opencode run -m github-copilot/gpt-5.4`
5. Old codex files (`.codex/`, `codex-debugger.md`, `codex-system/`, etc.) are marked as deleted in git
6. New opencode files (`.opencode/`, `opencode-debugger.md`, `opencode-system/`, etc.) are properly created

**No Critical or High severity issues found.** The Medium findings (S-1, H-1, O-2, C-1) are pre-existing patterns or best-practice improvements, not migration regressions.
