# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL: Testing & Simulation Execution Rules ⚠️

### 🚨 IMPORTANT: User-Driven Testing Only 🚨
**THE USER PERFORMS ALL SIMULATION TESTS - AI MUST NOT RUN SIMULATIONS**

1. **NEVER execute simulation commands** (e.g., curl for /simulation/step)
2. **WAIT for user to provide logs** from their testing
3. **ANALYZE logs provided by user** and suggest fixes
4. **NO automated testing** - this saves tokens and provides real-world results

**Why this approach:**
- User has the actual runtime environment
- Saves significant API tokens and time
- More accurate real-world testing results
- User can observe visual UI behavior

### When User Reports Issues:
1. **Ask user to provide the log file** or relevant log excerpts
2. **Analyze the provided logs** to identify issues
3. **Suggest code fixes** based on log analysis
4. **WAIT for user to test** the fixes and provide feedback

### 🔍 Debug Strategy:
- **Focus on the latest logs** rather than initial logs
- **Analyze current state** from the most recent log entries
- **Make targeted fixes** based on the specific issues shown in logs
- **Avoid obsessing over initial state** - work with what's currently happening

### 🚨 CRITICAL: Simulation Debugging Principles 🚨
**NEVER MODIFY JSON FILES TO "FIX" SIMULATION LOGIC ISSUES**

When users report simulation abnormal behavior:
1. **DO NOT modify JSON configuration files** to make the simulation "work somehow"
2. **DO NOT add hardcoding to the engine** to force simulation progress
3. **ACCEPT logical deadlocks** - If the simulation environment has logical errors that prevent entity movement, let it remain stuck
4. **PRESERVE debugging capability** - Modifying JSON to bypass issues makes future debugging impossible

**Why this is critical:**
- JSON modifications hide root causes instead of solving them
- Users need to understand when their simulation logic has errors
- Deadlocks and stuck states are valuable debugging information
- The simulation should faithfully reflect the configured logic, even if flawed

**Correct approach:**
- Analyze and explain WHY the simulation is stuck
- Point out the logical errors in the configuration
- Let users decide how to fix their simulation logic
- Only modify engine code for actual bugs, not to bypass user logic errors

### 🚨 CRITICAL: Engine Must Execute Scripts As Written 🚨
**NEVER MODIFY ENGINE TO "FIX" SCRIPT LOGIC ISSUES**

When a script has logical errors:
1. **DO NOT modify engine behavior** to make problematic scripts "work"
2. **EXECUTE scripts exactly as written** - Even if they cause problems
3. **PRESERVE script errors** - They are valuable feedback for users
4. **NO SPECIAL HANDLING** - Don't add engine logic to prevent script issues

**Examples of WRONG approaches:**
- "First go to wins" logic to prevent multiple go to commands
- Stopping script execution mid-way to avoid problems
- Adding conditions to skip certain script lines
- Modifying entity behavior to compensate for script errors

**Correct approach:**
- Execute ALL script lines from start to finish
- If multiple go to commands exist, the last one applies
- If script causes infinite loops, let it happen
- Users must fix their scripts, not the engine

## Memory Guidance

### Script Design Principles
- **스크립트 명령은 직관적이어야 함**: 복잡한 옵션이나 조건을 추가하면 사용성이 떨어짐
- **명령어는 예측 가능하게 동작해야 함**: execute는 항상 즉시 실행, go는 이동 요청 등
- **사용자가 타이밍을 제어할 수 있어야 함**: 필요시 delay나 wait를 명시적으로 사용
- **특수한 경우를 위한 복잡한 옵션 추가 지양**: 모든 시나리오를 하나의 명령어로 해결하려 하지 말 것

### Execute Command Principles (CRITICAL)
- **`execute` 명령은 엔티티 유무와 상관없이 즉시 실행되어야 함**
- **`execute` 명령은 비동기적으로 실행되어 호출한 블록을 블로킹하지 않아야 함**
- **절대 execute에 엔티티 대기 로직이나 조건을 추가하지 말 것**

