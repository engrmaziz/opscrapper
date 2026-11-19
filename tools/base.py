"""
Base tool interfaces and registry for modular tool and MCP (Model Context Protocol) injection.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
import inspect
from pydantic import BaseModel, Field


class ToolMetadata(BaseModel):
    """Metadata describing a registered agent tool."""

    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="Description of what the tool accomplishes")
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for parameters")
    is_async: bool = Field(default=True, description="Whether tool execution is async")


class BaseAgentTool(ABC):
    """Abstract base class for all Antigravity agent tools."""

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Executes the tool logic with given arguments."""
        pass

    def get_metadata(self) -> ToolMetadata:
        """Returns the structured tool metadata."""
        return ToolMetadata(
            name=self.name,
            description=self.description,
            is_async=inspect.iscoroutinefunction(self.execute),
        )


class ToolRegistry:
    """Central registry to manage custom scraping tools and external MCP servers."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseAgentTool] = {}
        self._mcp_servers: List[Dict[str, Any]] = []

    def register(self, tool: BaseAgentTool) -> None:
        """Registers a custom agent tool instance."""
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseAgentTool]:
        """Retrieves a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolMetadata]:
        """Returns metadata for all currently registered tools."""
        return [tool.get_metadata() for tool in self._tools.values()]

    def register_mcp_server(self, name: str, endpoint: str, capabilities: Optional[List[str]] = None) -> None:
        """Registers an external Model Context Protocol (MCP) server integration."""
        self._mcp_servers.append({
            "name": name,
            "endpoint": endpoint,
            "capabilities": capabilities or [],
        })

    def list_mcp_servers(self) -> List[Dict[str, Any]]:
        """Returns registered MCP server configs."""
        return list(self._mcp_servers)


# Global tool registry instance
registry = ToolRegistry()


def tool(name: str, description: str) -> Callable[[Callable[..., Any]], BaseAgentTool]:
    """Decorator to convert a standard async function into a BaseAgentTool."""

    def decorator(func: Callable[..., Any]) -> BaseAgentTool:
        class FunctionalTool(BaseAgentTool):
            def __init__(self) -> None:
                self.name = name
                self.description = description

            async def execute(self, **kwargs: Any) -> Any:
                if inspect.iscoroutinefunction(func):
                    return await func(**kwargs)
                return func(**kwargs)

        instance = FunctionalTool()
        registry.register(instance)
        return instance

    return decorator
