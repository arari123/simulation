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
4. **Wait for user to test** the fixes and provide feedback

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

## Project Overview

Vue.js 3 + FastAPI 제조 공정 시뮬레이션 - A high-performance manufacturing process simulation web application that allows users to visually design and simulate manufacturing processes using drag-and-drop blocks and connectors.

## Development Commands

### Frontend (Vue.js 3 + Vite)
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start development server (http://localhost:5173)
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend (FastAPI + SimPy)
```bash
cd backend

# Virtual environment setup (first time)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run server
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the script
./run_backend.sh
```

### Backend Server Logging
**Log File Location**: `backend/logs/backend_server.log`
- Auto-created on server start
- Fresh log for each server restart
- 200 line limit with rotation (keeps last 100 lines)
- Contains server events, API calls, simulation debug logs
- Reset on simulation reset via `/simulation/reset`
- **Primary debugging tool** - Always check logs when issues occur
- Log format: `YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message`

## Architecture Overview

### Backend Architecture - Simple Engine v3 (Current)
**Revolutionary change**: 90% code reduction from previous architecture

**Core Files:**
- `app/simple_simulation_engine.py` - Main engine orchestration
- `app/simple_block.py` - Independent block objects with self-contained logic
- `app/simple_entity.py` - Lightweight entity representation
- `app/simple_signal_manager.py` - Direct signal state management
- `app/simple_script_executor.py` - Script command → function mapping
- `app/simple_engine_adapter.py` - API compatibility layer

**Architecture Principles:**
1. **Block Independence**: Each block runs its own SimPy process
2. **Script-Driven**: All behavior defined in scripts, not hardcoded
3. **Batch Processing**: Scripts execute sequentially until entity movement
4. **Direct Functions**: Each command maps to a simple function
5. **Zero Manager Dependencies**: No complex inter-manager communications

### Frontend Architecture
**Key Components:**
- `App.vue` - Main application orchestrator
- `components/CanvasArea.vue` - Konva.js-based visual simulation
- `components/shared/SettingsBase.vue` - Unified settings interface
- `components/shared/ActionEditor.vue` - Action/script editing
- Composables: `useSimulation`, `useBlocks`, `useSignals` - State management

**Entity Visualization:**
- Orange squares with numbers in blocks
- Purple squares during transit between blocks
- Global entity ID → number mapping for consistent display

## Script Syntax

### Commands
```
delay 5                           # Wait 5 seconds
신호명 = true                     # Set signal
wait 신호명 = true                # Wait for signal
wait A = true or B = true         # OR condition wait
wait A = true and B = true        # AND condition wait (NEW)
if 신호명 = true                  # Conditional (indent sub-actions)
if A = true and B = true          # AND condition (NEW)
if A = true or B = true           # OR condition (NEW)
log "메시지"                      # Log message (NEW)
go to 블록명.커넥터명             # Move to another block
go to 블록명.커넥터명,3           # Move with 3s transit delay
go from 커넥터명 to 블록명.커넥터명,3  # Move from specific connector (recommended)
jump to 1                         # Jump to line 1
// comment                        # Comment line

# Entity Attribute Commands (NEW)
product type += flip(red)         # Add 'flip' attribute and set color to red
product type += flip,1c(blue)     # Add multiple attributes and set color
product type += (green)           # Change color only without adding attributes
product type -= flip              # Remove 'flip' attribute
product type -= flip,1c           # Remove multiple attributes
product type -= (default)         # Reset color to default

# Attribute Conditions
if product type = flip            # Check single attribute
if product type = flip or 1c      # Check OR condition
if product type = flip and 1c     # Check AND condition
if product type = transit         # Check transit state

wait product type = transit       # Wait for transit state
wait product type = flip          # Wait for attribute
wait product type = flip or 1c    # Wait with OR condition
wait product type = flip and 1c   # Wait with AND condition
```

### Example Script
```
wait 공정1 load enable = true or 공정2 load enable = true
if 공정1 load enable = true
    공정1 load enable = false
    go from R to 공정1.L,3
if 공정2 load enable = true
    공정2 load enable = false
    go from R to 공정2.L,3
```

## Key Technical Details

### ID Type Handling
- All IDs are converted to strings for consistency
- Frontend and backend handle both numeric and string IDs seamlessly
- Comparison uses `String(id1) === String(id2)` pattern

### Entity Number Display
- Uses global `Map<entityId, number>` for consistent numbering
- Numbers persist across entity movements
- Reset only when simulation resets (entity count = 0)

### Script Type Actions
- Blocks can have either `actions` array or `script` field
- Script field automatically converted to script type action
- Script editor supports both viewing and editing scripts

### Step Execution
- Each step = one entity movement (not one action)
- Multiple actions execute within single step until `go to`
- Event-based stepping ensures realistic time progression

### Connector Management
- **Add Connectors**: Use "+" button in block settings
- **Delete Connectors**: Red "🗑️ 커넥터 삭제" button in connector settings
- **Move Connectors**: Drag blue dotted circle when connector is selected
- **Automatic Cleanup**: Deleting connector removes all related connections and script references

### Script Editor v2 (CodeMirror 6)
- **Advanced Features**: Syntax highlighting, real-time error checking, undo/redo
- **Error Visualization**: Red underlines on specific problematic words/phrases
- **Language Support**: Custom simulation script language definition
- **Error Detection**: Blocks with script errors show red borders and ❌ icons
- **Tooltips**: Mouse-over error details with precise error messages
- **Performance**: Debounced validation (300ms) for smooth editing experience

## Common Issues & Solutions

### Entity Numbers Changing
- **Cause**: Local entity mapping recreated each update
- **Solution**: Use global `globalEntityIdToNumber` Map

### Scripts Not Visible in Editor
- **Cause**: Missing script type handling
- **Solution**: Added script type to ActionEditor and conversion functions

### Source Block Not Creating Entities
- **Cause**: Script conditions not met or capacity full
- **Solution**: Check signals and block capacity

### Entities Stuck in Transit
- **Cause**: Destination block full or missing process
- **Solution**: Check block capacity and ensure all blocks have processes

## Performance Considerations

### Debug Mode
- Location: `backend/app/core/constants.py` (if using old engine)
- Simple engine has built-in debug logging
- Production: Minimal logging for 22,000+ steps/sec
- Debug: Detailed logging ~1,000 steps/sec

### Frontend Optimization
- Partial rendering with dirty flags
- Entity updates batched
- Canvas operations minimized

## Important Development Rules

1. **Never run simulations internally** - User provides logs
2. **Script-centric design** - Avoid hardcoding logic
3. **Maintain API compatibility** - Use adapter pattern
4. **Entity ID consistency** - Always convert to strings
5. **Global state for persistence** - Entity numbers, signals
6. **Preserve existing functionality** - When adding new features, create separate modules to avoid breaking current code
7. **Intuitive script commands** - Commands should be easy to understand for non-programmers
8. **Add new functions, don't modify** - When adding script commands, create new functions instead of modifying existing ones
9. **NO HARDCODED VALUES** - All timing, delays, and configuration must come from scripts or config files

## 🧪 테스트 필요 사항

### 조건부 명령어 동작 테스트 (우선순위: 중)
다음 조건부 명령어들의 정상 동작 확인이 필요함:

**IF 조건문:**
- `if 신호A = true` (기본 단일 조건)
- `if 신호A = true and 신호B = true` (AND 조건 - 새로 구현됨)
- `if 신호A = true or 신호B = true` (OR 조건 - 기존 구현)
- `if product type = test` (엔티티 속성 조건)
- `if product type = test and flip` (혼합 조건)

**WAIT 조건문:**
- `wait 신호A = true` (기본 단일 조건)
- `wait 신호A = true and 신호B = true` (AND 조건 - 새로 구현됨)
- `wait 신호A = true or 신호B = true` (OR 조건 - ✅ 테스트 완료)
- `wait product type = test` (엔티티 속성 조건)
- `wait product type = test and flip` (혼합 조건)

**테스트 현황:**
- ✅ OR 대기 조건: 정상 동작 확인 완료
- ⏳ 나머지 조건들: 테스트 대기중

**테스트 파일:**
- `test_or_wait_simple.json` - OR 조건 테스트용 (완료)
- `test_if_wait_conditions.json` - 종합 조건 테스트용 (테스트 필요)

## Recent Major Changes

### 2025-06-06: Advanced Script Editor v2 & Error Visualization ✅
- **Complete Script Editor Replacement**: Revolutionary CodeMirror 6-based editor
  - Professional-grade editing experience with syntax highlighting
  - Real-time grammar checking with precise error positioning
  - Support for Undo/Redo (Ctrl+Z, Ctrl+Y), Tab indentation, line numbers
  - Custom language definition for simulation scripts
  - Advanced error display with red underlines on specific words/phrases
- **Visual Error Detection System**: Instant script error identification
  - Blocks with script errors display red borders and ❌ icons
  - Error count display (`3개 오류`) on problematic blocks
  - Mouse-over tooltips showing detailed error information
  - Automatic validation on JSON file load
  - Covers both block actions and connector actions
- **Enhanced Script Validation**: Improved accuracy and user experience
  - Comment-aware validation (ignores `// comments`)
  - Precise error positioning on exact problematic tokens
  - Support for all script commands including AND/OR conditions
  - Stricter delay validation (numbers only, no variable names)

### 2025-06-06: 용량 초과 경고 시스템 및 스크립트 검증 개선
- **용량 초과 경고 시스템**: 블록 용량 초과로 엔티티 이동 실패 시 경고 메시지 표시
  - 백엔드: 경고 생성, 5초 후 자동 삭제, 1초 간격 로그로 스팸 방지
  - 프론트엔드: 블록 근처에 "⚠️ 용량 초과" 시각적 표시
- **스크립트 검증 개선**: 들여쓰기된 log 명령어 오류 인식 문제 수정
  - log 명령어가 신호 설정 명령어로 잘못 인식되던 문제 해결
  - 들여쓰기 상황에서의 정확한 명령어 구분 로직 개선

### 2025-06-03: Simple Engine v3
- Complete engine rewrite (90% code reduction)
- Replaced 7-manager system with 4 simple classes
- All behavior now script-driven
- Added OR condition support for wait commands
- Fixed entity number persistence issue

### Frontend Improvements
- Script type action support in editor
- Global entity number mapping
- Enhanced transit entity visualization
- Tab key support in script editors

### 2025-06-05: Entity Attributes Feature
- **Entity Custom Attributes**: Added support for custom entity attributes
  - Entities can have multiple string attributes (e.g., flip, 1c)
  - Automatic transit state tracking during movement
  - Support for 6 colors: gray, blue, green, red, black, white
- **New Script Commands**:
  - `product type +=` for adding attributes and colors
  - `product type -=` for removing attributes
  - Conditional checks with OR/AND logic
  - Wait conditions for entity states and attributes
- **Frontend Color Support**: 
  - Entities display with assigned colors
  - Automatic text color adjustment for visibility
  - Transit entities maintain color during movement

### 2025-06-06: Entity Attribute System Implementation ✅
- **Complete Entity Attribute System**: Full implementation of custom entity attributes
  - Added entity state tracking: "normal" and "transit" states
  - Implemented custom attributes as Set (e.g., flip, 1c)
  - Added 6 color support: gray, blue, green, red, black, white
  - Script commands: `product type += attribute(color)` and `product type -= attribute`
  - Conditional checks: `if/wait product type = attribute1 and attribute2`
  - OR logic support: `wait product type = flip or product type = 1c`
- **Backend Enhancements**:
  - Extended SimpleEntity model with state, custom_attributes, and color fields
  - Implemented product type command parsers in script executor
  - Transit state automatically set during entity movement
  - Attributes persist across block movements
- **Frontend Updates**:
  - Dynamic entity color rendering based on backend state
  - EntityState model includes color and custom_attributes
  - Visual feedback for entity states during simulation
- **Bug Fixes**:
  - Fixed field mapping issue: ProcessBlockConfig uses 'capacity' not 'maxCapacity'
  - Backend now correctly reads capacity from frontend (was defaulting to 100)
  - Removed debug console.print() statements from backend
  - Removed repetitive console.log statements from frontend
  - Added missing /simulation/update-settings endpoint

### Recent Fixes (Latest)
- **Script Priority Fix**: Fixed script action priority in backend engine (2025-06-04)
  - Backend now prioritizes `actions` array script type over legacy `script` field
  - Resolves 10-second delay issue when user edits scripts in UI
  - Ensures UI script changes are properly saved and executed
- **Connector Deletion Feature**: Complete implementation of connector removal (2025-06-04)
  - Added "🗑️ 커넥터 삭제" button in connector settings popup
  - Automatically removes all related connection lines
  - Includes confirmation dialog to prevent accidental deletion
  - Refreshes auto-connections after deletion to clean up script references
- **Script Editor Save Issue**: Fixed script changes not being saved properly
  - ScriptEditor now passes both parsed actions and raw script text
  - SettingsBase creates proper script type actions
  - Backend recognizes and executes script type actions
- **Time Display Accuracy**: Fixed floating point accumulation errors
  - Frontend displays time with exactly 1 decimal place
  - Backend rounds all time values to 1 decimal place
  - Wait command check interval reduced from 0.1s to 0.01s
  - Source block generation timing aligned with transit delays

### 2025-06-04: Connector Drag Feature Implementation ✅
- **Complete Connector Position Movement**: Fully functional drag-and-drop for connectors
  - Manual drag system to prevent premature drag end issues
  - Free movement within block boundaries with magnetic snap to edges
  - Temporary position storage for smooth prop updates
  - Synchronized movement of connector, drag handle (blue dotted circle), and labels
  - Event listener cleanup to prevent duplicate executions
- **Technical Implementation**: 
  - Used Konva.js manual mouse event handling instead of built-in drag
  - Temporary position mapping (`temporaryConnectorPositions`) for seamless UI updates
  - Constraint and snap algorithm for automatic edge alignment
  - Real-time connection line updates during drag operations