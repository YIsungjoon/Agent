import os
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, TypedDict, Annotated
from pathlib import Path
from pydantic import BaseModel

from langgraph.graph import StateGraph, START, END

# Import Pydantic models
from fractal_system.models import Workspace, IRACNode, Edge, ToolIntent, ToolObservation, IRAC
from fractal_system.agents import agent_runner
from fractal_system.tools import registry, dispatch_tool
from fractal_system.logger import logger

# Directories for persistence
RUNS_DIR = Path("/home/leehm/linux_project/Agent/runtime/runs")

# Define LangGraph State
class WorkspaceState(TypedDict):
    workspace: Workspace
    feedback: str
    step_logs: List[str]
    current_iteration: int

def append_log(state_logs: List[str], text: str) -> List[str]:
    """Helper to append log statements cleanly."""
    return state_logs + [f"[{datetime.now().strftime('%H:%M:%S')}] {text}"]

# --- LangGraph Nodes ---

def run_open_node(state: WorkspaceState) -> Dict[str, Any]:
    """Stage 1: Open the run, generate metadata and initialize workspace state."""
    logger.info("run_open_node triggered. Starting run initialization...")
    
    workspace_data = state.get("workspace", {})
    if isinstance(workspace_data, Workspace):
        question = workspace_data.question
    elif isinstance(workspace_data, dict):
        question = workspace_data.get("question", "No question provided")
    else:
        question = state.get("question", "No question provided")
    
    # Create unique run ID
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    logger.info(f"Generated new unique run ID: {run_id}")
    logger.info(f"Target User Question: {question}")
    
    # Ensure runs directory exists
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    
    workspace = Workspace(
        run_id=run_id,
        created_at=datetime.now().isoformat(),
        question=question,
        status="open",
        max_depth=2
    )
    
    logs = append_log([], f"🏁 Run Opened: Initialized workspace with ID '{run_id}'")
    logger.info(f"Workspace state created successfully for run '{run_id}'")
    return {
        "workspace": workspace,
        "feedback": "",
        "step_logs": logs,
        "current_iteration": 0
    }

def root_irac_node(state: WorkspaceState) -> Dict[str, Any]:
    """Stage 2: Root IRAC formulation by Mayor."""
    workspace = state["workspace"]
    logs = state["step_logs"]
    
    logger.info(f"[{workspace.run_id}] root_irac_node triggered. Formulating root I0 node...")
    logs = append_log(logs, "👑 Node 'I0' (Root): Mayor is formulating root IRAC...")
    
    # Mayor decides root IRAC structure
    root_data = agent_runner.run_mayor_root(workspace.question)
    
    # Formulate Pydantic Node
    root_irac = IRAC(
        issue=root_data.get("irac", {}).get("issue", workspace.question),
        rule=root_data.get("irac", {}).get("rule", ""),
        application=root_data.get("irac", {}).get("application", ""),
        conclusion=root_data.get("irac", {}).get("conclusion", "")
    )
    
    root_node = IRACNode(
        id="I0",
        depth=0,
        agent_type="mayor",
        owner_agent="mayor",
        status="draft",
        irac=root_irac,
        unknowns=root_data.get("unknowns", [])
    )
    
    workspace.nodes.append(root_node)
    logger.info(f"[{workspace.run_id}] Root node I0 formulated: {root_irac.model_dump()}")
    
    logs = append_log(logs, f"👑 Root issue formulated successfully by Mayor: '{root_irac.issue[:50]}...'")
    return {
        "workspace": workspace,
        "step_logs": logs
    }

