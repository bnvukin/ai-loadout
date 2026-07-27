# Third-Party Notices

Loadout is a **bootstrapper and control center**. It does not bundle or redistribute the
third-party software it manages. When you confirm an action, Loadout invokes those tools
from **official package managers or vendor CLIs** at your request. Each product remains
governed by its own license and terms of service.

## Tools Loadout can detect, install, or monitor

| Tool | Vendor / project | License (summary) | Official site |
|------|------------------|-------------------|---------------|
| Git | Software Freedom Conservancy | GPLv2 | https://git-scm.com/ |
| Python | Python Software Foundation | PSF License | https://www.python.org/ |
| Node.js / npm | OpenJS Foundation | MIT | https://nodejs.org/ |
| pnpm | pnpm project | MIT | https://pnpm.io/ |
| uv | Astral | MIT / Apache-2.0 | https://github.com/astral-sh/uv |
| Docker Desktop | Docker, Inc. | Subscription / vendor terms | https://www.docker.com/ |
| PowerShell 7 | Microsoft | MIT | https://github.com/PowerShell/PowerShell |
| WSL | Microsoft | Windows component | https://learn.microsoft.com/windows/wsl/ |
| winget | Microsoft | MIT | https://learn.microsoft.com/windows/package-manager/ |
| Chocolatey | Chocolatey Software | Apache-2.0 | https://chocolatey.org/ |
| Homebrew | Homebrew | BSD-2-Clause | https://brew.sh/ |
| CUDA / nvcc | NVIDIA | NVIDIA EULA | https://developer.nvidia.com/cuda-toolkit |
| VS Build Tools | Microsoft | Microsoft license | https://visualstudio.microsoft.com/downloads/ |
| Ollama | Ollama | MIT | https://ollama.com/ |
| Open WebUI | Open WebUI | MIT | https://openwebui.com/ |
| VS Code | Microsoft | MIT (product terms apply) | https://code.visualstudio.com/ |
| Cursor | Cursor | Vendor terms | https://cursor.com/ |
| Continue | Continue Dev | Apache-2.0 | https://continue.dev/ |
| Claude Code | Anthropic | Vendor terms | https://docs.anthropic.com/ |
| Codex CLI | OpenAI | Vendor terms | https://openai.com/ |
| Gemini CLI | Google | Vendor terms | https://ai.google.dev/ |
| Local LLM models | Respective authors | Per-model license | Ollama / Hugging Face hubs |

This list is **non-exhaustive** — see `src/ai_loadout/deps/registry.py` and
`src/ai_loadout/runtimes/registry.py` for the full detection set.

## Python dependencies (Loadout itself)

Runtime: `psutil` (BSD-3-Clause). Dashboard extra: FastAPI, uvicorn, websockets (see
`pyproject.toml`). Dev: pytest, ruff, httpx.

## Your responsibility

By using Loadout to install a tool or download a model, **you** accept that product's
license and terms. Loadout surfaces sources in command previews and docs but does not
accept the EULA on your behalf.

Loadout itself is released under the [MIT License](./LICENSE).

See also [DISCLAIMER.md](./DISCLAIMER.md) and [PRIVACY.md](./PRIVACY.md).
