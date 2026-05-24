import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

# Import custom tools from tools.py
from tools import web_search, multiply

# Collect tools and create the prebuilt ToolNode
tools = [web_search, multiply]
tool_node = ToolNode(tools)

def get_agent_graph():
    """Initializes the LLM, binds the tools, constructs the LangGraph state machine,
    and returns a compiled graph.
    """
    # 1. Initialize the Chat Model (Gemini 1.5 Flash is chosen as default for cost/speed)
    # It will automatically pick up GEMINI_API_KEY or GOOGLE_API_KEY from environment variables
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=api_key
    )
    
    # 2. Bind the tools to the model so the LLM is aware of them and can output tool calls
    model_with_tools = model.bind_tools(tools)

    # 3. Define the LLM agent node
    def call_model(state: MessagesState):
        messages = state["messages"]
        # Invoke the model with current conversation history
        response = model_with_tools.invoke(messages)
        # Return the response to update state['messages'] (using reducer/add_messages)
        return {"messages": [response]}

    # 4. Construct the Graph
    workflow = StateGraph(MessagesState)

    # Add the nodes (agent node to invoke LLM, tools node to execute tools)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # Set the entrypoint. When graph starts, it goes to "agent" node first
    workflow.add_edge(START, "agent")

    # Add conditional edge from "agent"
    # tools_condition will check if the LLM output wants to call a tool:
    # - Yes: route to "tools" node
    # - No: route to END
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
    )

    # After the tool is executed in "tools" node, we route back to "agent"
    # to let the LLM see the tool output and decide next steps
    workflow.add_edge("tools", "agent")

    # 5. Compile the workflow into a runnable graph
    graph = workflow.compile()
    return graph
