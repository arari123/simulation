"""
신호 트랜잭션 관리 모듈
여러 액션에서 발생하는 신호 변경을 트랜잭션으로 묶어 처리합니다.
병렬 처리 환경에서 신호 동기화 문제를 해결합니다.
"""
import simpy
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
import logging

logger = logging.getLogger(__name__)

class SignalTransaction:
    """신호 변경 트랜잭션"""
    def __init__(self, entity_id: str, source: str):
        self.entity_id = entity_id
        self.source = source  # 어느 블록/커넥터에서 발생했는지
        self.changes: List[Tuple[str, Any]] = []  # (signal_name, new_value)
        self.timestamp: Optional[float] = None
        
    def add_change(self, signal_name: str, new_value: Any):
        """신호 변경 추가"""
        self.changes.append((signal_name, new_value))
        
    def __repr__(self):
        return f"SignalTransaction(entity={self.entity_id}, source={self.source}, changes={len(self.changes)})"

class SignalTransactionManager:
    """신호 트랜잭션 관리자"""
    
    def __init__(self, signal_manager):
        self.signal_manager = signal_manager
        self.pending_transactions: deque = deque()
        self.active_transaction: Optional[SignalTransaction] = None
        self.transaction_event: Optional[simpy.Event] = None
        self.env: Optional[simpy.Environment] = None
        
    def initialize(self, env: simpy.Environment):
        """환경 초기화"""
        self.env = env
        self.transaction_event = env.event()
        # 트랜잭션 처리 프로세스 시작
        env.process(self._transaction_processor())
        
    def begin_transaction(self, entity_id: str, source: str) -> SignalTransaction:
        """새 트랜잭션 시작"""
        transaction = SignalTransaction(entity_id, source)
        transaction.timestamp = self.env.now if self.env else 0
        self.active_transaction = transaction
        logger.debug(f"{self.env.now if self.env else 0}: Beginning signal transaction for {entity_id} from {source}")
        return transaction
        
    def commit_transaction(self, transaction: SignalTransaction):
        """트랜잭션 커밋 - 큐에 추가"""
        if transaction != self.active_transaction:
            logger.warning(f"Attempting to commit inactive transaction: {transaction}")
            return
            
        self.pending_transactions.append(transaction)
        self.active_transaction = None
        
        # 트랜잭션 처리 이벤트 트리거
        if self.transaction_event and not self.transaction_event.triggered:
            self.transaction_event.succeed()
            
        logger.debug(f"{self.env.now if self.env else 0}: Committed transaction: {transaction}")
        
    def add_signal_change(self, signal_name: str, new_value: Any):
        """현재 활성 트랜잭션에 신호 변경 추가"""
        if not self.active_transaction:
            # 트랜잭션이 없으면 즉시 적용 (기존 방식)
            if self.env:
                self.signal_manager.set_signal(signal_name, new_value, self.env)
            return
            
        self.active_transaction.add_change(signal_name, new_value)
        
    def _transaction_processor(self):
        """트랜잭션 처리 프로세스"""
        while True:
            # 대기 중인 트랜잭션이 있을 때까지 대기
            if not self.pending_transactions:
                self.transaction_event = self.env.event()
                yield self.transaction_event
                
            # 모든 대기 중인 트랜잭션 처리
            while self.pending_transactions:
                transaction = self.pending_transactions.popleft()
                self._apply_transaction(transaction)
                
                # 매우 짧은 지연으로 다른 프로세스가 실행될 기회 제공
                yield self.env.timeout(0.001)
                
    def _apply_transaction(self, transaction: SignalTransaction):
        """트랜잭션 적용"""
        logger.info(f"{self.env.now}: Applying transaction from {transaction.source} with {len(transaction.changes)} changes")
        
        for signal_name, new_value in transaction.changes:
            current_value = self.signal_manager.get_signal(signal_name, None)
            if current_value != new_value:
                self.signal_manager.set_signal(signal_name, new_value, self.env)
                logger.info(f"{self.env.now}: [TRANSACTION] Signal '{signal_name}' changed from {current_value} to {new_value}")
                
    def reset(self):
        """트랜잭션 매니저 초기화"""
        self.pending_transactions.clear()
        self.active_transaction = None
        self.transaction_event = None
        self.env = None