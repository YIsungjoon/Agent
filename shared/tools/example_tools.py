from langchain_core.tools import tool
from shared.tools.tool_wrapper import execute_web_search, execute_multiply

@tool
def web_search(query: str) -> str:
    """Search the web for information about a given query.
    
    Use this tool to find information about current events, facts, or descriptions of things.
    """
    return execute_web_search(query)

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers together.
    
    Use this tool when you need to calculate the product of two numbers (e.g., a * b).
    """
    return execute_multiply(a, b)
