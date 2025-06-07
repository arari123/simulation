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
log "메시지"                      # Log message
go to 블록명.커넥터명             # Move to another block
go to 블록명.커넥터명,3           # Move with 3s transit delay
go from 커넥터명 to 블록명.커넥터명,3  # Move from specific connector
jump to 1                         # Jump to line 1
// comment                        # Comment line
create entity                     # Create new entity (force execution blocks)
dispose entity                    # Remove entity from simulation
force execution                   # Enable block to run without entities

# Entity Attribute Commands
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
```

### Script Examples

#### Example 1: Counter with Conditional Routing
```
int counter += 1
log "Processing entity, counter: {counter}"
if counter >= 10
    done = true
    log "Limit reached!"
delay 2
if counter > 5
    go to highPriority.L,1
if counter <= 5
    go to normalProcess.L,1
```

#### Example 2: Integer Operations
```
int x = 10
int y = 5
int result = x
int result += y      // result = 15
int result *= 2      // result = 30
int result /= 3      // result = 10 (integer division)
log "Final result: {result}"
```

#### Example 3: Wait for Integer Condition
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

### 2025-06-07: Block Status Attributes & Korean Variable Support ✅
- **Block Status Attributes**: New block status system
  - New syntax: `블록이름.status = "값"` (e.g., `공정1.status = "처리중"`)
  - Status displayed at the top of blocks in UI (italic style)
  - Status automatically cleared on simulation reset
  - Full script editor support with validation
- **Korean Variable Names**: Integer variables now support Korean names
  - Example: `int 공정1처리수 += 1`
  - Works with all integer operations
- **Implementation Details**:
  - Backend: Added status field to IndependentBlock class
  - Script executor: Added parsing for `.status =` commands
  - Frontend: Status display above block box, cleared on reset
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