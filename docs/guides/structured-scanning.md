# Structured Scanning

SafeAI can scan nested JSON payloads and files, not just flat strings. The `scan_structured_input` method walks through dictionaries, lists, and nested objects, detecting secrets and PII at every level. Each detection includes the path within the structure where it was found, so you know exactly which field contains the problem.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.quickstart()

payload = {
    "user": {"name": "Alice", "api_key": "sk-ABCDEF1234567890"},
    "message": "Hello world",
}

result = ai.scan_structured_input(payload)
print(result.action)  # "block"
print(result.detections[0].path)  # "user.api_key"
```

## Full Example

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Deeply nested payload with secrets and PII at various levels
payload = {
    "request_id": "req-001",
    "user": {
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "preferences": {
            "api_key": "sk-ABCDEF1234567890",
            "notifications": True,
        },
    },
    "tools": [
        {"name": "search", "params": {"query": "weather"}},
        {"name": "database", "params": {"connection": "postgres://admin:s3cret@db:5432/prod"}},
    ],
}

result = ai.scan_structured_input(payload, agent_id="data-bot")

print(f"Action: {result.action}")
print(f"Detections: {len(result.detections)}")

for d in result.detections:
    print(f"  [{d.type}] at path: {d.path}")
    print(f"    value: {d.masked_value}")

# Output:
#   [api_key] at path: user.preferences.api_key
#     value: sk-ABCDEF****
#   [email] at path: user.email
#     value: ****@example.com
#   [database_url] at path: tools[1].params.connection
#     value: postgres://****:****@db:5432/prod
```

!!! info "Array indexing in paths"
    Paths use dot notation for objects and bracket notation for arrays: `tools[1].params.connection`. This makes it easy to locate the exact field in your payload.

## File Scanning

Scan files on disk for secrets and PII:

```python
# Scan a JSON file
result = ai.scan_file_input("config/secrets.json", agent_id="deploy-bot")

if result.detections:
    print(f"Found {len(result.detections)} issue(s) in file:")
    for d in result.detections:
        print(f"  [{d.type}] at {d.path}")
```

Supported file formats:

| Format | Extension     | Notes                             |
|--------|---------------|-----------------------------------|
| JSON   | `.json`       | Full structural path tracking     |
| YAML   | `.yaml`/`.yml`| Parsed and scanned as nested dict |
| TOML   | `.toml`       | Parsed and scanned as nested dict |
| Text   | `.txt`/`.log` | Scanned as flat string            |
| ENV    | `.env`        | Key-value pairs scanned           |

## StructuredScanResult

The result object provides detailed detection information:

```python
result = ai.scan_structured_input(payload)

# Top-level fields
result.action          # "allow" | "block" | "redact"
result.detections      # list of Detection objects
result.safe_payload    # payload with secrets redacted (when action is "redact")

# Each detection
d = result.detections[0]
d.type                 # "api_key", "email", "database_url", etc.
d.path                 # dot/bracket path: "user.preferences.api_key"
d.span                 # character span within the leaf value
d.masked_value         # value with secret portion masked
d.data_tags            # tags assigned: ["secret.api_key"]
```

## Configuration

```yaml title="safeai.yaml"
scan:
  structured:
    enabled: true
    max_depth: 20            # maximum nesting depth to traverse
    max_keys: 1000           # maximum total keys to scan
    action: block            # block | redact
    file_scanning:
      enabled: true
      max_file_size: 10mb    # skip files larger than this
      formats:
        - json
        - yaml
        - toml
        - env
        - text
```

| Setting         | Default | Description                                      |
|-----------------|---------|--------------------------------------------------|
| `max_depth`     | `20`    | Stop traversal at this nesting level             |
| `max_keys`      | `1000`  | Maximum fields scanned per payload               |
| `max_file_size` | `10mb`  | Skip files exceeding this size                   |

!!! tip "Performance"
    For very large payloads, tune `max_depth` and `max_keys` to balance thoroughness with scan latency. Most real-world payloads are well within the defaults.

## See Also

- [API Reference — Structured Scanning](../reference/structured.md)
- [Secret Detection guide](secret-detection.md) for flat-string scanning
- [PII Protection guide](pii-protection.md) for output-side PII handling
