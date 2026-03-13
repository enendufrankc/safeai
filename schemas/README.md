# Schemas

The JSON Schema files in this directory are copies of the canonical schemas
bundled inside the `safeai` package at `safeai/schemas/v1alpha1/`.

They are provided at the project root for convenience during development
(e.g., IDE validation, `safeai validate`). The package-bundled copies are
the authoritative source.

To keep them in sync after editing the canonical copy:

```bash
cp safeai/schemas/v1alpha1/*.json schemas/v1alpha1/
```
