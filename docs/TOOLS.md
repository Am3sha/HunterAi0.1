# Tool Management

HunterAI installs and runs security tools for you — users never hand-install
binaries. The subsystem has four pillars (Clean Architecture, infrastructure layer):

| Pillar          | File                         | Responsibility |
|-----------------|------------------------------|----------------|
| **Registry**    | `infrastructure/tools/registry.py` | Declarative catalog: pinned versions + per-platform sources. **Add a tool here.** |
| **Provider**    | `infrastructure/tools/provider.py` | Download asset → verify SHA-256 → extract binary. |
| **Manager**     | `infrastructure/tools/manager.py`  | Discover / install / update / status / resolve / run. Implements `ToolManagerPort`. |
| **Executor**    | `infrastructure/tools/executor.py` | Run a binary with no shell, a timeout, captured output. Implements `ToolExecutorPort`. |

The application/use-case layer depends only on the **ports** in
`app/domain/ports/tools.py`, never on these concrete classes.

## CLI (run inside WSL / Linux)

```bash
python -m app.tools_cli status         # required vs installed
python -m app.tools_cli setup          # install all required tools
python -m app.tools_cli setup --force  # reinstall + re-verify
python -m app.tools_cli install httpx  # one tool
python -m app.tools_cli paths          # resolved executable paths
# also available as the `hunterai-tools` console script after `pip install -e .`
```

## Install layout (managed tools dir, kept out of git)

```
<tools_dir>/<name>/<name>        # the executable
<tools_dir>/<name>/.meta.json    # {name, version, sha256, source_url, installed_at}
```

Default `tools_dir` is `<repo>/.hunterai/tools` (override with `HUNTERAI_TOOLS_DIR`).

## Integrity

- If a source pins a `sha256`, it is **strictly enforced** on download.
- Otherwise the asset is verified against the release's official `*_checksums.txt`,
  and `setup` prints the observed hash so you can pin it in the registry for fully
  reproducible installs.

## Adding a new tool (e.g. Nuclei, ffuf, Naabu)

1. Add a `ToolSpec` entry to `registry.py` (for ProjectDiscovery tools, reuse the
   `_pd_sources(...)` helper).
2. That's it for installation/execution. (An output parser may be added in the
   recon layer when the tool is wired into the pipeline.)
