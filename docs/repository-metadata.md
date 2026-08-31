# Repository publication checklist

These settings require repository-owner access and are intentionally not changed by local release preparation.

- **Description:** Deterministic quality gates and feedback loops for AI-generated code.
- **Homepage:** `https://github.com/MaheshBhushan/AgentGuard#readme` until dedicated documentation exists.
- **Topics:** `github-actions`, `code-quality`, `static-analysis`, `ai-agents`, `codex`, `claude-code`, `developer-tools`, `security`, `quality-gate`, `python`.
- **Social preview:** export a 1280×640 image using the repository name, shield motif, and the line “Deterministic quality gates for AI-generated code”; do not use a terminal screenshot that implies unmeasured results.
- Enable Discussions when there is capacity to answer support questions.
- Verify the Marketplace listing icon/color, release notes, support links, and `v1` tag before publication.
- Add the PyPI badge only after `agentguard-quality` is published and a clean installation is verified.

Suggested owner commands after reviewing the values:

```bash
gh repo edit MaheshBhushan/AgentGuard \
  --description "Deterministic quality gates and feedback loops for AI-generated code." \
  --homepage "https://github.com/MaheshBhushan/AgentGuard#readme" \
  --add-topic github-actions \
  --add-topic code-quality \
  --add-topic static-analysis \
  --add-topic ai-agents \
  --add-topic codex \
  --add-topic claude-code \
  --add-topic developer-tools \
  --add-topic security \
  --add-topic quality-gate \
  --add-topic python
```

Uploading a social preview and enabling Discussions remain manual GitHub settings. Run these commands only after explicit publication approval.
