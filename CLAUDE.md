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

⚠️ **See also: `.claude_testing_rules` file for critical testing guidelines**

## Project Overview

Vue.js 3 + FastAPI 제조 공정 시뮬레이션 - A high-performance manufacturing process simulation web application that allows users to visually design and simulate manufacturing processes using drag-and-drop blocks and connectors. **Recently optimized to achieve 22,000+ simulation steps per second.**

## Development Commands

### Frontend (Vue.js 3 + Vite)
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start development server (http://localhost:5173)
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend (FastAPI + SimPy) - High Performance
```bash
cd backend

# 가상환경 생성 및 활성화 (첫 실행 시)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (가상환경 활성화 필수)
source venv/bin/activate  # 가상환경 활성화
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는 실행 스크립트 사용
./run_backend.sh
```

### Testing & Validation
```bash
cd backend
# Performance and functionality tests
python test_performance_and_ui.py     # Comprehensive performance and UI validation
python test_reset_and_transit.py      # Reset functionality and entity visibility
python test_unified_simulation.py     # Core simulation engine tests

# Specific test scenarios
python test_complete_flow.py          # End-to-end simulation flow
python test_entity_visibility.py      # Entity tracking during transitions
```

### Server Management & Process Control
```bash
# Process identification and management
ps aux | grep uvicorn                 # Find running uvicorn processes
ps aux | grep "app.main:app"         # Find specific backend processes

# Server termination (ALWAYS required after testing)
pkill -f "app.main:app"              # Kill all backend processes
kill <PID>                           # Kill specific process by PID

# Port checking
lsof -i :8000                        # Check what's running on port 8000
```

**🚨 CRITICAL: Server Management Rules**

1. **Always terminate backend servers after testing sessions**
   - Running uvicorn processes consume system resources
   - Multiple servers can cause port conflicts and confusion
   - Clean shutdown ensures proper test environment isolation

2. **Quick cleanup:**
   ```bash
   pkill -f "app.main:app" && echo "✅ All backend servers terminated"
   ```

### Backend Server Logging
**Log File Location**: `backend/logs/backend_server.log`

**Key Features:**
- **Automatic File Creation**: Log file is created automatically when server starts
- **Fresh Start**: Each server restart creates a new log file (previous log is deleted)
- **Maximum 200 Lines**: Log automatically rotates to keep only the last 100 lines when reaching 200 lines
- **AI-Readable**: Log file can be read directly by AI for debugging
- **Simulation Reset Behavior**: Log file is completely reset when simulation is reset via `/simulation/reset` endpoint

**Log Contents:**
- Server startup/shutdown messages
- API request/response logs (uvicorn access logs)
- Application logs (info, warning, error levels)
- Simulation engine debug logs (when DEBUG_MODE = True)
- Timestamp for each log entry

**Reading Logs for Debugging:**
```bash
# View entire log file
cat backend/logs/backend_server.log

# View last 100 lines
tail -n 100 backend/logs/backend_server.log

# Watch logs in real-time
tail -f backend/logs/backend_server.log
```

**Log Configuration:**
- Configuration: `backend/app/logger_config.py`
- Automatic rotation when reaching 200 lines (keeps last 100 lines after rotation)
- Both console and file output for development convenience
- LineCountRotatingFileHandler for line-based rotation
- `reset_log_file()` function called on simulation reset

### Log Analysis Strategy
- **Focus on Latest Logs**: When debugging, analyze the most recent log entries
- **Current State Priority**: Understand what's happening now, not initial state
- **Pattern Recognition**: Look for repeated patterns in logs
- **Error Tracebacks**: Check full stack traces for root causes

## Architecture Overview

### Backend Architecture (Refactored Modular Design)
The backend has been completely refactored for modularity and dynamic simulation capabilities:

**Core Modules (v2 - Refactored):**
- `app/main.py` - FastAPI app initialization
- `app/models.py` - Pydantic data models with string ID conversion
- `app/simulation_engine_v2.py` - **Refactored modular simulation engine**
- `app/simulation_engine.py` - Legacy engine (deprecated, kept for reference)
- `app/entity.py` - Entity management with object pooling
- `app/state_manager.py` - Global simulation state with caching
- `app/script_executor.py` - Script command execution engine
- `app/utils.py` - Optimized utility functions
- `app/routes/` - API endpoint definitions with caching support

**New Modular Structure (core/):**
- `app/core/constants.py` - Centralized constants and configuration
- `app/core/entity_manager.py` - Entity lifecycle management
- `app/core/signal_manager.py` - Dynamic signal handling
- `app/core/pipe_manager.py` - Connection and routing management
- `app/core/source_manager.py` - Source block management
- `app/core/action_executor.py` - Action execution logic
- `app/core/block_processor.py` - Block process orchestration
- `app/core/monitoring.py` - Comprehensive state monitoring

**Key Improvements:**
- **No Hardcoded Values**: All hardcoded strings (블록명, 신호명) removed
- **Dynamic Signal Handling**: Any signal name can be used without code changes
- **Modular Architecture**: Each concern separated into its own manager
- **Flexible Action System**: Actions defined by configuration, not code
- **Language Agnostic**: No Korean strings hardcoded in engine

**Performance Optimizations Retained:**
- **Conditional Logging**: DEBUG_MODE controls logging overhead
- **Setup Caching**: Simulation environments are reused when configuration unchanged
- **Entity State Caching**: Cached entity states with dirty flag system
- **Timeout Optimization**: Configurable timeouts via constants

### Frontend Architecture (Vue 3 Composition API)
**Component Hierarchy:**
- `App.vue` - Main application with BlockManager integration
- `components/CanvasArea.vue` - **Enhanced with Transit entity visualization**
- `components/shared/SettingsBase.vue` - Common base for block/connector settings
- `components/shared/ActionEditor.vue` - Action editing with real-time validation
- `utils/BlockManager.js` - Centralized business logic

**Key Features:**
- **Transit Entity Visualization**: Entities are visible during block-to-block transitions (purple display on connection lines)
- Real-time script ↔ GUI synchronization
- Canvas-based drag-and-drop with Konva.js
- Performance-optimized rendering

### Simulation Flow Architecture
```
Source Block → Block Actions → Route to Connector → Connector Actions → Route to Next Block
                                      ↓
                               Transit State (Visible on UI)
```

**Critical Performance Rules:**
1. All movements use `블록명.커넥터명,딜레이` format (e.g., `go to 공정1.L,3`)
2. Entity transitions are tracked with "transit" state for UI visibility
3. Signal processing is event-driven with proper timing synchronization
4. Entity object pooling prevents memory leaks during long simulations

## Performance Optimization System

### Debug Mode Control
```python
# In constants.py
DEBUG_MODE = False  # Set to True for detailed debugging (impacts performance)
PERFORMANCE_MODE = True  # Set to False for detailed logging
MONITORING_MODE = True  # Set to True for comprehensive state monitoring
```

**Performance Impact:**
- `DEBUG_MODE = False`: 22,000+ steps/sec (production performance)
- `DEBUG_MODE = True`: ~1,000 steps/sec (detailed debugging)

### Caching System
The simulation engine implements intelligent caching:
- **Setup Caching**: `_cached_simulation_setup` prevents unnecessary environment recreation
- **Entity State Caching**: `_entity_states_cache` with dirty flag reduces computation
- **Cache Reset**: Automatically cleared during simulation reset

### Reset Functionality
```python
# Reset clears both simulation state and performance caches
await reset_simulation_endpoint()  # Clears environment + caches
```

## Configuration & Data Flow

### Base Configuration (`base.json`)
- Contains 3 default blocks: 투입 (Input), 공정1 (Process1), 배출 (Output)
- **ID Conversion**: Numeric IDs automatically converted to strings for Pydantic compatibility
- Global signals with initial values
- Transit entity paths defined by connection configuration

### API Integration
**Key Endpoints:**
- `POST /simulation/step` - **Optimized single simulation step**
- `POST /simulation/batch-step` - **High-performance multiple steps**
- `POST /simulation/reset` - **Reset with cache clearing**
- `GET /simulation/load-base-config` - Load default configuration

### Step Execution Behavior
**Critical Step Behavior Rule:**
- **Step execution continues until a `go to` action (entity movement) occurs**
- **Multiple non-movement actions (delay, signal_update, etc.) execute within a single step**
- **Only `route_to_connector` actions that cause entity movement trigger a new step**
- **Each step represents one complete entity movement: source block → transit → destination block**

**Implementation:**
- The simulation engine runs a loop until entity movement is detected
- Movement is detected by: entity location change OR processed entity count increase
- Maximum 1000 sub-steps per step to prevent infinite loops

**Example of Correct Step Behavior:**
```
Step N:   Entity executes multiple actions in 투입 block (delay, signal updates) 
Step N+1: Entity executes `go to 공정1.L` → moves 투입→공정1, arrives at 공정1
Step N+2: Entity executes actions in 공정1, then `go to 배출.L` → moves 공정1→배출
```

**Key Difference from Previous Behavior:**
- **Before**: Every action caused a separate step (delay, signal_update, go to each triggered steps)
- **After**: Only `go to` actions (entity movements) trigger step completion

### Data Transformation Pipeline
```
Frontend (Vue reactive data) → API calls → ID conversion → Pydantic validation → 
Cached SimPy environment → High-speed simulation execution → Results → Frontend update
```

## Critical Technical Considerations

### Performance vs. Debugging Trade-off
- **Production**: `DEBUG_MODE = False` for maximum performance (22,000+ steps/sec)
- **Development**: `DEBUG_MODE = True` for detailed logging (~1,000 steps/sec)

### Entity Visibility System
- **Transit State**: Entities in "transit" are displayed on connection lines
- **Color Coding**: Orange (in blocks), Purple (transit), Red (error states)
- **Real-time Tracking**: All entity movements are continuously tracked

### Memory Management
- **Entity Pooling**: Objects are reused to prevent memory leaks
- **State Caching**: Intelligent caching with automatic invalidation
- **Resource Cleanup**: Proper cleanup on simulation reset

## Development Workflow Patterns

### Performance-First Development
1. **Always test performance impact** of changes using `test_performance_and_ui.py`
2. **Use DEBUG_MODE appropriately** - False for production, True only when debugging
3. **Verify entity visibility** using `test_reset_and_transit.py`
4. **Check cache behavior** after modifications to core simulation logic

### Backend Module Development
1. **Simulation Performance**: Modify `app/simulation_engine_v2.py` with performance in mind
2. **Entity Management**: Use `app/entity.py` for entity lifecycle changes
3. **State Management**: Update `app/state_manager.py` for global state modifications
4. **API Changes**: Update `app/routes/simulation.py` for endpoint modifications

### Frontend Component Development
1. **Entity Visualization**: Modify `components/CanvasArea.vue` for display changes
2. **Transit Entities**: Use existing `displayTransitEntity` function for transit states
3. **Performance Monitoring**: Ensure UI updates don't impact simulation performance

## Signal Management System

### Global Signals
- **Real-time Updates**: Global signals are automatically updated during simulation execution
- **Signal Types**: Boolean signals (true/false) with initial and current values
- **UI Integration**: Global Signal Panel shows live signal states during simulation
- **Auto-discovery**: New signals created during simulation are automatically added to the panel

### Signal Integration Points
```javascript
// Frontend: Signal updates happen in App.vue after each step
if (result.current_signals) {
  updateSignalsFromSimulation(result.current_signals)
}
```

```python
# Backend: Signals included in simulation results
class SimulationStepResult(BaseModel):
    current_signals: Optional[Dict[str, bool]] = None  # Real-time signal states
```

## Script Syntax for Actions

### Basic Commands
```
delay 5                    # 5 second delay
신호명 = true              # Set signal value
if 신호명 = true           # Check signal value (indent sub-actions with tab)
wait 신호명 = true         # Wait until signal becomes true
go to self.커넥터명        # Move to connector in current block
go to 블록명.커넥터명      # Move to connector in another block
go to 블록명.커넥터명,3    # Move with 3 second delay
jump to 1                  # Jump to line 1 (auto 0.1s delay)
// 주석                    # Comment
```

### Conditional Execution Example
```
if 공정1 load enable = true
    공정1 load enable = false
    go to 공정1.L,3
if 공정2 load enable = true
    공정2 load enable = false
    go to 공정2.L,3
if 공정1 load enable = false
    delay 0.1
    jump to 1
```

### Script Editor Features
- **Tab Key Support**: Tab for indent, Shift+Tab for outdent
- **Auto-Indentation**: Enter key preserves current line's indentation
- **Multi-line Selection**: Tab/Shift+Tab works on selected lines
- **Syntax Preservation**: Tab size set to 4 spaces visually

## Auto Connection System

### Automatic Connection Creation
- **Action Analysis**: Analyzes `route_to_connector` actions and `go to` commands in scripts
- **Real-time Generation**: Creates connections immediately when actions are saved
- **Script Pattern Recognition**: Regex pattern `/go\s+to\s+([^.\s]+)\.([^,\s]+)/gi`
- **Duplicate Prevention**: Checks for existing connections before creating new ones
- **Manual Refresh**: "🔗 자동 연결 새로고침" button in Control Panel

### Connection Types
- **Manual Connections**: User-created connections (preserved during refresh)
- **Auto Connections**: Generated from actions (marked with `auto_generated` flag)
- **Conditional Connections**: From conditional branch scripts (marked with `from_conditional_script`)

### Implementation Functions
```javascript
// useBlocks.js
extractConnectionsFromActions()    // Extract connections from block/connector actions
extractConnectionsFromScript()     // Parse "go to" commands from scripts  
createAutoConnections()           // Create connections for block actions
createAutoConnectionsFromConnector() // Create connections for connector actions
refreshAllAutoConnections()       // Refresh all auto-generated connections
```

## Entity Visualization System

### Transit Entity Display
- **Enhanced Visibility**: Entities are visible during all transition phases
- **Color Coding**: Orange (in blocks), Purple (transit state), Red (error states)
- **Intelligent Routing**: Transit entities display on correct connection lines based on movement path
- **Format**: Backend sets transit names as "블록1→블록2" format for UI parsing

### Entity State Flow
```
Block Entry → Block Processing → Transit State → Target Block Entry
     ↓              ↓                ↓               ↓
   Orange         Orange           Purple          Orange
```

## Composition API Architecture

### Key Composables
- `useSimulation()` - Core simulation state and execution logic
- `useBlocks()` - Block and connection management
- `useSignals()` - Global signal management with real-time updates
- `usePerformanceMonitor()` - Performance tracking and metrics

### State Management Pattern
```javascript
// Reactive state management with computed properties
const { dispatchedProductsFromSim, processTimeFromSim, currentStepCount } = useSimulation()
const { globalSignals, updateSignalsFromSimulation } = useSignals()
```

## Recent Major Improvements (Latest)

### Complete Engine Refactoring (2025-06-03)
- **Modular Architecture**: Engine split into 7+ specialized modules in `app/core/`
- **Dynamic Simulation**: Removed all hardcoded values (블록명, 신호명)
- **Flexible Configuration**: Any block/signal names work without code changes
- **Clean Separation**: Each concern (entity, signal, pipe, source) has dedicated manager
- **Maintainable**: AI-friendly code structure for easier future modifications
- **Source Block Management**: Fixed entity creation timing and request event handling
- **Action Execution**: Enhanced to continue actions after entity routing for signal management
- **Reset Functionality**: Improved reset mechanism with proper state cleanup across all managers
- **Step Execution Fix**: Steps now complete only on entity movement (`go to` actions), not every action

### Frontend Improvements (2025-06-03)
- **ID Type Safety**: Fixed block/connector selection issues with numeric IDs by using String() conversions
- **Script Editor Enhancement**: Added Tab key support for indentation in script editors
- **Auto Connection Creation**: Automatic connection line generation from `go to` actions
- **Connection Refresh**: Manual refresh button to analyze all actions and create missing connections
- **Complex Wait Support**: Script parser now handles `wait condition1 or condition2` syntax
- **Conditional Script Preservation**: Multi-line conditional scripts are preserved when editing

### Logging System Improvements (2025-06-03)
- **Simulation Reset Log Clear**: Log file is reset when simulation is reset
- **Improved Error Messages**: Better routing error messages with available routes displayed
- **Source Block Entity Generation**: Fixed to generate entities continuously at appropriate intervals
- **Complex Wait Support**: Script executor now handles `wait condition1 or condition2` syntax with OR logic

### Multi-Connection Support (2025-06-03)
- **Multiple Connections per Connector**: PipeManager now supports multiple connections from a single connector
- **List-based Connection Storage**: Changed from single connection to list of connections per connector
- **Backward Compatibility**: Action executor handles both old (single) and new (list) formats
- **Script Executor Enhancement**: Supports routing to any of multiple connected destinations
- **Entity Generation Timing**: Added small timeout after entity generation to create step boundaries

### Performance Optimization (100x Improvement)
- **Before**: ~100-200 steps/second
- **After**: 22,000+ steps/second
- **Techniques**: Conditional logging, caching, timeout optimization

### Real-time Signal Management
- **Problem Solved**: Global signals now update in real-time during simulation
- **Integration**: Automatic signal state synchronization between backend and frontend
- **UI Enhancement**: Live signal value display in Global Signal Panel

### Enhanced Entity Visibility
- **Transit Intelligence**: Entities display on correct connection lines during movement
- **Path Recognition**: Backend provides dynamic transit format for accurate UI positioning
- **Fallback Logic**: Robust handling when connection paths cannot be determined

### Quantity-based Execution Control
- **Auto-stop**: Simulations automatically stop when target quantity is reached
- **Progress Tracking**: Real-time monitoring of processed entity count vs target
- **Mode Support**: Quantity-based and time-based execution modes

### Parallel Processing Support (2025-06-03)
- **Multi-Input Pipe Handling**: Blocks can now properly receive entities from multiple input pipes
- **Transit State in Conditional Branches**: Entities show proper transit state when routed via conditional_branch actions
- **Signal-Based Flow Control**: Proper synchronization for parallel processing with signal-based entity flow control
- **Fair Pipe Selection**: Blocks check all input pipes for available entities, not just the first pipe

## Git-based Automated Development Workflow

### Automated Git Management Scripts
The project includes a comprehensive set of automation scripts for streamlined development:

```bash
# Git repository setup and initialization
./scripts/setup-git.sh [repository-url]     # One-time setup with .gitignore, initial commit

# Development workflow automation  
./scripts/dev-start.sh                      # Auto-start with Git sync, dependency check
./scripts/dev-stop.sh                       # Clean server shutdown

# Automated version control
./scripts/auto-commit.sh [commit-message]   # Intelligent auto-commit with change analysis
./scripts/auto-deploy.sh [interval]         # Continuous file watching and auto-deployment

# Production deployment
./scripts/build.sh                          # Performance-tested production build with Docker
```

### Smart Git Integration Features

**Auto-Setup (`setup-git.sh`)**:
- Automatic .gitignore generation for Node.js/Python/IDE files
- Git user configuration validation
- Remote repository setup with initial commit
- Conventional commit message formatting

**Development Server (`dev-start.sh`)**:
- Pre-start Git status checking and uncommitted changes handling
- Automatic remote synchronization (fetch/pull)
- Dependency validation for both frontend and backend
- Process management with PID tracking

**Intelligent Auto-Commit (`auto-commit.sh`)**:
- Change analysis with file type categorization (frontend/backend/config)
- Conventional commit format: `type(scope): description [+added ~modified -deleted]`
- Git hook integration ready
- Remote push with conflict detection

**Production Build (`build.sh`)**:
- Performance test validation before build
- Automated Docker containerization
- Git tagging with build metadata
- Deployment package generation with documentation

### Development Workflow Patterns

**Daily Development**:
```bash
# Morning startup - auto-handles git sync and dependencies
./scripts/dev-start.sh

# During development - commit when needed
./scripts/auto-commit.sh "feat(frontend): add signal visualization"

# End of day - auto-commit all changes
./scripts/auto-commit.sh

# Continuous watching (optional)
./scripts/auto-deploy.sh 30  # Check every 30 seconds
```

**Release Workflow**:
```bash
# Performance validation and production build
./scripts/build.sh

# Automated Docker deployment package created
# Git tag automatically generated with build metadata
```

## Important Development Rules

### 1. Testing Methodology Rules
- **NEVER** perform internal testing - user will test and provide logs
- **ALWAYS** wait for user to provide test results and logs
- **ANALYZE** logs carefully to identify issues
- **UPDATE** code based on log analysis only

### 2. Debug Mode Rules
- **ALWAYS** set `DEBUG_MODE = False` before finishing any task
- **ALWAYS** set `PERFORMANCE_MODE = True` for production
- Location: `app/core/constants.py`

### 3. Modular Engine Rules (v2)
When modifying the simulation engine:
- **Use appropriate managers** for each concern:
  - `EntityManager`: Entity lifecycle operations
  - `SignalManager`: Signal handling
  - `PipeManager`: Connections and routing
  - `SourceManager`: Source block management
  - `ActionExecutor`: Action execution
  - `BlockProcessor`: Block process orchestration
- **Never hardcode** block names, signal names, or any configuration
- **Always test** with dynamic configurations
- **Maintain separation** of concerns between modules

### 4. Code Modification Rules
- Follow the existing modular structure in `app/core/`
- Add new action types to `ActionType` class in `constants.py`
- Keep all hardcoded values in `constants.py`
- Import DEBUG_MODE in all new core modules to prevent NameError
- Document any new modules or significant changes
- Always call `.reset()` on new managers in simulation engine reset method

## Common Troubleshooting Patterns

### Source Block Not Creating Entities
**Symptoms**: 
- Event queue only shows 2 timeout events (no source block process)
- No entities being created
- Time advances by 0.1s increments
- Only first entity created, no subsequent entities

**Common Causes**:
1. Source block not properly registered in `source_manager`
2. Source block process not added to SimPy environment
3. Request event not triggered for source blocks
4. Entity creation blocked by capacity constraints
5. Source block waiting for signal conditions that never become true

**Solutions**:
- Verify source block registration in `setup_simulation`
- Check that block processes are created for all blocks
- Ensure `trigger_initial_events` is called
- Verify block capacity settings
- Check signal states for source block generation conditions
- Source blocks now generate entities when block is empty (after first entity leaves)

### Entity Actions Not Executing
**Symptoms**:
- Entities created but not moving to next block
- Actions list not being processed
- Entities accumulating in source block

**Common Causes**:
1. Error in action execution preventing completion
2. Missing or incorrect routing parameters
3. Signal conditions not being met
4. Self-routing issues (block routing to its own connector)

**Solutions**:
- Check error logs for action execution failures
- Verify route_to_connector parameters
- Check signal states match expected conditions
- Handle self-connector routing specially

### Performance Debugging
**When simulation runs slowly**:
1. Check `DEBUG_MODE` setting in `constants.py`
2. Verify `PERFORMANCE_MODE` is True
3. Check for excessive logging in hot paths
4. Monitor entity count and queue sizes

### Cache-Related Issues
**Symptoms**:
- Configuration changes not taking effect
- Old simulation state persisting

**Solutions**:
- Force reset by setting `setup` parameter differently
- Clear `_cached_setup` in simulation engine
- Use reset endpoint to clear all state

## Entity Lifecycle and Common Issues

### Entity Flow Debugging
Entities follow this lifecycle:
1. **Creation**: Generated in source blocks when conditions are met
2. **Processing**: Actions executed in current block
3. **Transit**: Movement between blocks (visible on UI)
4. **Arrival**: Entity reaches destination block
5. **Disposal**: Entity exits system at sink blocks

**Common Breakpoints**:
- **Between Creation and Processing**: Check if actions are being executed
- **Between Processing and Transit**: Verify routing logic
- **During Transit**: Check pipe availability and capacity
- **At Arrival**: Verify destination block capacity
- **Parallel Routes**: Check if multiple entities are trying to enter capacity-limited blocks

### SimPy Event Queue Patterns
**Healthy Queue**:
- Multiple block processes scheduled
- Mix of entity events and timeout events
- Regular time progression

**Problem Queue**:
- Only 2 events (usually timeout events)
- No source block processes
- Time stuck at same value or incrementing by timeout values

### Action Execution Debugging
When actions fail to execute:
1. Check for `Entity has no attribute 'env'` errors - fixed in recent updates with hasattr() checks
2. Verify action parameters are correctly formatted
3. Ensure signal names exist and match exactly
4. Check for self-routing logic (block→self.connector)
5. Verify connector names match between script and configuration
6. Ensure remaining actions execute after entity routing via `_execute_remaining_actions`
7. Check DEBUG_MODE import in all core modules (common NameError source)

### Frontend ID Type Issues
**Symptoms**:
- Blocks not clickable when loaded from JSON files with numeric IDs
- Connector selection not working properly
- Block settings popup not opening

**Solutions**:
- All ID comparisons use `String()` conversion for type safety
- Functions like `findBlockById` use `String(block.id) === String(id)`
- Both numeric and string IDs work seamlessly

### Script Editor Tab Key Issues
**Symptoms**:
- Tab key moves focus instead of inserting indentation
- Cannot indent code blocks in script editors

**Solutions**:
- `@keydown="onKeyDown"` handler added to textareas
- `event.preventDefault()` stops default tab behavior
- Tab key now inserts tab character or indents selected lines

### Sink Block Processing Issues
**Symptoms**:
- Entities stuck in transit state (e.g., "공정2→배출")
- Sink blocks not processing entities despite having custom_sink action
- Multiple entities accumulating in transit to sink block

**Common Causes**:
1. Missing `block_entry` action in sink block connector
2. Sink block capacity constraints (maxCapacity=1)
3. Block process not properly retrieving entities from pipe
4. Parallel processing: multiple blocks sending entities to single sink block

**Solutions**:
- Ensure sink block connectors have proper actions (or handle empty actions)
- Check sink block capacity settings
- Verify block process continues after processing entities
- Monitor pipe states and entity locations
- For parallel processing: implement signal-based flow control to prevent simultaneous arrivals

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.