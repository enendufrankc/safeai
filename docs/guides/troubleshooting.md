# Troubleshooting and FAQ

Common issues and solutions when working with SafeAI.

---

## Installation

### `ModuleNotFoundError: No module named 'safeai'`

Make sure you installed the correct package name:

```bash
pip install safeai-sdk
```

The PyPI package is `safeai-sdk`, not `safeai`.

### Optional extras fail to install

Install extras explicitly:

```bash
pip install "safeai-sdk[vault]"   # HashiCorp Vault
pip install "safeai-sdk[aws]"     # AWS Secrets Manager
pip install "safeai-sdk[mcp]"     # MCP server
pip install "safeai-sdk[all]"     # all optional backends
```

---

## Configuration

### `FileNotFoundError` when calling `SafeAI.from_config("safeai.yaml")`

Run `safeai init --path .` first to scaffold the default config files, or ensure `safeai.yaml` exists in your working directory.

### Policy changes are not taking effect

SafeAI supports hot reload. Either:

- Call `ai.policy_engine.reload()` in code, or
- Send `POST /v1/policies/reload` to the proxy, or
- Restart the process.

Check that your policy file path matches the glob in `safeai.yaml → paths.policy_files`.

### Schema validation errors on startup

Run `safeai validate --config safeai.yaml` to check your config files against the JSON schemas in `schemas/v1alpha1/`.

---

## Proxy and Sidecar

### Proxy returns `503` on startup

The proxy health endpoint (`/v1/health`) returns `503` until initialization completes. Wait a moment and retry:

```bash
curl http://127.0.0.1:8910/v1/health
```

### Upstream forwarding not working

Ensure you pass the upstream URL when starting the proxy:

```bash
safeai serve --mode sidecar --upstream https://api.openai.com/v1 --port 8910
```

---

## Detectors and Scanning

### False positives on PII detection

Tune your policy to use `allow` rules for known safe patterns:

```yaml
policies:
  - name: allow-test-emails
    conditions:
      data_tags: ["pii.email"]
      boundary: input
    action: allow
    priority: 1
```

### Custom detector patterns not loading

Ensure your plugin file:

1. Is listed in `safeai.yaml → plugins.plugin_files`
2. Exports a `safeai_detectors()` function returning `[(pattern, tag, name)]` tuples
3. Has no import errors (check with `python -c "import plugins.your_plugin"`)

---

## Intelligence Layer

### `safeai intelligence auto-config` produces empty output

The intelligence layer requires a running AI backend. Check:

1. `safeai.yaml → intelligence.enabled` is `true`
2. Your backend (Ollama, OpenAI, etc.) is reachable at the configured `base_url`
3. The `api_key_env` environment variable is set if using a cloud provider

### AI-generated configs are not applied automatically

By design, SafeAI stages AI-generated configs in `.safeai-generated/` for human review. Inspect the files and copy approved configs to your project root.

---

## CLI

### `safeai: command not found`

Ensure the package is installed in your active environment:

```bash
pip install safeai-sdk
which safeai
```

If using `uv`, run commands via `uv run safeai ...`.

### `safeai logs` shows no output

Check that `safeai.yaml → audit.file_path` points to a valid path and that the log file exists. The default is `logs/audit.log`.

---

## MCP Server

### MCP tools not appearing in client

Ensure MCP extras are installed:

```bash
pip install "safeai-sdk[mcp]"
```

Start the server with:

```bash
safeai mcp --config safeai.yaml
```

---

## Still stuck?

- Search [existing issues](https://github.com/enendufrankc/safeai/issues)
- Open a [bug report](https://github.com/enendufrankc/safeai/issues/new?template=bug_report.yml)
- Review the [guides](../guides/policy-engine.md) for detailed walkthroughs