### Simulation Configuration Issues
- 유저가 시뮬레이션 동작오류 보고 시 시뮬레이션 환경(설정 json 파일)에 오류가 있다고 판단되면 이에 대해 설명하고 엔진 코드 수정 지양하기
- 동작 오류 시 시뮬레이션 환경 하드코딩 방식을 금지하고 엔진의 오류를 탐색한다

## Script Syntax

### Basic Commands
```
delay 5                           # Wait 5 seconds
신호명 = true                     # Set signal
wait 신호명 = true                # Wait for signal
wait A = true or B = true         # OR condition wait
wait A = true and B = true        # AND condition wait
if 신호명 = true                  # Conditional (indent sub-actions)
if A = true and B = true          # AND condition
if A = true or B = true           # OR condition
elif 신호명 = false               # Else-if condition (NEW)
else                              # Else clause (NEW)
log "메시지"                      # Log message
go 커넥터명 to 블록명.커넥터명          # Move from connector (default: entity 0)
go 커넥터명 to 블록명.커넥터명(0)       # Move entity at index 0
go 커넥터명 to 블록명.커넥터명(1,3)     # Move entity at index 1 with 3s delay
jump to 1                         # Jump to line 1
// comment                        # Comment line
create product                    # Create new entity (force execution blocks)
dispose product                   # Remove entity from simulation
force execution                   # Enable block to run without entities
execute 블록이름                  # Execute target block's script (NEW)

# Entity Attribute Commands
# New indexed syntax for multiple entities
product type(0) = flip            # Set attributes for first entity (index 0)
product type(1) = flip,1c         # Set attributes for second entity
product type(0) = flip(red)       # Set attributes and color
if product type(0) = transit      # Check if first entity is in transit
if product type(1) = flip         # Check if second entity has flip attribute
if product type(0) != transit     # Check if first entity is NOT in transit
if product type(1) != flip        # Check if second entity does NOT have flip attribute

# Legacy syntax (applies to first entity only)
product type += flip(red)         # Add 'flip' attribute and set color to red
product type += flip,1c(blue)     # Add multiple attributes and set color
product type += (green)           # Change color only without adding attributes
product type -= flip              # Remove 'flip' attribute
product type -= flip,1c           # Remove multiple attributes
product type -= (default)         # Reset color to default

# Block Status Commands (NEW)
블록이름.status = "running"        # Set block status to "running"
공정1.status = "idle"              # Set 공정1 block status to "idle"  
투입.status = "준비중"              # Korean status values supported
시스템모니터.status = "점검중"      # Spaces in block names require no spaces

# Integer Variable Commands (Enhanced with Korean support)
int counter = 10                  # Set integer variable to value
int counter += 5                  # Add to integer variable
int counter -= 3                  # Subtract from integer variable
int counter *= 2                  # Multiply integer variable
int counter /= 4                  # Divide integer variable (integer division)
int result = var1                 # Copy value from another variable
int 공정1처리수 += 1               # Korean variable names supported
int 대기시간 = 30                  # Initialize Korean named variable

# Integer Comparisons (NEW)
if count > 5                      # Greater than
if count < 10                     # Less than
if count >= 5                     # Greater than or equal
if count <= 10                    # Less than or equal
if count = 10                     # Equal to
if count != 5                     # Not equal to
if count > threshold              # Compare with another variable

# Mixed Conditions (NEW)
if enabled = true and count > 5   # Boolean AND integer condition
if active = true or count < 10    # Boolean OR integer condition
wait count >= 5                   # Wait for integer condition
wait count > limit                # Wait comparing variables

# Variable Interpolation in Logs (NEW)
log "Current count: {counter}"    # Display variable value in log
log "Processing entity, count:" counter  # Without braces also works

# Entity Attribute Interpolation in Logs (NEW)
log "Entity ID: {entity.id}"      # Display entity ID
log "Entity color: {entity.color}"     # Display entity color (or 'default')
log "Entity attributes: {entity.attributes}"  # Display comma-separated attributes (or 'none')
log "Entity state: {entity.state}"     # Display entity state (normal/transit)

# Indexed Entity Attribute Interpolation (NEW)
log "First entity: {entity(0).id}"           # Display ID of first entity in block
log "Second entity color: {entity(1).color}" # Display color of second entity
log "Third entity attrs: {entity(2).attributes}" # Display attributes of third entity
log "Entity 0 state: {entity(0).state}"     # Display state of first entity
```