def expand_tree_node(state: WorkspaceState) -> Dict[str, Any]:
    """Stage 3: Problem Decomposition & Recursive Expansion.
    Initializes root decomposition and handles recursive expansion of complex nodes.
    """
    workspace = state["workspace"]
    logs = state["step_logs"]
    
    logger.info(f"[{workspace.run_id}] expand_tree_node triggered.")
    
    # 1. Handle Root I0 node decomposition if it's in draft status
    root_node = next((n for n in workspace.nodes if n.id == "I0"), None)
    if root_node and root_node.status == "draft":
        logger.info(f"[{workspace.run_id}] Initializing root I0 decomposition by Planner...")
        logs = append_log(logs, "📋 Root Decomposition: Planner is formulating the initial sub-plan...")
        
        workspace_json = workspace.model_dump_json(by_alias=True, indent=2)
        decomp_result = agent_runner.run_planner_decomposition(workspace_json)
        
        nodes_added = []
        proposed_nodes = decomp_result.get("nodes", [])
        for node_data in proposed_nodes:
            node_id = node_data.get("id")
            if node_id == "I0":
                continue
                
            irac_data = node_data.get("irac", {})
            irac_obj = IRAC(
                issue=irac_data.get("issue", ""),
                rule=irac_data.get("rule", ""),
                application=irac_data.get("application", ""),
                conclusion=irac_data.get("conclusion", "")
            )
            
            new_node = IRACNode(
                id=node_id,
                parent_id="I0",
                depth=1,
                owner_agent=node_data.get("owner_agent", "worker"),
                status="draft",
                irac=irac_obj
            )
            workspace.nodes.append(new_node)
            nodes_added.append(node_id)
            logger.info(f"[{workspace.run_id}] Decomposed node {node_id} added under I0")
            
        proposed_edges = decomp_result.get("edges", [])
        for edge_data in proposed_edges:
            new_edge = Edge(
                from_node=edge_data.get("from", edge_data.get("from_node")),
                to=edge_data.get("to"),
                type=edge_data.get("type", "HAS_CHILD"),
                reason=edge_data.get("reason", "")
            )
            workspace.edges.append(new_edge)
            
        # Ensure all children have HAS_CHILD edges from I0
        for nid in nodes_added:
            if not any(e.from_node == "I0" and e.to == nid for e in workspace.edges):
                workspace.edges.append(Edge(from_node="I0", to=nid, type="HAS_CHILD", reason="Root decomposition edge"))
                
        root_node.status = "waiting_for_children"
        logs = append_log(logs, f"📋 Planner successfully decomposed root issue into child nodes: {nodes_added}")
        logger.info(f"[{workspace.run_id}] Root decomposition complete. Child nodes added: {nodes_added}")
        
    return {
        "workspace": workspace,
        "step_logs": logs
    }


