"""
Optimized Script Executor with Performance Improvements
This file shows the key optimizations that should be applied to simple_script_executor.py
"""

import re
from typing import Dict, Pattern

class OptimizedScriptExecutor:
    """Key optimizations to apply to SimpleScriptExecutor"""
    
    def __init__(self):
        # Pre-compile all regex patterns
        self._compiled_patterns: Dict[str, Pattern] = {
            'product_index_not': re.compile(r'^product\s+type\((\d+)\)\s*!=\s*(.+)$'),
            'product_index_eq': re.compile(r'^product\s+type\((\d+)\)\s*=\s*(.+)$'),
            'product_assign': re.compile(r'^product\s+type\((\d+)\)\s*=\s*(.+)$'),
            'int_operation': re.compile(r'^int\s+([\w가-힣]+)\s*([\+\-\*\/]?=)\s*(.+)$'),
            'go_pattern': re.compile(r'^go\s+([^\s]+)\s+to\s+([^(]+)(?:\((\d+)(?:,\s*(\d+(?:\.\d+)?))?\))?$', re.IGNORECASE),
            'entity_index': re.compile(r'entity\((\d+)\)\.(.+)'),
            'color_match': re.compile(r'\(([^)]+)\)'),
            'variable_pattern': re.compile(r'\{([^}]+)\}')
        }
        
        # Cache for parsed lines
        self._line_cache: Dict[str, tuple] = {}
        
    def execute_script_optimized(self, script: str, entity, env, block=None):
        """Optimized script execution with performance improvements"""
        lines = script.strip().split('\n')
        
        # Pre-process all lines once
        processed_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('//'):
                indent = len(line) - len(line.lstrip())
                processed_lines.append((i, stripped, indent))
            else:
                processed_lines.append((i, None, 0))
        
        # Check if debugging is needed at all
        has_breakpoints = (self.debug_manager and 
                          self.debug_manager.breakpoints and 
                          block and 
                          block.id in self.debug_manager.breakpoints)
        
        line_index = 0
        while line_index < len(processed_lines):
            orig_index, stripped_line, indent = processed_lines[line_index]
            
            if not stripped_line:
                line_index += 1
                continue
            
            # Only check breakpoints if they exist for this block
            if has_breakpoints:
                yield from self.debug_manager.check_breakpoint(
                    block.id, 
                    orig_index + 1,
                    env
                )
            
            # Use cached parse result if available
            if stripped_line in self._line_cache:
                command, params = self._line_cache[stripped_line]
            else:
                command, params = self.parse_script_line_optimized(stripped_line)
                self._line_cache[stripped_line] = (command, params)
            
            # Execute command...
            line_index += 1
    
    def parse_script_line_optimized(self, line: str) -> tuple:
        """Optimized line parsing with pre-compiled regex"""
        # Check most common commands first
        if line[:6] == 'delay ':
            return 'delay', line[6:]
        
        if line[:4] == 'log ':
            message = line[4:]
            if message[0] == '"' and message[-1] == '"':
                message = message[1:-1]
            return 'log', message
        
        if line[:3] == 'go ':
            match = self._compiled_patterns['go_pattern'].match(line)
            if match:
                params = {
                    'from_connector': match.group(1),
                    'to_target': match.group(2),
                    'entity_index': int(match.group(3)) if match.group(3) else 0
                }
                if match.group(4):
                    params['delay'] = match.group(4)
                return 'go_move', params
        
        if line[:3] == 'if ':
            return 'if', line[3:]
        
        if line[:5] == 'elif ':
            return 'elif', line[5:]
        
        if line == 'else':
            return 'else', None
        
        # Continue with other commands...
        return None, None
    
    def check_breakpoint_optimized(self, block_id: str, line_number: int, env):
        """Optimized breakpoint check"""
        # Fast path: no debugging at all
        if not self.debug_state.is_debugging and not self.breakpoints:
            yield env.timeout(0)
            return
        
        # Fast path: debugging but no breakpoints for this block
        if block_id not in self.breakpoints:
            yield env.timeout(0)
            return
        
        # Only do expensive checks if needed
        if line_number in self.breakpoints[block_id]:
            # Original breakpoint handling...
            pass