### Script Examples

#### Example 1: if/elif/else Usage (NEW)
```
force execution
log "투입 스크립트 실행"
if count = 0
  create product
  log "red 엔티티 생성"
  product type(0) = red(red)
  int count += 1
elif count = 1
  create product
  log "blue 엔티티 생성"
  product type(0) = blue(blue)
  int count = 0
else
  log "예상치 못한 count 값: {count}"
  int count = 0
```

#### Example 2: Execute Command Usage
```
# 투입 블록 (force execution)
force execution
create product
go OUT to 공정1.IN
execute 공정1         // 공정1 블록의 스크립트 실행

# 공정1 블록
log "공정1 시작"
delay 5
go OUT to 공정2.IN
execute 공정2         // 공정2 블록의 스크립트 실행

# 공정2 블록  
log "공정2 처리"
if 품질검사 = true
    execute 완료      // 조건에 따라 다른 블록 실행
if 품질검사 = false
    execute 재작업
```

#### Example 2: Counter with Conditional Routing
```
int counter += 1
log "Processing entity, counter: {counter}"
if counter >= 10
    done = true
    log "Limit reached!"
delay 2
if counter > 5
    go L to highPriority.IN(0,1)
if counter <= 5
    go L to normalProcess.IN(0,1)
```

#### Example 3: Integer Operations
```
int x = 10
int y = 5
int result = x
int result += y      // result = 15
int result *= 2      // result = 30
int result /= 3      // result = 10 (integer division)
log "Final result: {result}"
```

#### Example 4: Wait for Integer Condition
```
wait counter >= threshold
log "Threshold reached"
int counter = 0     // Reset counter
```

### Variable Types

The simulation supports two types of global variables:

1. **Boolean Signals** (기존)
   - Values: `true` or `false`
   - Used for: State control, conditions
   - Example: `ready = true`, `if ready = true`

2. **Integer Variables** (NEW)
   - Values: Any integer number
   - Used for: Counting, arithmetic, comparisons
   - Example: `int count = 0`, `if count > 5`

### Important Notes

- Integer division (`/=`) always returns an integer (truncates decimals)
- Variables are global across all blocks
- Uninitialized variables default to: boolean=false, integer=0
- Variable names are case-sensitive
- Variables persist across simulation steps until reset

## Recent Major Updates

### 2025-06-12: elif and else Conditional Support ✅
- **elif and else Commands**: Added support for elif and else conditional statements
  - New syntax: `elif condition` and `else`
  - Proper if/elif/else chain execution - only one branch executes
  - Works with all existing condition types (boolean, integer comparisons, entity attributes)
  - Supports proper indentation and nesting
- **Implementation**:
  - Added elif/else parsing in script executor
  - Tracks if any condition in the chain was met
  - Updated validator and syntax highlighter
  - Full backward compatibility with existing if statements
- **Benefits**:
  - Cleaner conditional logic without complex workarounds
  - Avoids duplicate condition execution issues
  - More readable and maintainable scripts

### 2025-06-12: Indexed Entity Attribute in Log Commands ✅
- **Entity Index Support in Logs**: Log commands can now access specific entities by index
  - New syntax: `{entity(0).id}`, `{entity(1).color}`, `{entity(2).attributes}`
  - Index refers to entity position in block's entity list (0-based)
  - Out of range indices return the original placeholder text
  - Backward compatible: `{entity.id}` still works for current entity
- **Implementation**:
  - Added indexed entity parsing in `execute_log` method
  - Block reference stored in script executor for entity list access
  - Regex pattern matches `entity(index).attribute` syntax
  - Supports all entity attributes: id, color, attributes, state
- **Use Cases**:
  - Display all entities in a block for debugging
  - Monitor specific entity positions in queues
  - Compare multiple entities in the same block

