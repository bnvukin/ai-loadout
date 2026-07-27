# Disclaimer

**Loadout** (`ai-loadout`) is an open-source tool that helps you detect, install, configure,
and monitor an AI development workstation on your own machine. It is provided **as-is**, with
**no warranty** of any kind.

## Purpose

Loadout is a **local control center** — not a hosted service. It reads your machine into a
"digital twin" (`state.json`), shows a live dashboard at `http://localhost:8421`, and can
(with your explicit confirmation) run installs, upgrades, repairs, model pulls, and config
edits. The CLI (`loadout scan`, `loadout plan`, etc.) is **read-only / dry-run** by default;
mutating work is initiated from the dashboard after you review a command preview.

## No warranty

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR
OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

## AI-generated and assistive content

Loadout may surface **recommendations** (model picks, health explanations, repair suggestions,
install plans). These are **assistive hints**, not professional advice. You are responsible
for validating recommendations before acting — especially for production systems, regulated
data, or security-sensitive environments.

## What Loadout can change on your machine

When you confirm an action, Loadout may:

- **Install or upgrade software** via package managers (winget, Chocolatey, Homebrew, apt,
  npm, pip, etc.) — e.g. Git, Python, Node.js, uv, pnpm, Docker, PowerShell 7, WSL, CUDA,
  VS Build Tools.
- **Pull AI models** via Ollama (`ollama pull …`).
- **Start or repair services** (e.g. start the Ollama server, start Docker Desktop) where
  implemented.
- **Refresh PATH detection** on Windows by reading the registry so newly installed tools
  are found without restarting the dashboard.
- **Edit configuration files** listed in the Config Center (Continue, VS Code/Cursor settings,
  Git config, Docker/npm/pip config, shell profiles, Hugging Face token file, …). Saves
  create a **timestamped backup** under `~/.ai-loadout/backups/` before overwriting.
- **Append logs** locally (`~/.ai-loadout/logs/install.log`, event history in the dashboard).

Dry-run / preview is available: `loadout plan`, dashboard install/update modals (command
shown before confirm), and API dry-run responses without `confirm: true`.

## Third-party software

Loadout **does not bundle** third-party tools. It invokes them from official sources at your
request. Each tool remains governed by its own license and terms, including but not limited to:

Git, Python, Node.js, npm, pnpm, uv, Docker, PowerShell, WSL, winget, Chocolatey, Homebrew,
CUDA, VS Build Tools, Ollama, Open WebUI, VS Code, Cursor, Continue, Claude Code, Codex CLI,
Gemini CLI, OpenCode, and local LLM models from various authors.

See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).

## Security and production systems

- Loadout is aimed at **developer workstations**. Use extra caution on shared, production,
  or compliance-regulated machines.
- **Secrets** (API keys, tokens) are redacted in the Config Center display and in config
  text where possible, but editing secret-bearing files shows full content for editing —
  be careful when sharing your screen.
- **Checksum / signature verification** of downloaded installers is **planned** (Layer 14);
  it is not a current guarantee. See [docs/confirmation-policy.md](./docs/confirmation-policy.md).

## Limitation of liability

To the maximum extent permitted by applicable law, the Loadout contributors shall not be
liable for any indirect, incidental, special, consequential, or punitive damages, or any
loss of profits, data, or goodwill, arising from your use of Loadout or any third-party
software it installs or configures.

## Acceptance

By using Loadout you acknowledge that you have read this disclaimer and accept responsibility
for actions you confirm in the tool.

## Trademarks

All product names, logos, and brands are property of their respective owners. Loadout is
not affiliated with or endorsed by Microsoft, GitHub, Anthropic, OpenAI, Google, Meta,
NVIDIA, Docker Inc., or any other vendor mentioned unless explicitly stated.
