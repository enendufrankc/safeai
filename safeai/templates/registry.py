"""Community template registry: fetch, search, install, and manage templates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx

from safeai.templates.models import CommunityIndex, TemplateMetadata

_DEFAULT_INDEX_URL = (
    "https://raw.githubusercontent.com/enendufrankc/safeai/main/"
    "safeai/config/defaults/community_index.json"
)
_INSTALL_DIR = Path("~/.safeai/templates").expanduser()
_CACHE_DIR = Path("~/.safeai/cache").expanduser()


class CommunityRegistry:
    """Fetch, search, install, and manage community policy templates."""

    def __init__(
        self,
        *,
        index_url: str = _DEFAULT_INDEX_URL,
        install_dir: Path | None = None,
        fallback_index_path: Path | None = None,
    ) -> None:
        self.index_url = index_url
        self.install_dir = install_dir or _INSTALL_DIR
        self._fallback_index_path = fallback_index_path or (
            Path(__file__).resolve().parents[1] / "config" / "defaults" / "community_index.json"
        )
        self._index: CommunityIndex | None = None

    def fetch_index(self, *, force: bool = False) -> CommunityIndex:
        """Fetch community index from remote URL with local cache fallback."""
        if self._index is not None and not force:
            return self._index
        # Try remote first
        try:
            response = httpx.get(self.index_url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                self._index = CommunityIndex.model_validate(data)
                self._cache_index(data)
                return self._index
        except Exception:
            pass
        # Try local cache
        cached = self._load_cached_index()
        if cached:
            self._index = cached
            return self._index
        # Fallback to bundled index
        self._index = self._load_fallback_index()
        return self._index

    def search(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        compliance: str | None = None,
    ) -> list[TemplateMetadata]:
        """Search the community index."""
        index = self.fetch_index()
        results: list[TemplateMetadata] = []
        for tmpl in index.templates:
            if category and tmpl.category.lower() != category.lower():
                continue
            if tags and not set(t.lower() for t in tags).intersection(
                set(t.lower() for t in tmpl.tags)
            ):
                continue
            if compliance and compliance.lower() not in [
                s.lower() for s in tmpl.compliance_standards
            ]:
                continue
            if query:
                q = query.lower()
                searchable = f"{tmpl.name} {tmpl.description} {' '.join(tmpl.tags)}".lower()
                if q not in searchable:
                    continue
            results.append(tmpl)
        return results

    def install(self, name: str) -> Path:
        """Download and install a template by name. Returns installed path."""
        index = self.fetch_index()
        template = None
        for tmpl in index.templates:
            if tmpl.name.lower() == name.lower():
                template = tmpl
                break
        if template is None:
            raise KeyError(f"Template '{name}' not found in community index.")
        if not template.download_url:
            raise ValueError(f"Template '{name}' has no download URL.")
        response = httpx.get(template.download_url, timeout=15.0)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to download template: HTTP {response.status_code}")
        content = response.content
        if template.sha256:
            actual_hash = hashlib.sha256(content).hexdigest()
            if actual_hash != template.sha256:
                raise ValueError(
                    f"SHA256 mismatch for '{name}': "
                    f"expected {template.sha256}, got {actual_hash}"
                )
        self.install_dir.mkdir(parents=True, exist_ok=True)
        dest = self.install_dir / f"{name}.yaml"
        dest.write_bytes(content)
        meta_path = self.install_dir / f"{name}.meta.json"
        meta_path.write_text(
            json.dumps(template.model_dump(), indent=2),
            encoding="utf-8",
        )
        return dest

    def list_installed(self) -> list[dict[str, Any]]:
        """List locally installed community templates."""
        if not self.install_dir.exists():
            return []
        rows: list[dict[str, Any]] = []
        for yaml_file in sorted(self.install_dir.glob("*.yaml")):
            meta_file = yaml_file.with_suffix(".meta.json")
            meta: dict[str, Any] = {"name": yaml_file.stem, "source": "community"}
            if meta_file.exists():
                try:
                    meta.update(json.loads(meta_file.read_text(encoding="utf-8")))
                except Exception:
                    pass
            meta["path"] = str(yaml_file)
            rows.append(meta)
        return rows

    def uninstall(self, name: str) -> bool:
        """Remove an installed template."""
        yaml_path = self.install_dir / f"{name}.yaml"
        meta_path = self.install_dir / f"{name}.meta.json"
        removed = False
        if yaml_path.exists():
            yaml_path.unlink()
            removed = True
        if meta_path.exists():
            meta_path.unlink()
            removed = True
        return removed

    def _cache_index(self, data: Any) -> None:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = _CACHE_DIR / "community_index.json"
            cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_cached_index(self) -> CommunityIndex | None:
        cache_file = _CACHE_DIR / "community_index.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return CommunityIndex.model_validate(data)
        except Exception:
            return None

    def _load_fallback_index(self) -> CommunityIndex:
        if self._fallback_index_path and self._fallback_index_path.exists():
            try:
                data = json.loads(self._fallback_index_path.read_text(encoding="utf-8"))
                return CommunityIndex.model_validate(data)
            except Exception:
                pass
        return CommunityIndex()