### 2025-06-10: Go Command Synchronous Movement ✅
- **Go Command Behavior Change**: `go` commands now wait for movement completion
  - Previously: `go` command would request movement and continue immediately
  - Now: `go` command blocks until entity reaches destination or fails
  - Movement completion states:
    - Success: Entity arrives at target block
    - Failure: Target block capacity exceeded or not found
  - Script execution continues only after movement resolution
- **Benefits**:
  - Predictable script execution order
  - Can react to movement failures immediately
  - No need for complex wait conditions after movement
- **Implementation**:
  - Added `movement_completed` and `movement_failed` flags to entities
  - Direct movement processing in `execute_go_move` when engine reference available
  - Removed redundant asynchronous movement processing from block processes

### 2025-06-10: Execute Command & Script Execution Control ✅
- **Major Architecture Change**: Removed automatic script execution on entity arrival
  - Scripts no longer execute automatically when entities arrive at blocks
  - Introduced `execute 블록이름` command for explicit script execution
  - Blocks now have execution states: `idle` and `running`
  - Execute commands are ignored if target block is already running
- **Benefits**:
  - Clearer execution flow with explicit control
  - Reduced bugs from complex entity tracking logic
  - More flexible simulation scenarios
  - Easier debugging and maintenance
- **Force Execution**: Maintained infinite loop behavior for blocks with `force execution`
- **Migration**: Existing simulations need to add `execute` commands where blocks should run

### 2025-06-08: Breakpoint Debugging System Implementation ✅
- **Complete Breakpoint System**: Full debugging capability with breakpoints
  - Click line numbers in script editor to set/unset breakpoints
  - Visual indicators (red dots) for active breakpoints
  - Execution pauses when hitting breakpoints
  - Continue execution button to resume from breakpoints
- **Backend Architecture**:
  - Added `DebugManager` class for breakpoint management
  - Global and engine-specific debug state management
  - Debug API endpoints: `/debug/breakpoints`, `/debug/control`, `/debug/status`
  - Breakpoint hit detection during script execution
- **Frontend Features**:
  - Debug control panel with active breakpoint list
  - Real-time breakpoint status updates
  - Continue execution and clear all breakpoints buttons
  - Breakpoints persist across script editor open/close
  - Immediate display of breakpoints in debug panel when set
- **User Experience**:
  - Breakpoint locations show with block names (e.g., "투입 라인 7")
  - Step execution disabled while paused at breakpoint
  - Clear visual feedback for debug state
  - All breakpoints properly cleared from UI when using "Clear All"

### 2025-06-07: Block Status Attributes & Korean Variable Support ✅
- **Block Status Attributes**: New block status system
  - New syntax: `블록이름.status = "값"` (e.g., `공정1.status = "처리중"`)
  - Status displayed at the top of blocks in UI (italic style)
  - Status automatically cleared on simulation reset
  - Full script editor support with validation
- **Korean Variable Names**: Integer variables now support Korean names
  - Example: `int 공정1처리수 += 1`
  - Works with all integer operations
- **Block Color Customization**: Blocks can have custom colors
  - Background color and text color separately configurable
  - Color picker UI with HEX input support
  - Default colors: background #cfdff7 (light blue), text #000000 (black)
  - Block selection shows only border highlight (no fill color change)
- **Implementation Details**:
  - Backend: Added status field to IndependentBlock class
  - Script executor: Added parsing for `.status =` commands
  - Frontend: Status display above block box, cleared on reset
  - CanvasArea.vue: Added backgroundColor and textColor support
  - SettingsBase.vue: Added color picker UI components
  - Important: Block status commands use dot notation (`.status =`) to distinguish from signal assignments

### 2025-06-06: Integer Variable System Implementation ✅
- **Integer Variable Support**: Complete implementation of integer type variables
  - New variable type system with backward compatibility
  - Arithmetic operations: `+=`, `-=`, `*=`, `/=`
  - Comparison operators: `>`, `<`, `>=`, `<=`, `=`, `!=`
  - Variable interpolation in log messages: `log "count: {variable}"`