def execute_leaves_node(state: WorkspaceState) -> Dict[str, Any]:
    """Stage 4-6: Subagent Execution. Runs R-A on active leaf nodes (nodes without children).
    Supports dynamic sub-node spawning if a subagent determines an issue is too complex.
    """
    workspace = state["workspace"]
    logs = state["step_logs"]
    feedback = state.get("feedback", "")
    iteration = state.get("current_iteration", 0) + 1
    
    logger.info(f"[{workspace.run_id}] execute_leaves_node triggered. Iteration: {iteration}")
    logs = append_log(logs, f"🔄 Subagent Leaf Execution: Iteration {iteration}...")
    
    # 1. Identify leaf node IDs (nodes that have no children in the workspace graph)
    all_parent_ids = {node.parent_id for node in workspace.nodes if node.parent_id is not None}
    
    # Leaves are nodes with status in ["draft", "rejected", "waiting_for_tool"] that are NOT in all_parent_ids
    pending_nodes = [
        node for node in workspace.nodes 
        if node.id != "I0" and node.id not in all_parent_ids and node.status in ["draft", "rejected", "waiting_for_tool"]
    ]
    
    if not pending_nodes:
        logger.info(f"[{workspace.run_id}] No pending leaf nodes to execute in this iteration.")
        logs = append_log(logs, "🔄 No active leaf nodes waiting for execution.")
        return {
            "workspace": workspace,
            "step_logs": logs,
            "feedback": "",
            "current_iteration": iteration
        }
        
    for node in pending_nodes:
        logger.info(f"[{workspace.run_id}] Leaf node execution starting: '{node.id}' (Owner: '{node.owner_agent}')")
        logs = append_log(logs, f"🤖 Subagent [{node.owner_agent}] executing R-A on node '{node.id}': '{node.irac.issue[:45]}...'")
        
        # Build workspace description
        workspace_desc = workspace.model_dump_json(by_alias=True, indent=2)
        if feedback and node.status == "rejected":
            workspace_desc += f"\n\n[REFINERY CRITIQUE FOR RE-SUBMISSION]:\n{feedback}"
            logger.info(f"[{workspace.run_id}] Node '{node.id}' was previously rejected. Passing Refinery critique.")
            
        # Run subagent
        update = agent_runner.run_subagent_node(
            question=workspace.question,
            workspace_str=workspace_desc,
            node_id=node.id,
            node_issue=node.irac.issue,
            agent_id=node.owner_agent
        )
        
        # 2. Check if the subagent determined the issue is too complex and proposed child nodes (Dynamic Expansion)
        proposed_children = update.get("proposed_child_nodes", [])
        if proposed_children:
            node.status = "waiting_for_children"
            child_ids = []
            
            for idx, child_data in enumerate(proposed_children):
                if not isinstance(child_data, dict):
                    continue
                # Generate child ID (e.g. I2_1, I2_2)
                child_id = f"{node.id}_{idx+1}"
                child_irac = child_data.get("irac", {})
                child_irac_obj = IRAC(
                    issue=child_irac.get("issue", ""),
                    rule=child_irac.get("rule", ""),
                    application=child_irac.get("application", ""),
                    conclusion=child_irac.get("conclusion", "")
                )
                
                child_node = IRACNode(
                    id=child_id,
                    parent_id=node.id,
                    depth=node.depth + 1,
                    owner_agent=child_data.get("owner_agent", "worker"),
                    status="draft",
                    irac=child_irac_obj
                )
                workspace.nodes.append(child_node)
                child_ids.append(child_id)
                logger.info(f"[{workspace.run_id}] Dynamic Decomposed Node {child_id} added under {node.id}")
                
            # Add proposed edges
            proposed_edges = update.get("proposed_edges", [])
            for edge_data in proposed_edges:
                if not isinstance(edge_data, dict):
                    continue
                new_edge = Edge(
                    from_node=edge_data.get("from", edge_data.get("from_node", node.id)),
                    to=edge_data.get("to"),
                    type=edge_data.get("type", "HAS_CHILD"),
                    reason=edge_data.get("reason", "")
                )
                workspace.edges.append(new_edge)
                
            # Ensure HAS_CHILD edges exist for child nodes
            for cid in child_ids:
                if not any(e.from_node == node.id and e.to == cid for e in workspace.edges):
                    workspace.edges.append(Edge(from_node=node.id, to=cid, type="HAS_CHILD", reason="Dynamic sub-task split"))
                    
            logs = append_log(logs, f"📋 Subagent '{node.owner_agent}' requested dynamic sub-plan for '{node.id}', spawning {len(child_ids)} child nodes: {child_ids}")
            logger.info(f"[{workspace.run_id}] Node '{node.id}' dynamically decomposed. Parent status set to 'waiting_for_children'")
            continue
            
        # 3. Apply standard R-A updates
        irac_update = update.get("irac", {})
        if irac_update:
            node.irac.issue = irac_update.get("issue", node.irac.issue)
            node.irac.rule = irac_update.get("rule", node.irac.rule)
            node.irac.application = irac_update.get("application", node.irac.application)
            node.irac.conclusion = irac_update.get("conclusion", node.irac.conclusion)
            
        node.evidence = update.get("evidence", node.evidence)
        node.unknowns = update.get("unknowns", node.unknowns)
        node.status = "completed"
        
        # 4. Handle Tool Intents (R-A Tool use)
        proposed_intents = update.get("tool_intents", [])
        if proposed_intents:
            if isinstance(proposed_intents, str):
                proposed_intents = [{"tool_name": proposed_intents, "purpose": "Search information"}]
                
            has_executed_any = False
            for idx, intent_data in enumerate(proposed_intents):
                if not isinstance(intent_data, dict):
                    continue
                    
                intent_id = f"intent_{node.id}_{idx}_{uuid.uuid4().hex[:4]}"
                intent = ToolIntent(
                    id=intent_id,
                    node_id=node.id,
                    agent_id=node.owner_agent,
                    tool_name=intent_data.get("tool_name") or "web_search",
                    tool_group=intent_data.get("tool_group") or "web",
                    risk=intent_data.get("risk") or "low",
                    purpose=intent_data.get("purpose") or "Search for rules/observations",
                    expected_output=intent_data.get("expected_output") or "results",
                    preflight=intent_data.get("preflight"),
                    approval_status="pending",
                    provenance_policy=intent_data.get("provenance_policy") or "url",
                    fallback=intent_data.get("fallback")
                )
                
                logger.info(f"[{workspace.run_id}] Tool intent '{intent.id}' proposed: {intent.model_dump()}")
                logs = append_log(logs, f"🛠️ Subagent requested tool '{intent.tool_name}' for node '{node.id}' (Purpose: {intent.purpose[:30]})")
                
                is_approved, reason = registry.policy_check(intent)
                logger.info(f"[{workspace.run_id}] Policy Check for intent '{intent.id}': Approved = {is_approved}, Reason = {reason}")
                
                if is_approved:
                    intent.approval_status = "approved"
                    workspace.tool_intents.append(intent)
                    node.tool_intents.append(intent.id)
                    
                    logs = append_log(logs, f"🟢 Policy Approved: Running tool '{intent.tool_name}'...")
                    args = intent_data.get("arguments", intent_data.get("args", {"query": intent.purpose}))
                    logger.info(f"[{workspace.run_id}] Dispatching tool '{intent.tool_name}' with args: {args}")
                    
                    obs_content = dispatch_tool(intent.tool_name, args)
                    logger.info(f"[{workspace.run_id}] Tool '{intent.tool_name}' returned observation: {obs_content}")
                    
                    obs_id = f"obs_{node.id}_{idx}_{uuid.uuid4().hex[:4]}"
                    observation = ToolObservation(
                        id=obs_id,
                        intent_id=intent.id,
                        node_id=node.id,
                        observation_type="source_candidate" if "search" in intent.tool_name else "calculation_result",
                        provenance={"source": "mock_simulator", "timestamp": datetime.now().isoformat()},
                        content=obs_content
                    )
                    
                    workspace.tool_observations.append(observation)
                    node.tool_observations.append(observation.id)
                    logs = append_log(logs, f"📦 Tool Observation retrieved: '{obs_content[:50]}...'")
                    node.evidence.append(f"Tool {intent.tool_name} returned: {obs_content}")
                    has_executed_any = True
                else:
                    intent.approval_status = "blocked"
                    workspace.tool_intents.append(intent)
                    node.tool_intents.append(intent.id)
                    node.status = "waiting_for_tool"
                    node.irac.application += f"\n[BLOCKED TOOL CALL: {reason}]"
                    logs = append_log(logs, f"❌ Policy BLOCKED tool '{intent.tool_name}': {reason}")
                    
            if has_executed_any and node.status != "waiting_for_tool":
                node.status = "draft"
                logger.info(f"[{workspace.run_id}] Node '{node.id}' executed tools. Keeping in 'draft' to ingest evidence in the next pass.")
                logs = append_log(logs, f"🔄 Node '{node.id}' executed tools. Keeping in 'draft' to process evidence next.")
                
        logger.info(f"[{workspace.run_id}] Node '{node.id}' processing complete. Status: '{node.status}'")
        logs = append_log(logs, f"🤖 Node '{node.id}' processing complete. Status: '{node.status}'")
        
    return {
        "workspace": workspace,
        "step_logs": logs,
        "feedback": "",
        "current_iteration": iteration
    }


