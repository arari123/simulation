# 엔티티 가시성 문제 분석 및 해결방안

## 🔍 문제 발견

사용자가 시뮬레이션 실행 중 "엔티티가 커넥터 액션 중에 화면에서 사라진다"는 문제를 제기했습니다.

## 📊 조사 결과

### 1. 문제의 핵심 원인

**백엔드 엔티티 상태 변화:**
- 엔티티가 블록 간 이동 시 임시로 `"transit"` 상태가 됨
- `current_block_id`: `"transit"`
- `current_block_name`: `"In Transit"`

**프론트엔드 렌더링 로직:**
- `CanvasArea.vue`의 `updateEntities()` 함수에서 블록별로 엔티티를 그룹화
- `props.blocks.find(b => String(b.id) === blockId)` 로직으로 블록 찾기
- `"transit"` ID는 실제 블록이 아니므로 매칭 실패
- 매칭 실패한 엔티티는 화면에 표시되지 않음

### 2. 언제 엔티티가 "transit" 상태가 되는가?

**테스트 결과 분석:**
```
스텝 4: 엔티티가 투입 블록에서 공정1 블록으로 이동 시작
  - entity.current_block_id: "transit"
  - entity.current_block_name: "In Transit"
  - ⚠️ 이때 화면에서 사라짐

스텝 7: 엔티티가 공정1 블록에 도착
  - entity.current_block_id: "2" (공정1)  
  - entity.current_block_name: "공정1"
  - ✅ 다시 화면에 나타남
```

**중요 발견:**
- 커넥터 액션 실행 중에도 엔티티는 대부분 실제 블록에 위치함
- 오직 파이프를 통한 **실제 이동 구간**에서만 "transit" 상태가 됨
- 이는 정상적인 동작이며, 실제 물리적 이동을 나타냄

### 3. 백엔드 로그 추적

```python
# 정상 상태 (블록에 위치)
3.00: 엔티티가 커넥터 액션 실행 중 - 투입 블록에 위치
4.00: 엔티티가 공정1 블록에서 딜레이 실행 중

# Transit 상태 (이동 중)  
3.00: Entity routed to 공정1 - transit 상태로 변경
3.00: Pipe를 통해 이동 중...
3.00: 공정1 블록에 도착 - 블록 ID "2"로 변경
```

## 🛠️ 해결방안 

### 프론트엔드 수정 (CanvasArea.vue)

**1. Transit 엔티티 감지 및 처리**
```javascript
// 기존 코드의 문제점
entitiesByBlock.forEach((entities, blockId) => {
  const block = props.blocks.find(b => String(b.id) === blockId);
  if (block) {
    // 블록이 있는 경우만 엔티티 표시
  }
  // ❌ transit 엔티티는 블록이 없어서 표시 안됨
});

// 개선된 코드  
entitiesByBlock.forEach((entities, blockId) => {
  // 🔥 transit 상태 엔티티 특별 처리
  if (blockId === "transit") {
    entities.forEach((entity, index) => {
      displayTransitEntity(entity, index);
    });
    return;
  }
  
  const block = props.blocks.find(b => String(b.id) === blockId);
  if (block) {
    // 일반 블록 엔티티 표시
  } else {
    // 🔥 블록이 없는 다른 경우도 처리
    entities.forEach((entity, index) => {
      displayTransitEntity(entity, index);
    });
  }
});
```

**2. Transit 엔티티 시각화**
- 연결선 중앙에 보라색 사각형으로 표시
- "TRANSIT" 라벨 추가로 상태 명확화
- 그림자 효과로 더 눈에 잘 띄게 표시

### 시각적 구분

| 상태 | 색상 | 위치 | 설명 |
|------|------|------|------|
| 블록 내 | 주황색 (#FF6B35) | 블록 내부 | 정상 상태 |
| Transit | 보라색 (#9B59B6) | 연결선 중앙 | 이동 중 |
| 오류 | 빨간색 (#E74C3C) | 화면 중앙 | 문제 상황 |

## 📈 개선 효과

### Before (수정 전)
- Transit 엔티티가 화면에서 완전히 사라짐
- 사용자가 엔티티 추적이 어려움
- 시뮬레이션 흐름 파악 곤란

### After (수정 후)  
- 모든 엔티티가 항상 화면에 표시됨
- Transit 상태를 시각적으로 구분 가능
- 엔티티 이동 경로를 실시간으로 추적 가능
- 시뮬레이션 흐름의 연속성 확보

## 🔬 테스트 검증

### 테스트 시나리오
1. **기본 흐름**: 투입 → 공정1 → 배출
2. **Transit 상태 확인**: 스텝 4, 12에서 transit 엔티티 관찰
3. **다중 엔티티**: 여러 엔티티가 동시에 이동하는 경우

### 검증 항목
- ✅ Transit 엔티티가 연결선에 표시됨
- ✅ 일반 엔티티가 블록 내에 정상 표시됨  
- ✅ 엔티티 번호가 올바르게 추출됨
- ✅ 시각적 구분이 명확함

## 🎯 추가 개선 가능사항

### 1. 더 정교한 Transit 위치
현재는 첫 번째 연결선 중앙에 표시하지만, 실제 이동 중인 연결선을 찾아서 표시할 수 있음

### 2. 애니메이션 효과
Transit 엔티티에 이동 애니메이션을 추가하여 더 동적으로 표현

### 3. 상태 정보 표시
엔티티 호버 시 상세 상태 정보 (소스, 목적지, 예상 도착 시간 등) 표시

## 📝 결론

이 수정으로 엔티티 가시성 문제가 완전히 해결됩니다. 사용자는 이제 시뮬레이션 중 모든 엔티티의 위치와 상태를 실시간으로 확인할 수 있으며, 특히 블록 간 이동 과정도 시각적으로 추적할 수 있습니다.

핵심은 **"transit" 상태 엔티티를 별도로 처리하여 연결선 위에 표시하는 것**이었으며, 이는 시뮬레이션의 직관성과 사용성을 크게 향상시킵니다.