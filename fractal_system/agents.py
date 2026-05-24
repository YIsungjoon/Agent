import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from fractal_system.logger import logger, log_header

REF_DIR = Path("/home/leehm/linux_project/Agent/ref")
PROMPTS_DIR = REF_DIR / "prompts"
CONFIG_DIR = REF_DIR / "config"

class AgentRunner:
    def __init__(self):
        self._llm = None
        self.agent_roster = self._load_agent_roster()

    @property
    def llm(self):
        if self._llm is None:
            # Try to get the API key. Fall back to a dummy key only for import checks so it doesn't crash Pydantic validation
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "DUMMY_IMPORT_KEY"
            self._llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.1,
                google_api_key=api_key
            )
        return self._llm

    def _load_agent_roster(self) -> List[Dict[str, Any]]:
        agents_yaml_path = CONFIG_DIR / "agents.yaml"
        if not agents_yaml_path.exists():
            return []
        with open(agents_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("agents", [])

    def _load_prompt(self, filename: str) -> str:
        path = PROMPTS_DIR / filename
        if not path.exists():
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _extract_yaml(self, text: str) -> Dict[str, Any]:
        """Cleans and extracts YAML content from LLM markdown code blocks."""
        # Find yaml or markdown codeblocks
        pattern = r"```(?:yaml)?\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            yaml_str = match.group(1)
        else:
            # If no code blocks, try to find lines that look like YAML or parse entire text
            yaml_str = text
            
        try:
            parsed = yaml.safe_load(yaml_str)
            if isinstance(parsed, dict):
                return parsed
            logger.warning(f"Extracted YAML parsed content is not a dict: {type(parsed)}")
            return {}
        except Exception as e:
            logger.error(f"Failed to parse YAML string. Text: {yaml_str}\nError: {e}")
            # Fallback regex parsing or return empty
            return {}

    def run_mayor_root(self, question: str) -> Dict[str, Any]:
        """Mayor opens the run and defines the root IRAC node (I0)."""
        log_header("Mayor formulation of Root Node (I0)")
        logger.info(f"Root Question: {question}")
        
        system_prompt = self._load_prompt("root_agent.md")
        user_prompt = f"사용자 질문: {question}\n\n루트 노드 I0를 정의하고 YAML 형식으로 출력하십시오."
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        logger.debug(f"Root Agent System Prompt:\n{system_prompt}")
        response = self.llm.invoke(messages)
        logger.info("Mayor formulation LLM invocation successful.")
        logger.debug(f"Root Agent Raw Response:\n{response.content}")
        
        result = self._extract_yaml(response.content)
        logger.info(f"Root Agent Extracted YAML: {result}")
        
        # Ensure ID is I0
        if "root_node" in result:
            result["root_node"]["id"] = "I0"
            return result["root_node"]
        elif "id" in result:
            result["id"] = "I0"
            return result
        return {"id": "I0", "irac": {"issue": question, "rule": "", "application": "", "conclusion": ""}, "unknowns": [question], "answer_state": "unknown"}

    def run_planner_decomposition(self, workspace_state_str: str) -> List[Dict[str, Any]]:
        """Planner reviews the workspace and decomposes the root node into child nodes and edges."""
        log_header("Planner Decomposition of Root Node")
        logger.info("Planner analysis of workspace initiated.")
        
        # Dynamic description of roles from agents.yaml
        roles_desc = "\n".join([
            f"- {a['role']} ({a['id']}): Responsible for {', '.join(a.get('primary_for', []))}. Tools: {', '.join(a.get('allowed_tool_groups', []))}"
            for a in self.agent_roster
        ])
        
        system_prompt = f"""당신은 Fractal IRAC 시스템의 Planner입니다.
당신의 업무는 현재 Workspace 상태를 분석하여, 루트 노드(I0)를 풀기 위한 하위 문제 노드(I1, I2, I3 등)와 이들 간의 에지(Edge) 관계를 정식화하는 것입니다.

사용 가능한 에이전트 역할군:
{roles_desc}

지침:
1. 루트 질문을 해결하기 위한 하위 태스크 노드를 최소 2개, 최대 4개로 분해하십시오.
2. 각 노드에 적합한 primary_agent (위 역할군의 id)와 depth=1을 설정하십시오.
3. 노드 간의 논리적 순서 및 흐름에 맞추어 에지(from -> to)를 생성하십시오. 에지 타입은 HAS_CHILD, REQUIRES_RULE, APPLIES_RULE, SUPPORTS 등 ref/config/graph.yaml을 참고하여 설정하십시오.
4. 출력은 반드시 다음 YAML 형식을 따르십시오:

```yaml
decomposition:
  nodes:
    - id: I1
      parent_id: I0
      depth: 1
      owner_agent: librarian  # 예시
      irac:
        issue: "하위 과제 질문 내용"
        rule: ""
        application: ""
        conclusion: ""
      status: "draft"
    - id: I2
      parent_id: I0
      depth: 1
      owner_agent: worker     # 예시
      irac:
        issue: "하위 과제 질문 내용"
        rule: ""
        application: ""
        conclusion: ""
      status: "draft"
  edges:
    - from: I0
      to: I1
      type: HAS_CHILD
      reason: "루트 문제를 풀기 위한 서브 이슈 분해"
    - from: I0
      to: I2
      type: HAS_CHILD
      reason: "루트 문제를 풀기 위한 서브 이슈 분해"
    - from: I1
      to: I2
      type: SUPPORTS
      reason: "조회 결과가 적용에 도움이 됨"
```
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"현재 Workspace 상태:\n{workspace_state_str}\n\n하위 노드 분해를 수행하고 YAML로 리턴해주십시오.")
        ]
        
        logger.debug(f"Planner System Prompt:\n{system_prompt}")
        logger.debug(f"Planner Input Workspace State String:\n{workspace_state_str}")
        
        response = self.llm.invoke(messages)
        logger.info("Planner LLM invocation successful.")
        logger.debug(f"Planner Raw Response:\n{response.content}")
        
        result = self._extract_yaml(response.content)
        logger.info(f"Planner Extracted YAML: {result}")
        
        return result.get("decomposition", result)

    def run_subagent_node(self, 
                          question: str, 
                          workspace_str: str, 
                          node_id: str, 
                          node_issue: str,
                          agent_id: str) -> Dict[str, Any]:
        """Runs the specific subagent for a given node, letting them update the IRAC contents or submit tool intents."""
        log_header(f"Subagent Execution on Node: {node_id} (Agent: {agent_id})")
        logger.info(f"Node Issue: {node_issue}")
        
        system_prompt = self._load_prompt("subagent.md")
        
        # Find agent details
        agent_info = next((a for a in self.agent_roster if a["id"] == agent_id), {"role": "Worker", "primary_for": ["general"]})
        role_instruction = f"역할: {agent_info['role']}. 주 업무: {', '.join(agent_info.get('primary_for', []))}. 허용 도구: {', '.join(agent_info.get('allowed_tool_groups', []))}"
        
        user_prompt = f"""
- root question: {question}
- shared workspace:
{workspace_str}
- assigned node: id='{node_id}', issue='{node_issue}'
- role instruction: {role_instruction}
- allowed tools: {', '.join(agent_info.get('allowed_tool_groups', []))}

이 배정된 노드의 IRAC(이슈, 룰, 적용, 결론)을 갱신하거나 도구 사용이 필요한 경우 tool_intents를 제안하십시오.
반드시 YAML 양식(`node_update:`)에 맞춰 출력하십시오.
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        logger.debug(f"Subagent [{agent_id}] System Prompt:\n{system_prompt}")
        logger.debug(f"Subagent [{agent_id}] User Prompt:\n{user_prompt}")
        
        response = self.llm.invoke(messages)
        logger.info(f"Subagent [{agent_id}] LLM invocation successful.")
        logger.debug(f"Subagent [{agent_id}] Raw Response:\n{response.content}")
        
        result = self._extract_yaml(response.content)
        logger.info(f"Subagent [{agent_id}] Extracted YAML: {result}")
        
        return result.get("node_update", result)

    def run_refinery_review(self, workspace_str: str) -> Dict[str, Any]:
        """Refinery agent reviews the full workspace and approves or sends it back with comments."""
        log_header("Refinery Quality Review")
        logger.info("Refinery verification of full workspace initiated.")
        
        system_prompt = self._load_prompt("refinery.md")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"현재 작업 공간 상태:\n{workspace_str}\n\n답변 초안의 정합성을 검토하고 YAML 형식으로 승인 여부(status: approve, send_back)를 출력하십시오.")
        ]
        
        logger.debug(f"Refinery System Prompt:\n{system_prompt}")
        logger.debug(f"Refinery Input Workspace String:\n{workspace_str}")
        
        response = self.llm.invoke(messages)
        logger.info("Refinery LLM invocation successful.")
        logger.debug(f"Refinery Raw Response:\n{response.content}")
        
        result = self._extract_yaml(response.content)
        logger.info(f"Refinery Extracted YAML: {result}")
        
        return result.get("review", result)

    def run_subagent_synthesis(self, parent_id: str, parent_issue: str, children_data_str: str) -> Dict[str, Any]:
        """Synthesizes child node conclusions into the parent node's IRAC (Application & Conclusion)."""
        log_header(f"Subagent Synthesis on Parent Node: {parent_id}")
        logger.info(f"Parent Issue: {parent_issue}")
        
        system_prompt = """당신은 Fractal IRAC 시스템의 Synthesis 에이전트입니다.
당신의 업무는 상위 노드(Parent Node)의 질문과 그 하위 노드(Child Nodes)들의 분석 결과(이슈, 규칙, 적용, 결론)를 종합하여, 상위 노드의 IRAC 중 적용(Application)과 결론(Conclusion)을 작성하는 것입니다.

지침:
1. 하위 노드들의 결론과 증거들을 누락 없이 정교하게 엮어 상위 노드 관점의 적용(Application)을 상세히 기술하십시오.
2. 상위 노드의 질문에 대한 명확하고 완성도 높은 최종 결론(Conclusion)을 작성하십시오.
3. 출력은 반드시 다음 YAML 형식을 따르십시오:

```yaml
synthesis:
  irac:
    application: "하위 노드들의 내용과 증거들을 종합 적용한 상세 텍스트"
    conclusion: "상위 노드 질문에 대한 명확한 핵심 답변 결론"
```
"""
        user_prompt = f"""- parent node: id='{parent_id}', issue='{parent_issue}'
- resolved child nodes details:
{children_data_str}

위 내용을 종합하여 상위 노드의 적용(application)과 결론(conclusion)을 YAML 형식으로 리턴해주십시오."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        logger.debug(f"Synthesis System Prompt:\n{system_prompt}")
        logger.debug(f"Synthesis User Prompt:\n{user_prompt}")
        
        response = self.llm.invoke(messages)
        logger.info("Synthesis LLM invocation successful.")
        logger.debug(f"Synthesis Raw Response:\n{response.content}")
        
        result = self._extract_yaml(response.content)
        logger.info(f"Synthesis Extracted YAML: {result}")
        
        return result.get("synthesis", result)

    def run_mayor_final_synthesis(self, workspace_str: str) -> str:
        """Mayor creates the final readable markdown response summarizing the achievements."""
        log_header("Mayor Final Synthesis Report")
        logger.info("Mayor final report synthesis initiated.")
        
        system_prompt = """당신은 Fractal IRAC 시스템의 Mayor입니다.
