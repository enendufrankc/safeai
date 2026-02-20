# SafeAI Quickstart (Phase 1)

This quickstart covers install, initialization, boundary scans, audit query, memory writes, and one end-to-end SDK run.

## 1. Install

```bash
python3 -m pip install -e ".[dev]"
```

## 2. Initialize project files

```bash
safeai init
```

Creates:
- `safeai.yaml`
- `policies/default.yaml`
- `contracts/example.yaml`
- `schemas/memory.yaml`

## 3. Validate config and schemas

```bash
safeai validate --config safeai.yaml
```

Expected output includes:
- config path
- policy count
- memory schema count

## 4. Run boundary scans

Input boundary:

```bash
safeai scan --boundary input --input "token=sk-ABCDEFGHIJKLMNOPQRSTUV"
```

Output boundary:

```bash
safeai scan --boundary output --input "Contact alice@example.com"
```

## 5. Inspect audit logs

Default JSON output:

```bash
safeai logs --tail 20
```

Filtered query examples:

```bash
safeai logs --boundary output --action redact --tail 10
safeai logs --agent assistant-1 --last 1h --tail 50
```

Text output:

```bash
safeai logs --text-output --tail 5
```

## 6. Run the end-to-end SDK example

```bash
python3 examples/e2e_example.py
```

The example demonstrates:
- input scan
- output guard
- memory write/read via schema-bound fields
- audit query

## 7. Next steps

1. Edit `policies/default.yaml` to fit your data tags and tool names.
2. Tighten `schemas/memory.yaml` to only approved memory fields.
3. Add custom detectors and integration tests for your domain data.