def collapse_tree_node(state: WorkspaceState) -> Dict[str, Any]:
    """Stage 7: Recursive bottom-up collapse of resolved children into parent nodes.
    Repeats bottom-up synthesis recursively until all possible parents are collapsed.
    """
    workspace = state["workspace"]
    logs = state["step_logs"]
    
    logger.info(f"[{workspace.run_id}] collapse_tree_node triggered.")
    logs = append_log(logs, "🔬 Collapse Stage: Checking completed child groups for bottom-up synthesis...")
    
    while True:
        collapsed_any = False
        
        # Find all nodes that are waiting for children
        waiting_parents = [node for node in workspace.nodes if node.status == "waiting_for_children"]
        
        for parent in waiting_parents:
            # Find all child nodes in the workspace
            children = [node for node in workspace.nodes if node.parent_id == parent.id]
            
            # If parent has children and ALL of them are completed
            if children and all(child.status == "completed" for child in children):
                logger.info(f"[{workspace.run_id}] Collapsing children of parent '{parent.id}'...")
                
                # Format children data for synthesis LLM call
                children_data_list = []
                for child in children:
                    child_info = f"""--- Node {child.id} ({child.owner_agent}) ---
이슈 (Issue): {child.irac.issue}
규칙 (Rule): {child.irac.rule or '미제시'}
적용 (Application): {child.irac.application or '미제시'}
결론 (Conclusion): {child.irac.conclusion or '미제시'}
"""
                    children_data_list.append(child_info)
                
                children_data_str = "\n".join(children_data_list)
                
                # Call Subagent Synthesis
                synthesis_update = agent_runner.run_subagent_synthesis(
                    parent_id=parent.id,
                    parent_issue=parent.irac.issue,
                    children_data_str=children_data_str
                )
                
                # Apply synthesis results to parent
                parent.irac.application = synthesis_update.get("irac", {}).get("application", parent.irac.application)
                parent.irac.conclusion = synthesis_update.get("irac", {}).get("conclusion", parent.irac.conclusion)
                parent.status = "completed"
                
                logger.info(f"[{workspace.run_id}] Parent '{parent.id}' successfully synthesized and marked 'completed'")
                logs = append_log(logs, f"🔬 Synthesized and collapsed child nodes of parent '{parent.id}' into 'completed' status.")
                collapsed_any = True
                
        # If we didn't collapse any parent in this pass, we are done
        if not collapsed_any:
            break
            
    return {
        "workspace": workspace,
        "step_logs": logs
    }


