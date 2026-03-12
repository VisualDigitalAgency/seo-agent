"""
Base Agent — HTTP Tool-Calling Version
Flow:
  1. Agent fetches available tools from tool server GET /tools
  2. Sends to OpenRouter with tools array
  3. If model returns tool_calls → POST each to tool server → feed results back
  4. Loop until model returns final text response (no more tool calls)
  5. Parse JSON from final response
"""

import os
import json
import re
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


TOOL_SERVER_URL = os.environ.get("TOOL_SERVER_URL", "http://localhost:8001")
OPENROUTER_URL  = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterRateLimitError(Exception):
    pass

class OpenRouterConnectionError(Exception):
    pass


class BaseAgent:

    def __init__(self, pipeline):
        self.pipeline   = pipeline
        self.config     = pipeline.config.get("model", {})

        # Per-agent model override support
        # config.json: {"model": {"content_model": "anthropic/claude-sonnet-4-5"}}
        agent_class = self.__class__.__name__.lower().replace("agent", "")
        self.model = (
            self.config.get(f"{agent_class}_model")
            or self.config.get("model", "anthropic/claude-sonnet-4-5")
        )

        self.max_tokens  = self.config.get("max_tokens", 4096)
        self.temperature = self.config.get("temperature", 0.3)
        self.api_key     = os.environ.get("OPENROUTER_API_KEY", "")

        # Fetch tool definitions from tool server once per agent instance
        self._tools = self._fetch_tools()

    # ── Tool server interaction ───────────────────────────────────────────────

    def _fetch_tools(self) -> list:
        """GET /tools from tool server to get OpenAI-compatible tool definitions"""
        try:
            resp = requests.get(f"{TOOL_SERVER_URL}/tools", timeout=5)
            if resp.status_code == 200:
                tools = resp.json().get("tools", [])
                self.log(f"Loaded {len(tools)} tools from tool server")
                return tools
        except Exception as e:
            self.log(f"Tool server not reachable: {e} — running without tools", level="WARNING")
        return []

    def _call_tool(self, tool_name: str, tool_args: dict) -> str:
        """
        POST to tool server to execute a tool call.
        Returns the result as a JSON string (to feed back to the LLM).
        """
        self.log(f"  → Tool call: {tool_name}({json.dumps(tool_args)[:120]})")
        try:
            resp = requests.post(
                f"{TOOL_SERVER_URL}/tools/{tool_name}",
                json=tool_args,
                timeout=30
            )
            if resp.status_code == 200:
                result = resp.json()
                self.log(f"  ← Tool result: {str(result)[:120]}")
                return json.dumps(result)

            # Tool server returned an error (e.g. 403 blocked by permission guard)
            error_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"error": resp.text}
            self.log(f"  ← Tool error {resp.status_code}: {error_body}", level="WARNING")
            return json.dumps({"error": f"Tool server returned {resp.status_code}", "detail": error_body})

        except requests.exceptions.Timeout:
            return json.dumps({"error": f"Tool {tool_name} timed out"})
        except Exception as e:
            self.log(f"  ← Tool call failed: {e}", level="ERROR")
            return json.dumps({"error": str(e)})

    # ── Main LLM call with tool loop ─────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        retry=retry_if_exception_type((OpenRouterRateLimitError, OpenRouterConnectionError))
    )
    def call_claude(self, system_prompt: str, user_prompt: str, expect_json: bool = True) -> dict | str:
        """
        Call OpenRouter with tool support.
        Automatically handles multi-turn tool_use → tool_result loops.
        Returns parsed JSON dict (if expect_json=True) or raw string.
        """
        if expect_json:
            system_prompt += (
                "\n\nCRITICAL: Your FINAL response (after all tool calls) must be valid JSON only. "
                "No markdown fences, no explanation, no backticks. Start with { or [ directly."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  os.environ.get("APP_URL", "http://localhost:3000"),
            "X-Title":       "SEO Agent",
        }

        messages = [{"role": "user", "content": user_prompt}]

        # Tool-calling loop — runs until model stops calling tools
        max_tool_rounds = 10
        for round_num in range(max_tool_rounds):
            payload = {
                "model":       self.model,
                "max_tokens":  self.max_tokens,
                "temperature": self.temperature,
                "system":      system_prompt,
                "messages":    messages,
            }

            # Only attach tools if tool server is available
            if self._tools:
                payload["tools"]       = self._tools
                payload["tool_choice"] = "auto"

            self.log(f"OpenRouter call [{self.model}] — round {round_num + 1}")

            try:
                resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
            except requests.exceptions.ConnectionError as e:
                raise OpenRouterConnectionError(f"Connection failed: {e}")

            if resp.status_code == 429:
                raise OpenRouterRateLimitError(f"Rate limited: {resp.text}")
            if resp.status_code == 401:
                raise ValueError("Invalid OPENROUTER_API_KEY")
            if resp.status_code != 200:
                raise Exception(f"OpenRouter error {resp.status_code}: {resp.text}")

            data    = resp.json()
            if "error" in data:
                raise Exception(f"OpenRouter error: {data['error'].get('message', data['error'])}")

            choice  = data["choices"][0]
            message = choice["message"]
            finish  = choice.get("finish_reason", "")

            # ── Model wants to call tools ─────────────────────────────────────
            if finish == "tool_calls" or message.get("tool_calls"):
                tool_calls = message.get("tool_calls", [])
                self.log(f"Model requesting {len(tool_calls)} tool call(s)...")

                # Add assistant message with tool_calls to history
                messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_calls})

                # Execute each tool and add results
                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        tool_args = json.loads(tc["function"].get("arguments", "{}"))
                    except json.JSONDecodeError:
                        tool_args = {}

                    tool_result = self._call_tool(tool_name, tool_args)

                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc["id"],
                        "content":      tool_result,
                    })

                # Continue loop — send results back to model
                continue

            # ── Model gave a final response ───────────────────────────────────
            content = (message.get("content") or "").strip()

            if not expect_json:
                return content

            # Parse JSON from final response
            if content.startswith("```"):
                lines   = content.split("\n")
                start   = 1
                end     = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                content = "\n".join(lines[start:end]).strip()

            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                self.log(f"JSON parse failed: {e}. Trying regex extraction...", level="WARNING")
                match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                raise ValueError(f"Model returned non-JSON: {content[:300]}")

        raise Exception(f"Tool loop exceeded {max_tool_rounds} rounds without a final response")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def log(self, msg: str, level: str = "INFO"):
        self.pipeline.log(msg, level)

    def load_skill(self, skill_name: str) -> str:
        return self.pipeline.load_skill(skill_name)

    def build_context_summary(self, context: dict) -> str:
        parts = []
        if context.get("keyword_research"):
            kw = context["keyword_research"]
            parts.append(f"Primary keyword: {kw.get('primary', '')}")
            parts.append(f"Secondary keywords: {', '.join(kw.get('secondary', [])[:5])}")
            parts.append(f"Search intent: {kw.get('intent', '')}")
        if context.get("serp_analysis"):
            serp = context["serp_analysis"]
            parts.append(f"SERP gaps: {', '.join(serp.get('content_gaps', [])[:3])}")
        return "\n".join(parts) if parts else "No prior context"
