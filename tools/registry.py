import inspect
import functools
import time
import logging
from typing import Callable, Dict, Any, List, Optional

logger = logging.getLogger("aura_tool_registry")


class ToolDefinition:
    def __init__(self, func: Callable, name: str, description: str, category: str):
        self.func = func
        self.name = name
        self.description = description.strip() if description else ""
        self.category = category
        self.signature = inspect.signature(func)
        self.parameters_schema = self._generate_parameters_schema()

    def _generate_parameters_schema(self) -> Dict[str, Any]:
        properties = {}
        required = []

        type_map = {
            int: "integer",
            float: "number",
            str: "string",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in self.signature.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = type_map.get(param.annotation, "string")
            param_def: Dict[str, Any] = {"type": param_type}

            if param.default is not inspect.Parameter.empty:
                param_def["default"] = param.default
            else:
                required.append(param_name)

            properties[param_name] = param_def

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def to_llm_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI / Groq tool specification format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Executes the tool with performance timing and error handling."""
        start_time = time.perf_counter()
        try:
            # Clean kwargs: remove empty string keys
            clean_kwargs = {k: v for k, v in kwargs.items() if k and str(k).strip()}
            
            # Inspect signature: only pass arguments that the function accepts
            has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in self.signature.parameters.values())
            if not has_var_keyword:
                valid_params = set(self.signature.parameters.keys())
                filtered_kwargs = {k: v for k, v in clean_kwargs.items() if k in valid_params}
            else:
                filtered_kwargs = clean_kwargs

            result = self.func(**filtered_kwargs)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": True,
                "tool": self.name,
                "result": result,
                "execution_ms": duration_ms,
                "error": None
            }
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Error executing tool {self.name}: {e}", exc_info=True)
            return {
                "success": False,
                "tool": self.name,
                "result": None,
                "execution_ms": duration_ms,
                "error": str(e)
            }



class ToolRegistry:
    """Central registry of all tools available to AURA agents."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._tools: Dict[str, ToolDefinition] = {}
        return cls._instance

    def register(self, name: Optional[str] = None, category: str = "general", description: Optional[str] = None):
        """Decorator to register a function as an AURA tool."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = description or func.__doc__ or f"Executes {tool_name}"
            definition = ToolDefinition(
                func=func,
                name=tool_name,
                description=tool_desc,
                category=category
            )
            self._tools[tool_name] = definition

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            wrapper._aura_tool_def = definition
            return wrapper
        return decorator

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def get_schemas(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns JSON schema array for LLM function calling."""
        tools = self.list_tools(category)
        return [t.to_llm_schema() for t in tools]

    def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "tool": name,
                "result": None,
                "execution_ms": 0,
                "error": f"Tool '{name}' not found in registry."
            }
        return tool.execute(**kwargs)


# Global singleton registry and decorator
registry = ToolRegistry()
aura_tool = registry.register