def refinery_review_node(state: WorkspaceState) -> Dict[str, Any]:
    """Stage 8: Refinery Review. Critiques evidence and either approves or sends back."""
    workspace = state["workspace"]
    logs = state["step_logs"]
    iteration = state["current_iteration"]
    
    logger.info(f"[{workspace.run_id}] refinery_review_node triggered. Reviewing iteration: {iteration}")
    logs = append_log(logs, "🔬 Refinery Review Stage: Refinery is reviewing quality...")
    
    # If we reached maximum loop budget (e.g. 3 loops), force approval to prevent cost runaway
    if iteration >= 3:
        logger.warning(f"[{workspace.run_id}] Refinery Loop budget exceeded! Force approving run.")
        logs = append_log(logs, "🔬 Loop budget exceeded! Force approving to prevent infinite cycle.")
        workspace.status = "approved"
        return {"workspace": workspace, "step_logs": logs, "feedback": ""}
        
    # Serialize workspace to JSON string for Refinery review
    workspace_json = workspace.model_dump_json(by_alias=True, indent=2)
    
    # Run Refinery
    review = agent_runner.run_refinery_review(workspace_json)
    status = review.get("status", "approve").lower()
    logger.info(f"[{workspace.run_id}] Refinery Review Result: Status = {status}, Review Output = {review}")
    
    if status == "approve":
        logs = append_log(logs, "🔬 Refinery: APPROVED! Draft answers have high logical rigor.")
        workspace.status = "approved"
        # Propagate subagent conclusions back to update root node (I0) conclusion
        conclusions = []
        for node in workspace.nodes:
            if node.id != "I0" and node.irac.conclusion:
                conclusions.append(f"[{node.id} 결론] {node.irac.conclusion}")
                
        # Update root I0 application and conclusion
        root_node = next((n for n in workspace.nodes if n.id == "I0"))
        root_node.irac.application = "\n".join(conclusions)
        root_node.irac.conclusion = review.get("revised_answer", "All sub-nodes successfully resolved.")
        root_node.status = "completed"
        
        logger.info(f"[{workspace.run_id}] Refinery approved. Final root node update: Application = {root_node.irac.application}, Conclusion = {root_node.irac.conclusion}")
        return {
            "workspace": workspace,
            "step_logs": logs,
            "feedback": ""
        }
    else:
        # Send Back cycle
        feedback_text = review.get("missing_evidence", "") or review.get("unsafe_claims", "") or "Please provide more details."
        logs = append_log(logs, f"🔬 Refinery: REJECTED & SENT BACK! Critique: '{feedback_text[:60]}...'")
        
        # Reset completed nodes back to draft/rejected to let them fix based on comments
        for node in workspace.nodes:
            if node.id != "I0" and node.status == "completed":
                node.status = "rejected"
                
        # Reset root I0 status back to waiting_for_children so we loop back properly!
        root_node = next((n for n in workspace.nodes if n.id == "I0"))
        root_node.status = "waiting_for_children"
        
        workspace.status = "open"
        logger.info(f"[{workspace.run_id}] Refinery REJECTED the draft. Sending back with feedback: {feedback_text}")
        return {
            "workspace": workspace,
            "step_logs": logs,
            "feedback": feedback_text
        }


