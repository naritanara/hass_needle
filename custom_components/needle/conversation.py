"""Needle conversation entity."""

import json
from typing import TYPE_CHECKING, override

import probatio
from homeassistant.components.conversation import (
    AssistantContentDeltaDict,
    ChatLog,
    ConversationEntity,
    ConversationEntityFeature,
    ConversationInput,
    ConversationResult,
    ConverseError,
    ToolResultContent,
    ToolResultContentDeltaDict,
    async_get_result_from_chat_log,
    async_set_agent,
    async_unset_agent,
)
from homeassistant.components.conversation.models import (
    AbstractConversationAgent,
)
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.helpers.llm import (
    Tool,
    ToolInput,
)

import needle

from .const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import (
        AddConfigEntryEntitiesCallback,
    )

    from .data import NeedleConfigEntry


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: NeedleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Conversation set up for Needle config entry."""
    async_add_entities([NeedleConversation(config_entry)])


class NeedleConversation(ConversationEntity, AbstractConversationAgent):
    """Conversation entity for Needle."""

    _attr_has_entity_name = True
    _attr_name = "Needle"
    _attr_supported_features = ConversationEntityFeature.CONTROL
    _attr_supports_streaming = True

    def __init__(self, entry: NeedleConfigEntry) -> None:
        """Initialize the conversation entity."""
        self.entry = entry

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        async_set_agent(self.hass, self.entry, self)

    @override
    async def async_will_remove_from_hass(self) -> None:
        async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    @property
    @override
    def supported_languages(self) -> list[str]:
        return ["en"]

    async def _async_handle_message(
        self, user_input: ConversationInput, chat_log: ChatLog
    ) -> ConversationResult:
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                self.entry.options.get(CONF_LLM_HASS_API),
                user_extra_system_prompt=user_input.extra_system_prompt,
            )
        except ConverseError as err:
            return err.as_conversation_result()

        tools = []
        if chat_log.llm_api:
            tools = [
                NeedleConversation._hass_to_needle_tool(tool)
                for tool in chat_log.llm_api.tools
            ]

        agent = await self.hass.async_add_executor_job(needle.Needle, tools)
        query = user_input.text
        for _ in range(8):
            results = []
            async for msg in chat_log.async_add_delta_content_stream(
                user_input.agent_id,
                self.run_needle(agent, query),
            ):
                if isinstance(msg, ToolResultContent):
                    call_result = msg.tool_result
                    if "error_text" in call_result:
                        results.append({"error": call_result["error_text"]})
                    else:
                        results.append(call_result)

            query = json.dumps(results)

            if not chat_log.unresponded_tool_results:
                break

        return async_get_result_from_chat_log(user_input, chat_log)

    @staticmethod
    def _hass_to_needle_tool(tool: Tool) -> dict:
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": probatio.to_openapi(tool.parameters),
        }

    async def run_needle(
        self,
        agent: needle.Needle,
        query: str,
    ) -> AsyncGenerator[AssistantContentDeltaDict | ToolResultContentDeltaDict]:
        """Run the Needle agent with the given query and return the response."""
        response = await self.hass.async_add_executor_job(
            lambda: agent.run(query, max_steps=0)
        )
        reasoning = response["reasoning"]
        confidence = response["confidence"]
        thinking_content = f"{reasoning} (confidence {confidence})"

        yield AssistantContentDeltaDict(
            role="assistant", thinking_content=thinking_content
        )

        tool_calls = [
            ToolInput(call["name"], call["arguments"])
            for call in response.get("function_calls") or []
        ]
        if tool_calls:
            yield AssistantContentDeltaDict(
                tool_calls=tool_calls,
            )
        elif response.get("type") == "respond":
            yield AssistantContentDeltaDict(
                content="Done: " + query,
            )
        elif supressed_calls := response.get("suppressed_calls"):
            yield AssistantContentDeltaDict(
                content="I'm not sure if I should use this tool: "
                + ", then ".join(str(x) for x in supressed_calls),
            )
        else:
            yield AssistantContentDeltaDict(
                content="I don't know how to do that",
            )
