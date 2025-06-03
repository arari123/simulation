"""
파이프(연결) 관리 모듈
블록 간 연결과 엔티티 이동 경로를 관리합니다.
"""
import simpy
from typing import Dict, List, Optional, Any
from .constants import FormatConfig
import logging

logger = logging.getLogger(__name__)

class PipeManager:
    """파이프(연결) 관리를 담당하는 클래스"""
    
    def __init__(self):
        self.pipes: Dict[str, simpy.Store] = {}
        self.in_pipes_map: Dict[str, List[str]] = {}
        self.out_pipes_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
    def create_pipe_id(self, from_block_id: str, from_connector_id: str, 
                      to_block_id: str, to_connector_id: str) -> str:
        """파이프 ID를 생성합니다."""
        return FormatConfig.PIPE_ID_FORMAT.format(
            from_block=from_block_id,
            from_conn=from_connector_id,
            to_block=to_block_id,
            to_conn=to_connector_id
        )
        
    def create_pipes(self, connections: List[Any], blocks: List[Any], env: simpy.Environment):
        """연결 정보를 기반으로 파이프를 생성합니다."""
        # 파이프 생성
        for conn in connections:
            pipe_id = self.create_pipe_id(
                conn.from_block_id, conn.from_connector_id,
                conn.to_block_id, conn.to_connector_id
            )
            self.pipes[pipe_id] = simpy.Store(env)
            
        # 입출력 매핑 초기화
        for block in blocks:
            self.in_pipes_map[str(block.id)] = []
            self.out_pipes_map[str(block.id)] = {}
            # 각 커넥터에 대해 여러 연결을 저장할 수 있도록 리스트로 초기화
            if hasattr(block, 'connectionPoints') and block.connectionPoints:
                for cp in block.connectionPoints:
                    self.out_pipes_map[str(block.id)][cp.id] = []
            
        # 매핑 구성
        for conn in connections:
            pipe_id = self.create_pipe_id(
                conn.from_block_id, conn.from_connector_id,
                conn.to_block_id, conn.to_connector_id
            )
            
            # 입력 파이프 매핑
            self.in_pipes_map[str(conn.to_block_id)].append(pipe_id)
            
            # 출력 파이프 매핑
            to_block = next((b for b in blocks if str(b.id) == str(conn.to_block_id)), None)
            # to_connector의 실제 이름 찾기
            to_connector_name = conn.to_connector_id
            if to_block and hasattr(to_block, 'connectionPoints') and to_block.connectionPoints:
                for cp in to_block.connectionPoints:
                    if cp.id == conn.to_connector_id:
                        to_connector_name = cp.name
                        break
                        
            # 여러 연결을 지원하기 위해 리스트에 추가
            if conn.from_connector_id not in self.out_pipes_map[str(conn.from_block_id)]:
                self.out_pipes_map[str(conn.from_block_id)][conn.from_connector_id] = []
                
            self.out_pipes_map[str(conn.from_block_id)][conn.from_connector_id].append({
                'pipe_id': pipe_id,
                'block_id': conn.to_block_id,
                'block_name': to_block.name if to_block else 'Unknown',
                'connector_id': conn.to_connector_id,
                'connector_name': to_connector_name
            })
            
    def get_pipe(self, pipe_id: str) -> Optional[simpy.Store]:
        """파이프를 가져옵니다."""
        return self.pipes.get(pipe_id)
        
    def get_input_pipes(self, block_id: str) -> List[str]:
        """블록의 입력 파이프 목록을 반환합니다."""
        return self.in_pipes_map.get(str(block_id), [])
        
    def get_output_pipes(self, block_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """블록의 출력 파이프 정보를 반환합니다. 각 커넥터는 여러 연결을 가질 수 있습니다."""
        return self.out_pipes_map.get(str(block_id), {})
        
    def find_pipe_by_arrival(self, block_id: str, connector_id: str) -> Optional[str]:
        """도착 정보로 파이프를 찾습니다."""
        for pipe_id in self.pipes:
            if pipe_id.endswith(f"to_{block_id}_{connector_id}"):
                return pipe_id
        return None
        
    def reset(self):
        """파이프 관리자를 초기화합니다."""
        self.pipes.clear()
        self.in_pipes_map.clear()
        self.out_pipes_map.clear()