def final_answer_node(state: WorkspaceState) -> Dict[str, Any]:
    """Stage 9: Final Answer Synthesis by Mayor."""
    workspace = state["workspace"]
    logs = state["step_logs"]
    
    logger.info(f"[{workspace.run_id}] final_answer_node triggered. Starting final answer synthesis by Mayor...")
    logs = append_log(logs, "👑 Final Answer Stage: Mayor is synthesizing final comprehensive report...")
    
    workspace_json = workspace.model_dump_json(by_alias=True, indent=2)
    
    # Mayor synthesizes final markdown
    final_md = agent_runner.run_mayor_final_synthesis(workspace_json)
    
    workspace.answer_draft = final_md
    workspace.status = "completed"
    
    logger.info(f"[{workspace.run_id}] Mayor final synthesis completed. Synthesized Report Length: {len(final_md)} chars.")
    logs = append_log(logs, "👑 Final comprehensive report successfully synthesized by Mayor.")
    return {
        "workspace": workspace,
        "step_logs": logs
    }


def chronicler_node(state: WorkspaceState) -> Dict[str, Any]:
    """Stage 10: Memory Candidate & Run Closure. Persists results to disk."""
    workspace = state["workspace"]
    logs = state["step_logs"]
    
    logger.info(f"[{workspace.run_id}] chronicler_node triggered. Saving run data to disk...")
    logs = append_log(logs, "📝 Chronicler Node: Saving files and building long-term memories...")
    
    # 1. Save Workspace JSON
    json_path = RUNS_DIR / f"{workspace.run_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(workspace.model_dump_json(by_alias=True, indent=2))
    logger.info(f"[{workspace.run_id}] Saved workspace state JSON to: {json_path}")
        
    # 2. Save Workspace Markdown report
    md_path = RUNS_DIR / f"{workspace.run_id}.md"
    
    # Construct a beautiful markdown file summarizing everything
    md_content = f"""# Fractal IRAC Run Report - {workspace.run_id}
- **발제일**: {workspace.created_at}
- **원 질문**: {workspace.question}
- **상태**: {workspace.status}

---

## 👑 최종 종합 답변 (Mayor Synthesis)
{workspace.answer_draft}

---

## 🏗️ 계층형 추론 트레이스 (IRAC Nodes)
"""
    for node in workspace.nodes:
        md_content += f"""
### 🟢 노드: {node.id} (배정: {node.owner_agent})
- **상태**: {node.status}
- **이슈 (Issue)**: {node.irac.issue}
- **규칙 (Rule)**: {node.irac.rule or "미설정"}
- **적용 (Application)**: {node.irac.application or "미설정"}
- **결론 (Conclusion)**: {node.irac.conclusion or "미설정"}
- **근거/증거**:
"""
        for ev in node.evidence:
            md_content += f"  - {ev}\n"
        if not node.evidence:
            md_content += "  - (증거 없음)\n"
            
    md_content += "\n---\n## 📋 실행 이력 (Execution Logs)\n"
    for log in logs:
        md_content += f"- {log}\n"
        
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"[{workspace.run_id}] Saved workspace report Markdown to: {md_path}")
        
    logs = append_log(logs, f"🏁 Chronicler: Run closed successfully. Workspace saved to '{json_path.name}' and '{md_path.name}'")
    logger.info(f"[{workspace.run_id}] Chronicler successfully completed run closure and saved memories.")
    return {
        "workspace": workspace,
        "step_logs": logs
    }

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
