"""Tests for the policy template marketplace."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from safeai.templates.models import CommunityIndex, TemplateMetadata
from safeai.templates.registry import CommunityRegistry


def _sample_index() -> dict:
    return {
        "version": "v1",
        "templates": [
            {
                "name": "healthcare-hipaa",
                "description": "HIPAA policy template",
                "author": "safeai-team",
                "category": "compliance",
                "tags": ["hipaa", "healthcare"],
                "compliance_standards": ["hipaa"],
                "framework_compat": ["langchain"],
                "download_url": "https://example.com/healthcare-hipaa.yaml",
                "sha256": "",
                "version": "1.0.0",
            },
            {
                "name": "coding-agent-strict",
                "description": "Strict coding agent policy",
                "author": "safeai-team",
                "category": "agent-security",
                "tags": ["coding", "agent"],
                "compliance_standards": [],
                "framework_compat": ["claude-code"],
                "download_url": "https://example.com/coding-agent-strict.yaml",
                "sha256": "",
                "version": "1.0.0",
            },
        ],
    }


class TestCommunityIndex:
    def test_parse_index(self) -> None:
        index = CommunityIndex.model_validate(_sample_index())
        assert len(index.templates) == 2
        assert index.templates[0].name == "healthcare-hipaa"
        assert index.templates[0].category == "compliance"

    def test_empty_index(self) -> None:
        index = CommunityIndex.model_validate({"version": "v1", "templates": []})
        assert len(index.templates) == 0


class TestTemplateMetadata:
    def test_minimal_metadata(self) -> None:
        meta = TemplateMetadata(name="test")
        assert meta.name == "test"
        assert meta.category == "general"
        assert meta.tags == []


class TestCommunityRegistry:
    def test_fetch_index_from_remote(self) -> None:
        registry = CommunityRegistry(install_dir=Path("/tmp/test_safeai_templates"))
        with patch("safeai.templates.registry.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = _sample_index()
            mock_get.return_value = mock_response
            index = registry.fetch_index(force=True)
            assert len(index.templates) == 2

    def test_fetch_index_falls_back_to_bundled(self, tmp_path: Path) -> None:
        fallback_path = tmp_path / "fallback.json"
        fallback_path.write_text(json.dumps(_sample_index()))
        registry = CommunityRegistry(
            index_url="https://invalid.example.com/index.json",
            install_dir=tmp_path / "templates",
            fallback_index_path=fallback_path,
        )
        with patch("safeai.templates.registry.httpx.get", side_effect=Exception("network error")):
            index = registry.fetch_index(force=True)
            assert len(index.templates) == 2

    def test_search_by_category(self, tmp_path: Path) -> None:
        fallback_path = tmp_path / "index.json"
        fallback_path.write_text(json.dumps(_sample_index()))
        registry = CommunityRegistry(
            install_dir=tmp_path / "templates",
            fallback_index_path=fallback_path,
        )
        with patch("safeai.templates.registry.httpx.get", side_effect=Exception):
            results = registry.search(category="compliance")
            assert len(results) == 1
            assert results[0].name == "healthcare-hipaa"

    def test_search_by_tag(self, tmp_path: Path) -> None:
        fallback_path = tmp_path / "index.json"
        fallback_path.write_text(json.dumps(_sample_index()))
        registry = CommunityRegistry(
            install_dir=tmp_path / "templates",
            fallback_index_path=fallback_path,
        )
        with patch("safeai.templates.registry.httpx.get", side_effect=Exception):
            results = registry.search(tags=["coding"])
            assert len(results) == 1
            assert results[0].name == "coding-agent-strict"

    def test_search_by_compliance(self, tmp_path: Path) -> None:
        fallback_path = tmp_path / "index.json"
        fallback_path.write_text(json.dumps(_sample_index()))
        registry = CommunityRegistry(
            install_dir=tmp_path / "templates",
            fallback_index_path=fallback_path,
        )
        with patch("safeai.templates.registry.httpx.get", side_effect=Exception):
            results = registry.search(compliance="hipaa")
            assert len(results) == 1

    def test_search_by_query(self, tmp_path: Path) -> None:
        fallback_path = tmp_path / "index.json"
        fallback_path.write_text(json.dumps(_sample_index()))
        registry = CommunityRegistry(
            install_dir=tmp_path / "templates",
            fallback_index_path=fallback_path,
        )
        with patch("safeai.templates.registry.httpx.get", side_effect=Exception):
            results = registry.search(query="strict")
            assert len(results) == 1
            assert results[0].name == "coding-agent-strict"

    def test_install_with_sha256_check(self, tmp_path: Path) -> None:
        yaml_content = b"version: v1alpha1\nrules: []\n"
        sha = hashlib.sha256(yaml_content).hexdigest()
        index_data = {
            "version": "v1",
            "templates": [
                {
                    "name": "test-template",
                    "description": "Test",
                    "author": "test",
                    "category": "general",
                    "tags": [],
                    "compliance_standards": [],
                    "framework_compat": [],
                    "download_url": "https://example.com/test.yaml",
                    "sha256": sha,
                    "version": "1.0.0",
                }
            ],
        }
        fallback_path = tmp_path / "index.json"
        fallback_path.write_text(json.dumps(index_data))
        install_dir = tmp_path / "templates"
        registry = CommunityRegistry(
            install_dir=install_dir,
            fallback_index_path=fallback_path,
        )
        with (
            patch("safeai.templates.registry.httpx.get") as mock_get,
        ):
            # Index fetch fails, falls back
            mock_get.side_effect = [
                Exception("network"),
                MagicMock(status_code=200, content=yaml_content),
            ]
            # Install call uses httpx.get for download
            with patch("safeai.templates.registry.httpx.get") as mock_get2:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.content = yaml_content
                mock_get2.return_value = mock_response
                # Force fallback index
                registry._index = CommunityIndex.model_validate(index_data)
                path = registry.install("test-template")
                assert Path(path).exists()
                assert (install_dir / "test-template.yaml").exists()
                assert (install_dir / "test-template.meta.json").exists()

    def test_install_sha256_mismatch_rejected(self, tmp_path: Path) -> None:
        index_data = {
            "version": "v1",
            "templates": [
                {
                    "name": "bad-template",
                    "description": "Test",
                    "author": "test",
                    "category": "general",
                    "tags": [],
                    "compliance_standards": [],
                    "framework_compat": [],
                    "download_url": "https://example.com/bad.yaml",
                    "sha256": "deadbeef" * 8,
                    "version": "1.0.0",
                }
            ],
        }
        registry = CommunityRegistry(
            install_dir=tmp_path / "templates",
            fallback_index_path=tmp_path / "nonexistent.json",
        )
        registry._index = CommunityIndex.model_validate(index_data)
        with patch("safeai.templates.registry.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, content=b"tampered content")
            with pytest.raises(ValueError, match="SHA256 mismatch"):
                registry.install("bad-template")

    def test_list_installed(self, tmp_path: Path) -> None:
        install_dir = tmp_path / "templates"
        install_dir.mkdir()
        (install_dir / "my-template.yaml").write_text("version: v1\n")
        (install_dir / "my-template.meta.json").write_text(json.dumps({"name": "my-template", "author": "test"}))
        registry = CommunityRegistry(install_dir=install_dir)
        installed = registry.list_installed()
        assert len(installed) == 1
        assert installed[0]["name"] == "my-template"

    def test_uninstall(self, tmp_path: Path) -> None:
        install_dir = tmp_path / "templates"
        install_dir.mkdir()
        (install_dir / "remove-me.yaml").write_text("version: v1\n")
        (install_dir / "remove-me.meta.json").write_text("{}")
        registry = CommunityRegistry(install_dir=install_dir)
        assert registry.uninstall("remove-me") is True
        assert not (install_dir / "remove-me.yaml").exists()
        assert not (install_dir / "remove-me.meta.json").exists()


class TestCatalogIntegration:
    def test_catalog_lists_all_sources(self, tmp_path: Path) -> None:
        from safeai.templates.catalog import PolicyTemplateCatalog

        install_dir = tmp_path / "community"
        install_dir.mkdir()
        (install_dir / "community-tmpl.yaml").write_text("version: v1\nrules: []\n")
        registry = CommunityRegistry(install_dir=install_dir)
        catalog = PolicyTemplateCatalog(community_registry=registry)
        templates = catalog.list_templates()
        names = [t["name"] for t in templates]
        sources = [t["source"] for t in templates]
        assert "community-tmpl" in names
        assert "community" in sources


class TestCLISearchInstall:
    def test_search_command(self) -> None:
        from click.testing import CliRunner

        from safeai.cli.templates import templates_group

        runner = CliRunner()
        with patch("safeai.templates.registry.CommunityRegistry.search") as mock_search:
            mock_search.return_value = [
                TemplateMetadata(
                    name="healthcare-hipaa",
                    description="HIPAA template",
                    category="compliance",
                    author="safeai-team",
                )
            ]
            result = runner.invoke(templates_group, ["search", "--category", "compliance"])
            assert result.exit_code == 0
            assert "healthcare-hipaa" in result.output

    def test_install_command(self) -> None:
        from click.testing import CliRunner

        from safeai.cli.templates import templates_group

        runner = CliRunner()
        with patch("safeai.templates.registry.CommunityRegistry.install") as mock_install:
            mock_install.return_value = Path("/tmp/test/my-template.yaml")
            result = runner.invoke(templates_group, ["install", "my-template"])
            assert result.exit_code == 0
            assert "installed" in result.output