- **Backend Architecture**:
  - Added `IntegerVariableManager` class for integer variable management
  - Created `UnifiedVariableAccessor` for unified access to both types
  - Extended script executor with integer operation support
- **Frontend Updates**:
  - Global signal panel now supports type selection (boolean/integer)
  - Conditional rendering based on variable type
  - Script validation extended for integer operations
- **Script Editor Enhancements**:
  - Added 'int' keyword highlighting
  - Support for all integer operators in syntax highlighting
  - Real-time validation for integer variable commands

### 2025-06-06: If Block Visual Representation ✅
- **Script Editor If Block Visualization**: Visual distinction for if blocks and their indented content
  - If statements highlighted with blue background and left border
  - Indented blocks within if statements have lighter blue background
  - Integrated into existing syntax highlighter for seamless experience
  - Supports nested if blocks with visual hierarchy
- **Implementation Details**:
  - Extended SimpleHighlighter.js with if block detection
  - Added line decorations for if statements and indented blocks
  - No additional dependencies or complex imports
  - Works with tabs, 4 spaces, and 2 spaces indentation

### 2025-01-07: Block Processing Count Display ✅
- **Block Processing Counter**: Display total processed entities for each block
  - Shows "처리: X" below each block in green color
  - Counts entities processed via `dispose entity` command
  - Real-time updates during simulation
  - Positioned outside block boundaries for better visibility

### 2025-01-07: Canvas Information Text Panel ✅
- **Info Text Panel**: Rich text information display at canvas top
  - Fixed position panel responsive to control panel width
  - Click to toggle minimize/expand states
  - Minimized: Shows first line only with ellipsis
  - Expanded: Shows full text with transparent background
  - Rich Text Editor Features:
    - Bold formatting for selected text
    - Color picker for selected text
    - Font size adjustment (12-24px) for selected text
    - Proper Korean text input support
  - Auto-saves to simulation JSON configuration
  - Teleport-based rendering for consistent positioning

### 2025-01-07: Simulation Log Viewer Implementation ✅
- **Script Log Display**: Web UI display for script `log` commands
  - LogPanel component positioned at bottom-left (next to control panel)
  - Real-time log collection from script execution
  - Variable interpolation support: `log "count: {variable}"`
  - Log filtering by text search and block name
  - Export functionality (TXT, CSV, JSON formats)
  - Auto-scroll toggle and minimize/maximize
  - Color coding for log levels (ERROR: red, WARNING: yellow)
- **Backend Architecture**:
  - Added log collection to SimpleScriptExecutor
  - Block-level log aggregation in SimpleBlock
  - Engine-level log collection and API response
  - Added `script_logs` field to SimulationStepResult model
- **Frontend Components**:
  - LogPanel.vue: Main log viewer component
  - useSimulationLogs.js: Log state management composable
  - Initial state: minimized (collapsed)
- **UI Improvements**:
  - z-index hierarchy fixed for proper layering
  - Responsive positioning to avoid control panel overlap
  - Initial states: Log panel minimized, Global signals hidden

### 2025-06-08: Execution Mode System Improvements ✅
- **High-Speed Mode Removal**: Simplified execution system
  - Removed high-speed execution mode to reduce complexity
  - Now only two modes: Default (entity movement) and Time Step
  - Cleaner code and easier maintenance
- **Time Step Mode Improvements**:
  - Set upper limit of 10 seconds for stable UI updates
  - Added validation to prevent values over 10 seconds
  - Time step duration preserved across simulation setup
- **Input UX Enhancements**:
  - Changed from @input to @blur event for better user experience
  - Users can now clear input fields without interference
  - Empty value handling without forcing default values
- **Mode Synchronization Fix**:
  - Fixed bug where mode changes weren't properly applied
  - Adapter now always applies its mode to the engine during setup
  - Mode persistence works correctly across simulations
- **Implementation Details**:
  - Backend: Removed `step_simulation_high_speed` method entirely
  - Frontend: Removed high-speed option from mode selector dropdown
  - Added 10-second cap in `set_execution_mode` with warning log
  - Fixed duplicate function declaration error in ControlPanel.vue