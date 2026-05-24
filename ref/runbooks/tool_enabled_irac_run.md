# Tool-enabled IRAC Runbook

이 runbook은 도구 사용이 필요한 질문을 Fractal IRAC로 처리할 때의 표준 절차입니다.

## 1. 질문 접수

Mayor는 질문을 그대로 저장하고, 즉답이 가능한지 판단하지 않습니다. 먼저 루트 IRAC를 만듭니다.

## 2. 하위 node 생성

Planner는 다음 기준으로 하위 node를 나눕니다.

- 정의가 필요한가?
- 최신 source가 필요한가?
- 사용자 조건이 부족한가?
- 예외나 충돌 source가 있을 수 있는가?
- 최종 답변을 리뷰할 별도 node가 필요한가?

## 3. 도구 intent 작성

각 node owner는 필요한 도구를 intent로 작성합니다.

예시:

```yaml
id: intent-001
node_id: I1
agent_id: librarian
tool_name: web_search
tool_group: web
risk: low
purpose: 현행 방화구획 관련 법령 원문 후보를 찾습니다.
expected_output: 법령명, 조문 번호, 시행일, URL
provenance_policy: URL과 retrieved_at을 tool_observation에 저장합니다.
```

## 4. 정책 확인

`config/tool_policy.yaml`을 기준으로 위험도를 확인합니다.

- low: 실행 후 provenance 기록
- medium: preflight와 fallback 기록
- high: approval 상태와 target 기록

## 5. 도구 결과 기록

도구 결과는 `tool_observations`에 저장합니다.

결과에서 claim을 추출할 때는 다음을 구분합니다.

- source text
- extracted claim
- agent interpretation
- answer implication

## 6. IRAC 갱신

도구 observation을 바탕으로 node의 Rule/Application을 갱신합니다.

## 7. Cross-link

Schema Cartographer가 node 간 edge를 갱신합니다.

## 8. Refinery

Refinery는 answer draft를 검토합니다. 부족하면 `send_back` 또는 `blocked`로 표시합니다.

## 9. 응답과 기억 후보

Mayor가 사용자 답변을 만들고, Chronicler가 기억 후보를 분리합니다.

