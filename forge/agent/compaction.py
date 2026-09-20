"""Context compaction: compresses long history into summaries to stay within model token limits."""

from typing import Any, Dict, List


class ContextCompactor:
    """Summarizes older conversation turns while keeping recent context and user goals intact."""

    def __init__(self, keep_recent_turns: int = 10, max_chars_per_tool_result: int = 2500):
        self.keep_recent_turns = keep_recent_turns
        self.max_chars_per_tool_result = max_chars_per_tool_result

    def compact(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prunes and compacts older messages if history has grown excessively long."""
        if len(messages) <= self.keep_recent_turns + 2:
            # Short history, just truncate oversized tool outputs if necessary
            return [self._truncate_tool_output(m) for m in messages]

        # Keep system prompt (if first)
        result: List[Dict[str, Any]] = []
        start_idx = 0
        if messages and messages[0].get("role") == "system":
            result.append(messages[0])
            start_idx = 1

        # Keep initial user prompt
        if start_idx < len(messages):
            result.append(messages[start_idx])
            start_idx += 1

        # Partition remaining messages into middle (to compact) and recent (to keep verbatim)
        remaining = messages[start_idx:]
        if len(remaining) <= self.keep_recent_turns:
            result.extend([self._truncate_tool_output(m) for m in remaining])
            return result

        split_point = len(remaining) - self.keep_recent_turns
        older_messages = remaining[:split_point]
        recent_messages = remaining[split_point:]

        # Create compact summary of older turns
        summary_lines = ["--- Prior Conversation Summary ---"]
        for m in older_messages:
            role = m.get("role")
            content = str(m.get("content", ""))
            if role == "user":
                summary_lines.append(f"User requested: {content[:150]}")
            elif role == "assistant":
                if m.get("tool_calls"):
                    tool_names = [tc.name if hasattr(tc, "name") else tc.get("name") for tc in m["tool_calls"]]
                    summary_lines.append(f"Agent invoked tools: {', '.join(tool_names)}")
                elif content:
                    summary_lines.append(f"Agent reported: {content[:120]}")
            elif role == "tool":
                tool_name = m.get("name") or "Tool"
                summary_lines.append(f"{tool_name} returned ({len(content)} chars)")

        summary_message = {
            "role": "user",
            "content": "\n".join(summary_lines),
        }
        result.append(summary_message)
        result.extend([self._truncate_tool_output(m) for m in recent_messages])

        return result

    def _truncate_tool_output(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Truncates single tool outputs that exceed max_chars_per_tool_result."""
        if message.get("role") != "tool":
            return message

        content = str(message.get("content", ""))
        if len(content) > self.max_chars_per_tool_result:
            half = self.max_chars_per_tool_result // 2
            truncated = (
                content[:half]
                + f"\n\n... [Output truncated: {len(content) - self.max_chars_per_tool_result} characters omitted] ...\n\n"
                + content[-half:]
            )
            new_msg = dict(message)
            new_msg["content"] = truncated
            return new_msg

        return message
