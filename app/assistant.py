import json
from typing import Any, Dict, Optional, Tuple

from app.llm_client import llm_client
from app.models import ToolCall
from app.tools import registry

TOOLS_SPEC = """
You can decide whether to call one tool before answering.
Return ONLY valid JSON with this exact schema:
{"tool": "none|web_search|firestore_lookup|call_cloud_function|shell_command|http_api", "arguments": {...}, "rationale": "short reason"}

Guidelines:
- Use web_search for fresh public web info.
- Use firestore_lookup for app-stored facts.
- Use call_cloud_function for task automation actions.
- For scheduled or on-demand news briefings, use call_cloud_function with action run_daily_news_digest.
- Use shell_command only for harmless local inspection commands.
- Use http_api for allow-listed APIs.
- If no tool is needed, set tool to none.
""".strip()


class AssistantService:
    async def _plan_tool_use(self, user_text: str) -> ToolCall:
        prompt = (
            f"{TOOLS_SPEC}\n\n"
            f"User message: {user_text}\n"
            "Return JSON now."
        )
        decision = llm_client.generate_json(prompt)
        try:
            return ToolCall(**decision)
        except Exception:
            return ToolCall(tool="none", arguments={}, rationale="Fallback on parse failure")

    async def _execute_tool(self, tool_call: ToolCall) -> Dict[str, Any]:
        if tool_call.tool == "web_search":
            return await registry.web_search(tool_call.arguments.get("query", ""))
        if tool_call.tool == "firestore_lookup":
            return await registry.firestore_lookup(
                tool_call.arguments.get("collection", "knowledge"),
                tool_call.arguments.get("doc_id", ""),
            )
        if tool_call.tool == "call_cloud_function":
            return await registry.call_cloud_function(
                tool_call.arguments.get("action", ""),
                tool_call.arguments.get("payload", {}),
            )
        if tool_call.tool == "shell_command":
            return await registry.shell_command(tool_call.arguments.get("command", ""))
        if tool_call.tool == "http_api":
            return await registry.http_api(tool_call.arguments.get("url", ""))
        return {"ok": True, "message": "No tool used"}

    async def respond(self, user_text: str, enable_tools: bool = True) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        tool_name = None
        tool_result = None

        if enable_tools:
            tool_call = await self._plan_tool_use(user_text)
            if tool_call.tool != "none":
                tool_name = tool_call.tool
                tool_result = await self._execute_tool(tool_call)

        final_prompt = (
            "You are a practical cloud AI assistant. "
            "Provide concise and useful answers.\n\n"
            f"User input: {user_text}\n"
            f"Tool used: {tool_name or 'none'}\n"
            f"Tool result JSON: {json.dumps(tool_result or {}, ensure_ascii=True)}\n"
            "Write the final response for the user."
        )
        answer = llm_client.generate_text(final_prompt)
        return answer, tool_name, tool_result


assistant_service = AssistantService()
