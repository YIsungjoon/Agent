# 구조 개요

Fractal IRAC System은 세 층으로 나뉩니다.

## 1. 사고 구조

모든 판단은 IRAC node로 저장됩니다.

```yaml
node:
  id:
  parent_id:
  depth:
  owner_agent:
  irac:
    issue:
    rule:
    application:
    conclusion:
  evidence:
  unknowns:
  tool_intents:
  tool_observations:
  status:
```

IRAC node는 자기 안에서 답을 끝내지 못하면 하위 node를 만듭니다. 하위 node도 동일한 형식을 사용하므로 재귀 구조가 됩니다.

## 2. Multiagent 구조

각 node는 하나의 primary agent와 여러 supporting agent를 가집니다.

| 역할 | 주요 책임 |
| --- | --- |
| Mayor | 루트 목표 정식화, dispatch, 사용자 전달 책임 |
| Planner | 문제 분해, dependency, 병렬화 |
| Librarian | rule source, citation, compiled knowledge |
| Source Learner | 새 source claim, verification path |
| Worker | 조건 분석, 적용 검토, 제한된 실행 |
| Schema Cartographer | cross-link, edge type, analogy 구분 |
| Refinery | evidence 검토, blocker, final draft 품질 |
| Chronicler | trace, memory candidate, session continuity |

## 3. Tool-use 구조

도구 사용은 네 단계로 기록합니다.

```text
tool_intent -> policy_check -> tool_call -> tool_observation
```

- `tool_intent`: 왜 도구가 필요한지
- `policy_check`: 위험도, 권한, approval 필요 여부
- `tool_call`: 실제 호출 metadata
- `tool_observation`: 결과, provenance, 신뢰도, 다음 연결

도구 결과는 IRAC의 Rule 또는 Application을 보강할 수 있지만, 그 자체가 Conclusion은 아닙니다.

## Workspace 단위

한 번의 실행은 하나의 workspace입니다.

```text
workspace
  run_metadata
  root_question
  nodes
  edges
  agent_roster
  agent_assignments
  handoffs
  shared_entries
  tool_intents
  tool_observations
  final_answer
  memory_candidates
```

이 workspace는 사람에게 읽히는 Markdown과 기계가 읽는 JSON으로 동시에 저장합니다.

