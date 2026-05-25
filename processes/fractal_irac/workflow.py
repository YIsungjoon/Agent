from langgraph.graph import StateGraph, START, END
from shared.logger import logger
from processes.fractal_irac.nodes import (
    WorkspaceState,
    run_open_node,
    root_irac_node,
    expand_tree_node,
    execute_leaves_node,
    collapse_tree_node,
    refinery_review_node,
    final_answer_node,
    chronicler_node
)

# --- State Routing Logic ---

def router_after_collapse(state: WorkspaceState) -> str:
    """Decides if I0 is fully completed, routing to refinery_review or looping back to expand_tree."""
    workspace = state["workspace"]
    root_node = next((node for node in workspace.nodes if node.id == "I0"), None)
    
    if root_node and root_node.status == "completed":
        logger.info(f"[{workspace.run_id}] Root I0 node completed. Routing to refinery review.")
        return "refinery_review"
    else:
        logger.info(f"[{workspace.run_id}] Root I0 node not yet completed. Looping back to expand tree.")
        return "expand_tree"


def router_after_review(state: WorkspaceState) -> str:
    """Decides if Refinery approved the draft or if we loop back for revisions."""
    workspace = state["workspace"]
    if workspace.status == "approved":
        logger.info(f"[{workspace.run_id}] Refinery approved! Proceeding to final answer synthesis.")
        return "final_answer"
    else:
        logger.info(f"[{workspace.run_id}] Refinery sent back. Looping back to expand tree.")
        return "expand_tree"

# --- Graph Assembly ---

workflow = StateGraph(WorkspaceState)

# Add all nodes in the hierarchical recursive stage
workflow.add_node("run_open", run_open_node)
workflow.add_node("root_irac", root_irac_node)
workflow.add_node("expand_tree", expand_tree_node)
workflow.add_node("execute_leaves", execute_leaves_node)
workflow.add_node("collapse_tree", collapse_tree_node)
workflow.add_node("refinery_review", refinery_review_node)
workflow.add_node("final_answer", final_answer_node)
workflow.add_node("chronicler", chronicler_node)

# Set starting point
workflow.add_edge(START, "run_open")

# Sequence standard initialization
workflow.add_edge("run_open", "root_irac")
workflow.add_edge("root_irac", "expand_tree")
workflow.add_edge("expand_tree", "execute_leaves")
workflow.add_edge("execute_leaves", "collapse_tree")

# Route to review or loop back
workflow.add_conditional_edges(
    "collapse_tree",
    router_after_collapse,
    {
        "refinery_review": "refinery_review",
        "expand_tree": "expand_tree"
    }
)

# Route to final answer or loop back for refinery rejection
workflow.add_conditional_edges(
    "refinery_review",
    router_after_review,
    {
        "final_answer": "final_answer",
        "expand_tree": "expand_tree"
    }
)

# Route to chronicler and exit
workflow.add_edge("final_answer", "chronicler")
workflow.add_edge("chronicler", END)

# Compile Graph
fractal_graph = workflow.compile()
