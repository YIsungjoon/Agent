# Fractal IRAC System

이 폴더는 Fractal IRAC 구조를 하나의 독립 subsystem으로 보존합니다. `scripts/aal.py fractal`은 현재 실행기이고, 이 폴더는 그 실행기가 따라야 할 완성형 구조 기준입니다.

## 핵심 아이디어

Fractal IRAC는 하나의 질문을 작은 IRAC 단위로 나눕니다.

```text
Issue -> Rule -> Application -> Conclusion
```

각 IRAC node는 필요하면 다시 하위 IRAC node를 만들 수 있습니다. 여러 agent는 같은 shared workspace를 읽고, 자신이 맡은 node를 갱신하고, 도구 사용 결과를 provenance와 함께 남깁니다.

## 폴더 구조

```text
fractal_irac_system/
  MANIFEST.yaml
  architecture/
    OVERVIEW.md
    RUN_LIFECYCLE.md
  config/
    agents.yaml
    graph.yaml
    tool_policy.yaml
  prompts/
    root_agent.md
    subagent.md
    tool_use.md
    refinery.md
  schemas/
    workspace.schema.json
  tools/
    contracts.yaml
    README.md
  runbooks/
    tool_enabled_irac_run.md
  examples/
    fire_compartment/
      workspace.seed.json
      README.md
  runtime/
    runs/
      README.md
  validate_structure.py
```

## 실행과 저장의 분리

- `fractal_irac_system/`: 구조, policy, prompt, schema, runbook의 기준
- `memory/fractal_irac/runs/`: 실제 실행 결과 workspace 저장소
- `docs/FRACTAL_IRAC_AGENT.md`: 개념 설명
- `docs/MULTIAGENT_FRACTAL_IRAC.md`: multiagent overlay 설명
- `scripts/aal.py fractal`: 현재 CLI 실행기

## 도구 사용 원칙

도구는 IRAC node가 직접 임의로 쓰지 않습니다. 각 node는 먼저 `tool_intent`를 작성하고, `tool_policy.yaml`의 위험도와 agent 권한을 확인한 뒤, 결과를 `tool_observations`로 shared workspace에 기록합니다.

도구 결과는 곧바로 결론이 아닙니다. 결과는 source 또는 observation이고, 결론은 Rule/Application/Conclusion 단계에서 별도로 합성합니다.

## 검증

구조 파일이 모두 있는지 확인합니다.

```bash
python3 fractal_irac_system/validate_structure.py
```

