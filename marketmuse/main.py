import asyncio
import logging
import argparse

from dataclasses import dataclass
from typing import List

from autogen_core import TRACE_LOGGER_NAME, AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, TopicId, message_handler, type_subscription
from autogen_core.models import ChatCompletionClient, LLMMessage, SystemMessage, UserMessage
from autogen_core.tool_agent import ToolAgent, tool_agent_caller_loop
from autogen_core.tools import FunctionTool, Tool, ToolSchema
from autogen_ext.models.openai import OpenAIChatCompletionClient

from tools.web_search import web_search

OLLAMA_OPENAI_BASE_URL="http://0.0.0.0:11434/v1"
OPENAI_BASE_URL="https://api.openai.com/v1"

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(TRACE_LOGGER_NAME)

def get_model_client(
        openai_base_url : str, 
        model_name : str, 
        vision_capabilities : bool = False, 
        api_key : str = "none") -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=model_name,
        api_key=api_key,
        base_url=openai_base_url,
        model_capabilities={
            "json_output": True,
            "vision": vision_capabilities,
            "function_calling": True,
        },
    )

@dataclass
class Message:
    content: str

sdr_topic_type = "SDRAgent"
account_director_type = "AccountDirectorAgent"

@type_subscription(topic_type=sdr_topic_type)
class SDRAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, tool_schema: List[ToolSchema], tool_agent_type: str) -> None:
        super().__init__("A prospect information extractor agent with tools")
        self._system_messages : List[LLMMessage] = [SystemMessage(
            content=(
                "You are tasked with providing detailed and actionable information about a sales lead to support an Account Director's outreach efforts"
                "Please execute the following 5 queries to bolster your efforts: 1) {prospect full name} {company name} 2) {prospect full name} {company name} site: zoominfo.com 3) '{company name}' about us 4) '{company name}' competitors 5) '{company name}' recent news or announcements"
                "Generate a comprehensive and concise summary of the lead and their company, ensuring it is easy to understand and actionable for an Account Director using this structure: \n\n"
                "1. Lead Overview: Provide basic details about the lead 2. Company Insights: Summarize key information about the company 3. Lead-Specific Information: Provide role-specific and relevant details about the lead 4) Relationship Context: Identify any pre-existing relationships or connections 5) Opportunity Insights: Highlight how your services or solutions could address their needs 6) Next Steps: Suggest clear actions to move the lead forward in the sales process "
            )
        )]
        self._model_client = model_client
        self._tool_schema = tool_schema
        self._tool_agent_id = AgentId(tool_agent_type, self.id.key)

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> None:
        logger.debug(f"Received message: {message.content}")
        session: List[LLMMessage] = self._system_messages + [UserMessage(content=message.content, source=self.id.key)]
        messages = await tool_agent_caller_loop(
            self,
            tool_agent_id=self._tool_agent_id,
            model_client=self._model_client,
            input_messages=session,
            tool_schema=self._tool_schema,
            cancellation_token=ctx.cancellation_token,
        )
        assistant_generated_message = messages[-1].content
        assert isinstance(assistant_generated_message, str)
        print(f"\n{'-'*80}\n{self.id.type}:\n{assistant_generated_message}")
        await self.publish_message(Message(content=assistant_generated_message), topic_id=TopicId(account_director_type, source=self.id.key))


@type_subscription(topic_type=account_director_type)
class AccountDirectorAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("An account director agent.")
        self._system_message = SystemMessage(
            content=(
                "You are an Account Director AI agent responsible for crafting strategic outreach plans based on sales lead information."
                "Your task is to Analyze the provided information. Identify key opportunities and challenges. Recommend a tailored outreach strategy. Outline next steps to engage the lead effectively."
            )
        )
        self._model_client = model_client

    @message_handler
    async def handle_intermediate_text(self, message: Message, ctx: MessageContext) -> None:
        prompt = f"Below is the info about the prospect:\n\n{message.content}"

        llm_result = await self._model_client.create(
            messages=[self._system_message, UserMessage(content=prompt, source=self.id.key)],
            cancellation_token=ctx.cancellation_token,
        )
        response = llm_result.content
        assert isinstance(response, str)
        print(f"{'-'*80}\n{self.id.type}:\n{response}")

async def main():
    parser = argparse.ArgumentParser(description="Configure the AI agent.")
    parser.add_argument("--name", required=True, help="Full name of the lead to research")
    parser.add_argument("--company-name", required=True, help="Company name to research")
    parser.add_argument("--model-name", required=True, help="The name of the model to use.")
    parser.add_argument("--openai-local-url", required=False, help="The local URL to your openapi enabled server like ollama. Will default to base open ai URL if omitted")
    parser.add_argument("--api-key", required=False, help="OpenAI api key. Only required if you are using openai server or your local server requires a key")
    parser.add_argument("--vision-enabled", help="Model supports Vision.")
    args = parser.parse_args()

    client_args = {"model_name": args.model_name, "openai_base_url": OPENAI_BASE_URL}
    if args.api_key:
        client_args["api_key"] = args.api_key
    if args.vision_enabled is not None:
        client_args["vision_enabled"] = args.vision_enabled
    if args.openai_local_url:
        client_args["openai_base_url"] = args.openai_local_url
    model_client = get_model_client(**client_args)

    runtime = SingleThreadedAgentRuntime()

    tools: List[Tool] = [FunctionTool(web_search, description="Run a web search and return contents of top results", name="web_search")]

    await ToolAgent.register(runtime, "web_search_agent", lambda: ToolAgent("web_search_agent", tools))
    await SDRAgent.register(
        runtime,
        type=sdr_topic_type,
        factory=lambda: SDRAgent(
            model_client=model_client, tool_schema=[tool.schema for tool in tools], tool_agent_type="web_search_agent"
        ),
    )
    await AccountDirectorAgent.register(runtime, type=account_director_type, factory=lambda: AccountDirectorAgent(model_client=model_client))

    runtime.start()
    await runtime.publish_message(
        Message(content=f"Sales lead - Name: {args.name}, Current Company: {args.company_name}"),
        topic_id=TopicId(sdr_topic_type, source="default"),
    )
    await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())
