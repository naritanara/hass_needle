"""Adds config flow for Blueprint."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

import probatio
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigFlow,
    ConfigFlowContext,
    ConfigFlowResult,
    FlowType,
    OptionsFlow,
)
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from custom_components.needle.data import NeedleConfigEntry


class NeedleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Needle."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,  # noqa: ARG002
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        return self.async_create_entry(
            title="Needle",
            data={},
        )

    async def async_on_create_entry(
        self, result: ConfigFlowResult
    ) -> ConfigFlowResult:
        """Trigger the options flow after the config entry is created."""
        if "result" not in result:
            warnings.warn("missing result in config flow result", stacklevel=2)
            return result

        options_result = await self.hass.config_entries.options.async_init(
            result["result"].entry_id,
            context=ConfigFlowContext(source=SOURCE_USER),
        )
        result["next_flow"] = FlowType.OPTIONS_FLOW, options_result["flow_id"]
        return result

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: NeedleConfigEntry,  # noqa: ARG004
    ) -> NeedleOptionsFlow:
        """Return the options flow."""
        return NeedleOptionsFlow()


class NeedleOptionsFlow(OptionsFlow):
    """Options flow for the Needle integration."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.options_schema,  # pyright: ignore[reportArgumentType]
        )

    @property
    def options_schema(
        self,
    ) -> probatio.Schema:
        """Return the options schema."""
        apis = [
            SelectOptionDict(
                label=api.name,
                value=api.id,
            )
            for api in llm.async_get_apis(self.hass)
        ]

        return probatio.Schema(
            {
                probatio.Optional(
                    CONF_LLM_HASS_API,
                    description={
                        "suggested_value": self.config_entry.options.get(
                            CONF_LLM_HASS_API
                        )
                    },
                ): SelectSelector(
                    SelectSelectorConfig(options=apis, multiple=True)
                )
            }
        )
