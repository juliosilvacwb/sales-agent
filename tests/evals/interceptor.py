"""LangChain Callback Interceptor to capture intermediate structured tool execution data."""
from dataclasses import dataclass
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


@dataclass
class ToolInvocationRecord:
    """Record of an intercepted tool execution."""
    tool_name: str
    tool_input: Any
    run_id: str
    raw_output: Optional[Any] = None
    parsed_output: Optional[Any] = None
    error: Optional[str] = None


class ToolInterceptionCallbackHandler(BaseCallbackHandler):
    """Callback handler that intercepts and parses tool calls during agent execution."""

    def __init__(self) -> None:
        super().__init__()
        self._invocations: List[ToolInvocationRecord] = []
        self._run_map: Dict[str, ToolInvocationRecord] = {}

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Invoked when a tool starts execution."""
        tool_name = serialized.get("name") or kwargs.get("name", "unknown_tool")
        run_id_str = str(run_id)
        
        record = ToolInvocationRecord(
            tool_name=tool_name,
            tool_input=inputs if inputs is not None else input_str,
            run_id=run_id_str,
        )
        self._invocations.append(record)
        self._run_map[run_id_str] = record
        logger.info("[EVAL_INTERCEPTOR] Tool started: %s (run_id=%s)", tool_name, run_id_str)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Invoked when a tool successfully finishes execution."""
        run_id_str = str(run_id)
        record = self._run_map.get(run_id_str)
        if not record and self._invocations:
            record = self._invocations[-1]

        # Extract string content if output is a BaseMessage (e.g., ToolMessage)
        raw_val = output.content if isinstance(output, BaseMessage) else output
        parsed_val: Any = raw_val

        if isinstance(raw_val, str):
            try:
                parsed_val = json.loads(raw_val)
            except (json.JSONDecodeError, TypeError):
                parsed_val = raw_val

        if record:
            record.raw_output = raw_val
            record.parsed_output = parsed_val
            logger.info("[EVAL_INTERCEPTOR] Tool ended: %s (run_id=%s)", record.tool_name, run_id_str)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Invoked when a tool fails with an exception."""
        run_id_str = str(run_id)
        record = self._run_map.get(run_id_str)
        if not record and self._invocations:
            record = self._invocations[-1]

        if record:
            record.error = str(error)
            logger.warning("[EVAL_INTERCEPTOR] Tool error: %s (run_id=%s) -> %s", record.tool_name, run_id_str, error)

    @property
    def has_invocations(self) -> bool:
        """Returns True if at least one tool invocation was intercepted."""
        return len(self._invocations) > 0

    @property
    def invocation_count(self) -> int:
        """Returns the total number of intercepted tool calls."""
        return len(self._invocations)

    @property
    def actual_tool_name(self) -> Optional[str]:
        """Returns the name of the first intercepted tool."""
        return self._invocations[0].tool_name if self._invocations else None

    @property
    def parsed_tool_output(self) -> Optional[Any]:
        """Returns the parsed structured output of the first intercepted tool."""
        return self._invocations[0].parsed_output if self._invocations else None

    @property
    def raw_tool_output(self) -> Optional[Any]:
        """Returns the raw output of the first intercepted tool."""
        return self._invocations[0].raw_output if self._invocations else None

    @property
    def all_invocations(self) -> List[ToolInvocationRecord]:
        """Returns all intercepted tool invocation records."""
        return list(self._invocations)

    def clear(self) -> None:
        """Clears all captured tool invocations."""
        self._invocations.clear()
        self._run_map.clear()
