# 도구 사용 계층

Fractal IRAC에서 도구는 agent의 손발이지만, 결론을 대신하지 않습니다. 도구는 source와 observation을 만들고, IRAC node가 그것을 해석합니다.

## 기본 흐름

```text
agent need
  -> tool_intent
  -> policy_check
  -> tool_call
  -> tool_observation
  -> IRAC update
```

## 도구 결과의 위치

- Rule source 검색 결과: `node.irac.rule`, `node.evidence`
- 조건 추출 결과: `node.irac.application`
- 화면 관찰 결과: `tool_observations`, `screen_observation source note`
- 장기 기억 조회 결과: `shared_entries`, `evidence`
- 장기 기억 upsert 후보: `memory_candidates`

## 중요한 경계

도구가 말한 것과 agent가 추론한 것을 섞지 않습니다.

```text
observation: 법령 페이지에서 A라는 문장을 찾았다.
inference: 이 문장은 사용자의 조건 B에 적용될 수 있다.
conclusion: 따라서 현재 조건에서는 C라고 답할 수 있다.
```

