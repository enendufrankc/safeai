# Schemas

The canonical JSON schemas for SafeAI configuration files live inside the
Python package at:

```
safeai/schemas/v1alpha1/
├── agent-identity.schema.json
├── memory.schema.json
├── policy.schema.json
└── tool-contract.schema.json
```

These schemas are bundled with the `safeai-sdk` package and used at runtime
for configuration validation. Refer to those files as the single source of truth.
