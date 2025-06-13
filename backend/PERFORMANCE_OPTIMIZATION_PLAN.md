# Script Executor Performance Optimization Plan

## Performance Issues Identified

### 1. Debug Manager Overhead (CRITICAL)
**Problem**: `check_breakpoint` is called for every single line, even when no breakpoints exist
- Line 1049-1058 in execute_script
- Creates a generator yield on every line
- Significant overhead for scripts with many lines

**Solution**:
```python
# Add fast path check at the beginning of execute_script
has_breakpoints = (self.debug_manager and 
                  self.debug_manager.breakpoints and 
                  block and 
                  block.id in self.debug_manager.breakpoints)

# Then only check if needed
if has_breakpoints:
    yield from self.debug_manager.check_breakpoint(...)
```

### 2. Repeated String Operations (HIGH IMPACT)
**Problem**: Multiple string operations on the same line
- `line.strip()` called multiple times
- `line.lstrip()` for indentation calculation
- String slicing and splitting repeatedly

**Solution**:
```python
# Pre-process all lines once
processed_lines = []
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped and not stripped.startswith('//'):
        indent = len(line) - len(line.lstrip())
        processed_lines.append((i, stripped, indent))
```

### 3. Regex Compilation Overhead (MEDIUM IMPACT)
**Problem**: Regular expressions compiled on every parse_script_line call
- Lines 273, 251, 509, 643, 798, 846, etc.

**Solution**:
```python
# Pre-compile all patterns in __init__
self._compiled_patterns = {
    'product_index_not': re.compile(r'^product\s+type\((\d+)\)\s*!=\s*(.+)$'),
    'product_index_eq': re.compile(r'^product\s+type\((\d+)\)\s*=\s*(.+)$'),
    # ... other patterns
}
```

### 4. Inefficient Command Parsing (MEDIUM IMPACT)
**Problem**: Sequential string checks with startswith()
- Lines 794-925 check each command type sequentially

**Solution**:
```python
# Use command prefix checking
if line[:6] == 'delay ':  # Faster than startswith
    return 'delay', line[6:]
elif line[:4] == 'log ':
    return 'log', line[4:]
# Check most common commands first
```

### 5. Line Caching (LOW-MEDIUM IMPACT)
**Problem**: Same lines parsed multiple times in loops

**Solution**:
```python
# Add line cache
self._line_cache = {}

# In parse_script_line
if line in self._line_cache:
    return self._line_cache[line]
# ... parse line
self._line_cache[line] = (command, params)
```

## Implementation Priority

1. **Debug Manager Fast Path** (Highest impact, easiest to implement)
   - Estimated performance improvement: 30-50%
   - Risk: Very low

2. **Pre-process Lines** (High impact, moderate complexity)
   - Estimated performance improvement: 20-30%
   - Risk: Low

3. **Pre-compile Regex** (Medium impact, easy to implement)
   - Estimated performance improvement: 10-15%
   - Risk: Very low

4. **Optimize Command Parsing** (Medium impact, moderate complexity)
   - Estimated performance improvement: 10-15%
   - Risk: Low

5. **Add Line Caching** (Low impact, easy to implement)
   - Estimated performance improvement: 5-10%
   - Risk: Very low

## Total Expected Performance Improvement
Combined optimizations should provide 60-80% performance improvement for script execution.

## Testing Strategy
1. Create performance benchmarks before optimization
2. Apply optimizations incrementally
3. Measure impact of each optimization
4. Ensure no functionality is broken
5. Test with various script sizes and complexity

## Additional Recommendations
1. Consider lazy loading of debug manager
2. Use `__slots__` for frequently created objects
3. Profile with cProfile to find other bottlenecks
4. Consider Cython for critical paths if needed