현재까지 에이전트들이 협업하여 완성한 Workspace의 모든 노드와 정보(IRAC, 증거, 도구 결과)를 종합하여, 최종 사용자에게 제공할 가장 우수하고 신뢰할 수 있는 종합 보고서를 한국어로 작성하십시오.

작성 지침:
1. 깔끔한 Markdown 스타일을 채택하십시오.
2. 최종 결론(Conclusion)을 서두에 명확히 제시하십시오.
3. 근거가 되는 규칙(Rules)과 관찰 데이터(Application/Evidence)를 출처와 함께 체계적으로 구조화하여 작성하십시오.
4. 아직 미확정으로 남아있는 문제(unknowns)가 있다면 투명하게 서술하십시오.
5. 어조는 전문적이고 신뢰감을 주도록 정중하고 조용하게 작성하십시오.
"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"현재 작업 공간 내용:\n{workspace_str}\n\n최종 종합 보고서를 완성하십시오.")
        ]
        
        logger.debug(f"Mayor Synthesis System Prompt:\n{system_prompt}")
        logger.debug(f"Mayor Input Workspace String:\n{workspace_str}")
        
        response = self.llm.invoke(messages)
        logger.info("Mayor Final Synthesis LLM invocation successful.")
        logger.debug(f"Mayor Synthesized Output Markdown:\n{response.content}")
        
        return response.content

# Create a singleton runner
agent_runner = AgentRunner()
