import os
import json
import copy
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["basic"])

def convert_config_for_frontend(config_data: dict) -> dict:
    """프론트엔드용으로 설정을 변환 (ID 문자열 변환 + 신호 처리)"""
    # 딥 카피로 원본 데이터 보호
    config = copy.deepcopy(config_data)
    
    # 블록 ID 변환
    for block in config.get("blocks", []):
        if "id" in block and isinstance(block["id"], int):
            block["id"] = str(block["id"])
    
    # 연결 ID 변환
    for conn in config.get("connections", []):
        if "id" in conn and isinstance(conn["id"], int):
            conn["id"] = str(conn["id"])
        if "from_block_id" in conn and isinstance(conn["from_block_id"], int):
            conn["from_block_id"] = str(conn["from_block_id"])
        if "to_block_id" in conn and isinstance(conn["to_block_id"], int):
            conn["to_block_id"] = str(conn["to_block_id"])
    
    # 글로벌 신호를 initial_signals로 변환하여 추가
    if "globalSignals" in config and config["globalSignals"]:
        initial_signals = {}
        for signal in config["globalSignals"]:
            signal_name = signal.get("name")
            signal_value = signal.get("value", False)
            if signal_name:
                initial_signals[signal_name] = signal_value
        config["initial_signals"] = initial_signals
    
    return config

@router.get("/")
async def read_root():
    """루트 엔드포인트"""
    return {"message": "Simulation API is running"}

@router.get("/simulation/load-base-config")
async def load_base_config():
    """기본 설정 로드 - base.json 파일에서 읽어옴"""
    try:
        # base.json 파일 경로 찾기 (프로젝트 루트에서)
        base_json_path = None
        
        # 현재 디렉토리부터 상위로 올라가면서 base.json 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for _ in range(4):  # 최대 4단계 위까지 찾기
            parent_dir = os.path.dirname(current_dir)
            potential_path = os.path.join(parent_dir, "base.json")
            if os.path.exists(potential_path):
                base_json_path = potential_path
                break
            current_dir = parent_dir
        
        # 프로젝트 루트에서도 시도
        if not base_json_path:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            potential_path = os.path.join(project_root, "base.json")
            if os.path.exists(potential_path):
                base_json_path = potential_path
        
        if not base_json_path:
            raise FileNotFoundError("base.json 파일을 찾을 수 없습니다")
        
        print(f"[BasicRoutes] Loading base.json from: {base_json_path}")
        
        # base.json 파일 읽기
        with open(base_json_path, 'r', encoding='utf-8') as f:
            base_config = json.load(f)
        
        print(f"[BasicRoutes] Base config loaded successfully. Blocks: {len(base_config.get('blocks', []))}")
        
        # 프론트엔드 호환성을 위한 변환 적용
        converted_config = convert_config_for_frontend(base_config)
        print(f"[BasicRoutes] Config converted - ID conversion and signal processing applied")
        
        return converted_config
    
    except FileNotFoundError as e:
        print(f"[BasicRoutes] File not found: {e}")
        raise HTTPException(status_code=404, detail=f"base.json 파일을 찾을 수 없습니다: {e}")
    
    except json.JSONDecodeError as e:
        print(f"[BasicRoutes] JSON decode error: {e}")
        raise HTTPException(status_code=400, detail=f"base.json 파일 형식이 올바르지 않습니다: {e}")
    
    except Exception as e:
        print(f"[BasicRoutes] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"설정 로드 중 오류 발생: {e}") 