# 실행 생애주기

## 1. Run Open

Mayor가 사용자 질문을 받습니다.

산출물:

- `run_id`
- `root_question`
- `answer_state: draft`
- 초기 unknown

## 2. Root IRAC

Mayor와 Planner가 루트 IRAC node를 만듭니다.

```text
I0: 이 질문에서 판단해야 할 핵심 issue는 무엇인가?
```

## 3. Decomposition

Planner가 하위 issue를 만듭니다.

예시:

```text
I1: rule source 확인
I2: 적용 조건 확인
I3: 예외/완화 확인
I4: 답변 구성
```

## 4. Tool Intent

각 node owner는 필요한 도구를 바로 호출하지 않고 intent를 먼저 작성합니다.

```yaml
tool_intent:
  id: intent-001
  node_id: I1
  agent_id: librarian
  tool_name: web_search
  purpose: 현행 법령 원문 후보를 찾습니다.
  expected_output: 조문명, 조문 번호, 시행일, URL
  risk: low
```

## 5. Policy Check

도구 위험도를 확인합니다.

- low: 기록 후 실행 가능
- medium: preflight와 목적 명시 필요
- high: 사용자 승인 또는 별도 안전 gate 필요

## 6. Tool Observation

도구 결과를 source/observation으로 기록합니다.

```yaml
tool_observation:
  id: obs-001
  intent_id: intent-001
  node_id: I1
  observation_type: source_candidate
  provenance:
  confidence:
  extracted_claims:
```

## 7. Cross-link

Schema Cartographer가 멀리 떨어진 node를 연결합니다.

```text
I3 -> I2 [SHARES_CONDITION]
I3 -> I4 [BLOCKS]
I1 -> I4 [SUPPORTS]
```

## 8. Refinery Review

Refinery가 결론의 품질을 확인합니다.

검토 항목:

- 근거 source가 있는가?
- 조건 누락이 있는가?
- unknown을 숨기지 않았는가?
- tool observation과 conclusion이 구분되는가?
- 사용자가 바로 이해할 수 있는가?

## 9. Final Answer

Mayor가 최종 응답을 구성합니다.

최종 응답은 다음을 포함합니다.

- answer_state
- confidence
- 직접 답변
- 근거
- 남은 unknown
- 다음 질문 또는 다음 tool action

## 10. Memory Candidate

Chronicler와 Source Learner가 장기 기억 후보를 분리합니다.

- 검증된 사실
- 아직 검증되지 않은 claim
- 사용자의 선호
- 반복 가능한 업무 노하우
- schema 개선 후보

