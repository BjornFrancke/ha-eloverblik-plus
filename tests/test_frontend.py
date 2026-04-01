"""Tests for bundled Lovelace frontend registration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import (
    CONF_RESOURCE_TYPE_WS,
    LOVELACE_DATA,
    MODE_STORAGE,
    MODE_YAML,
)
from homeassistant.const import CONF_URL

from custom_components.eloverblik_plus.frontend import (
    CARD_RESOURCE_URL,
    FRONTEND_URL_BASE,
    async_setup_frontend,
)


async def test_async_setup_frontend_registers_static_path_and_resource() -> None:
    """Test the bundled card is served and registered once."""
    test_hass = SimpleNamespace(
        data={},
        http=SimpleNamespace(async_register_static_paths=AsyncMock()),
    )
    resources = SimpleNamespace(
        async_get_info=AsyncMock(return_value={"resources": 0}),
        async_items=lambda: [],
        async_create_item=AsyncMock(),
    )
    test_hass.data[LOVELACE_DATA] = SimpleNamespace(
        resource_mode=MODE_STORAGE,
        resources=resources,
    )

    await async_setup_frontend(test_hass)
    await async_setup_frontend(test_hass)

    test_hass.http.async_register_static_paths.assert_awaited_once()
    [static_config] = test_hass.http.async_register_static_paths.await_args.args[0]
    assert isinstance(static_config, StaticPathConfig)
    assert static_config.url_path == FRONTEND_URL_BASE
    assert static_config.path.endswith("/custom_components/eloverblik_plus/frontend")
    assert static_config.cache_headers is False
    resources.async_get_info.assert_awaited_once()
    resources.async_create_item.assert_awaited_once_with(
        {
            CONF_RESOURCE_TYPE_WS: "module",
            CONF_URL: CARD_RESOURCE_URL,
        }
    )


async def test_async_setup_frontend_skips_yaml_resource_registration() -> None:
    """Test YAML-mode Lovelace skips automatic resource creation."""
    test_hass = SimpleNamespace(
        data={},
        http=SimpleNamespace(async_register_static_paths=AsyncMock()),
    )
    resources = SimpleNamespace(
        async_get_info=AsyncMock(),
        async_items=lambda: [],
        async_create_item=AsyncMock(),
    )
    test_hass.data[LOVELACE_DATA] = SimpleNamespace(
        resource_mode=MODE_YAML,
        resources=resources,
    )

    await async_setup_frontend(test_hass)

    test_hass.http.async_register_static_paths.assert_awaited_once()
    resources.async_get_info.assert_not_awaited()
    resources.async_create_item.assert_not_awaited()


def test_readme_example_matches_shipped_custom_card_name() -> None:
    """Test documentation references the shipped custom card and editor hooks."""
    repo_root = Path(__file__).resolve().parents[1]
    readme = (repo_root / "README.md").read_text()
    frontend_js = (
        repo_root
        / "custom_components"
        / "eloverblik_plus"
        / "frontend"
        / "eloverblik-hourly-card.js"
    ).read_text()

    assert "type: custom:eloverblik-hourly-card" in readme
    assert 'customElements.define("eloverblik-hourly-card"' in frontend_js
    assert '"eloverblik-hourly-card-editor"' in frontend_js
    assert "static getStubConfig(hass)" in frontend_js
