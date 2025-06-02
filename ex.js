document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('canvas');
    const addUnitBtn = document.getElementById('add-unit-btn');
    const resetBtn = document.getElementById('reset-btn');
    const stepRunBtn = document.getElementById('step-run-btn');
    const runAllBtn = document.getElementById('run-all-btn');
    const targetStepInput = document.getElementById('target-step-input');
    const runToStepBtn = document.getElementById('run-to-step-btn');
    const currentStepDisplay = document.getElementById('current-step-display');
    const targetTimeInput = document.getElementById('target-time-input');
    const runToTimeBtn = document.getElementById('run-to-time-btn');
    const currentTimeDisplay = document.getElementById('current-time-display');
    const totalSimulationTimeDisplay = document.getElementById('total-simulation-time');
    const avgProductTimeDisplay = document.getElementById('avg-product-time');
    const totalDischargedProductsDisplay = document.getElementById('total-discharged-products');

    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');

    const sidePanel = document.getElementById('side-panel');
    const panelTitle = document.getElementById('panel-title');
    const deleteUnitBtn = document.getElementById('delete-unit-btn');
    const minimizePanelBtn = document.getElementById('minimize-panel-btn');
    const maximizePanelBtn = document.getElementById('maximize-panel-btn');
    const inputUnitConfigDiv = document.getElementById('input-unit-config');
    const generalUnitConfigDiv = document.getElementById('general-unit-config');
    const outputUnitConfigDiv = document.getElementById('output-unit-config');
    const dischargeIntervalInput = document.getElementById('discharge-interval');
    const inputTimeInput = document.getElementById('input-time');
    const totalQuantityInput = document.getElementById('total-quantity');
    const nextUnitWrapper = document.getElementById('next-unit-wrapper');
    const maxCapacityInput = document.getElementById('max-capacity');
    const addActionBtn = document.getElementById('add-action-btn');
    const unitConfigTableBody = document.getElementById('unit-config-table').querySelector('tbody');

    const addUnitModal = document.getElementById('add-unit-modal');
    const newUnitNameInput = document.getElementById('new-unit-name-input');
    const confirmAddUnitBtn = document.getElementById('confirm-add-unit-btn');
    const cancelAddUnitBtn = document.getElementById('cancel-add-unit-btn');

    const actionEditModal = document.getElementById('condition-edit-modal');
    const actionNameEditInput = document.getElementById('action-name-edit-input');
    const commandListUl = document.getElementById('command-list');
    const commandTypeSelect = document.getElementById('command-type-select');
    const addCommandToListBtn = document.getElementById('add-command-to-list-btn');
    const setSignalParamsDiv = document.getElementById('set-signal-params');
    const delayParamsDiv = document.getElementById('delay-params');
    const saveActionBtn = document.getElementById('save-action-btn');
    const cancelActionBtn = document.getElementById('cancel-action-btn');

    const svgLayer = document.getElementById('connection-svg-layer');
    const SVG_NS = "http://www.w3.org/2000/svg";

    let units = [];
    let unitIdCounter = 0;
    let commandIdCounter = 0;
    let actionGroupIdCounter = 0;
    let currentStep = 0; // 내부 마이크로 스텝 또는 전체 시뮬레이션 시간과 동기화
    let manualStepCount = 0; // 사용자가 스텝 실행 버튼을 누른 횟수
    let currentTime = 0;
    let selectedUnitElement = null;
    let editingActionGroup = null;
    let tempCommands = [];
    let nextProductId = 1;
    let totalDischargedCount = 0;
    let editingCommandIndex = -1; // 현재 수정 중인 명령어의 인덱스 (-1이면 수정 중 아님)
    let isEditingCommand = false; // 현재 명령어를 수정 중인지 여부
    let simulationRunning = false;
    let lastInputTime = -Infinity; 
    let simulationStepPromiseResolve = null;
    let stopFullSimulationRequested = false; // 전체 실행 중지 요청 플래그

    let unitBaseSize = { width: 150, height: 100, fontSize: 16 }; // 유닛 기본 높이 증가, 너비도 약간 증가
    let unitScale = 1;

    function log(level, message) { console.log(`[${level.toUpperCase()}] ${message}`); }

    function initialize() {
        log('info', "시뮬레이션 초기화 시작");
        simulationRunning = false;
        if (runAllBtn) runAllBtn.textContent = "전체 실행";

        clearCanvas();
        clearAllConnectionLines();
        addInitialUnits(); 
        nextProductId = 1;
        totalDischargedCount = 0;
        lastInputTime = -Infinity; 
        currentStep = 0; // 내부 스텝 카운터 초기화
        manualStepCount = 0; // 수동 스텝 카운터 초기화
        currentTime = 0;
        
        updateDisplays();
        closeSidePanel(); 
        updateAllConnectionLines();
        log('info', "시뮬레이션 초기화 완료");
    }
    
    function clearCanvas() {
        log('debug', "캔버스 클리어");
        canvas.innerHTML = ''; units = []; unitIdCounter = 0; commandIdCounter = 0; actionGroupIdCounter = 0;
        if (selectedUnitElement) closeSidePanel();
    }

    function addInitialUnits() {
        log('info', "초기 유닛 배치 시작");
        const cC=canvas.parentElement; const cX=cC.scrollLeft+cC.clientWidth/2; const cY=cC.scrollTop+cC.clientHeight/2;
        const uW=unitBaseSize.width*unitScale; const uH=unitBaseSize.height*unitScale; const gap=50;
        const tW=(uW*4)+(gap*3); const sX=cX-(tW/2); const yP=cY-(uH/2);

        const iUE=createUnitElement('투입','input',sX,yP); 
        const u1E=createUnitElement('유닛1','normal',sX+uW+gap,yP);
        const u2E=createUnitElement('유닛2','normal',sX+(uW+gap)*2,yP); 
        const oUE=createUnitElement('배출<br> ', 'output', sX+(uW+gap)*3, yP);
        
        const iUD=getUnitDataById(iUE.dataset.id); const u1D=getUnitDataById(u1E.dataset.id);
        const u2D=getUnitDataById(u2E.dataset.id); const oUD=getUnitDataById(oUE.dataset.id);

        if(iUD){iUD.config.inputTime=1;iUD.config.totalQuantity=100;if(u1D)iUD.config.nextUnitId=u1D.id;}
        if(u1D){u1D.config.maxCapacity=1;if(u2D)u1D.config.nextUnitId=u2D.id; 
            u1D.config.actions=[{id:`ag_${actionGroupIdCounter++}`,name:"투입 준비 (U1)",commands:[{id:`cmd_${commandIdCounter++}`,type:"SET_SIGNAL",signal:"유닛1_load_enable",value:true}]}, {id:`ag_${actionGroupIdCounter++}`,name:"투입 진행 (U1)",commands:[{id:`cmd_${commandIdCounter++}`,type:"SET_SIGNAL",signal:"유닛1_load_enable",value:false},{id:`cmd_${commandIdCounter++}`,type:"DELAY",duration:5,affects_previous:true,description:"U1 제품 이동"}]}, {id:`ag_${actionGroupIdCounter++}`,name:"공정 진행 (U1)",commands:[{id:`cmd_${commandIdCounter++}`,type:"DELAY",duration:10,description:"U1 내부 공정"}]}, {id:`ag_${actionGroupIdCounter++}`,name:"배출 준비 (U1)",commands:[{id:`cmd_${commandIdCounter++}`,type:"SET_SIGNAL",signal:"유닛1_배출준비",value:true}]}, {id:`ag_${actionGroupIdCounter++}`,name:"배출 진행 (U1)",commands:[{id:`cmd_${commandIdCounter++}`,type:"SET_SIGNAL",signal:"유닛1_배출준비",value:false}]}];
        }
        if(u2D){u2D.config.maxCapacity=1;if(oUD)u2D.config.nextUnitId=oUD.id;
            u2D.config.actions=[{id:`ag_${actionGroupIdCounter++}`,name:"투입 준비 (U2)",commands:[{id:`cmd_${commandIdCounter++}`,type:"SET_SIGNAL",signal:"유닛2_load_enable",value:true}]}, {id:`ag_${actionGroupIdCounter++}`,name:"투입 진행 (U2)",commands:[{id:`cmd_${commandIdCounter++}`,type:"SET_SIGNAL",signal:"유닛2_load_enable",value:false},{id:`cmd_${commandIdCounter++}`,type:"DELAY",duration:5,affects_previous:true,description:"U2 제품 이동"}]}, {id:`ag_${actionGroupIdCounter++}`,name:"공정 진행 (U2)",commands:[{id:`cmd_${commandIdCounter++}`,type:"DELAY",duration:15,description:"U2 내부 공정"}]}, {id:`ag_${actionGroupIdCounter++}`,name:"배출 준비 (U2)",commands:[{id:`cmd_${commandIdCounter++}`,type:"SET_SIGNAL",signal:"유닛2_배출준비",value:true}]}, {id:`ag_${actionGroupIdCounter++}`,name:"배출 진행 (U2)",commands:[{id:`cmd_${commandIdCounter++}`,type:"SET_SIGNAL",signal:"유닛2_배출준비",value:false}]}];
        }
        if(oUD)oUD.config.dischargeInterval=0; 
        
        units.forEach(unit=>{ 
            unit.products = unit.products || []; 
            unit.currentActionIndex=0; unit.currentCommandIndex=0; unit.status='IDLE'; unit.delayEndTime=0; unit.signals={}; unit.lastDischargeTime=-Infinity;
            if(unit.config.actions&&unit.config.actions.length>0){ const fAG=unit.config.actions[0]; if(fAG&&fAG.commands){fAG.commands.forEach(cmd=>{if(cmd.type==="SET_SIGNAL"&&cmd.signal){log('debug',`초기설정: ${unit.name.replace(/<br> /g, '')} - 신호 '${cmd.signal}'=${cmd.value}`); unit.signals[cmd.signal]=cmd.value;}});}}
            updateUnitDisplay(unit);
        });
        log('info', "초기 유닛 배치 완료");
    }
    
    function updateUnitSize(unitElement, scale) {
        log('debug', `updateUnitSize 호출: 유닛 ${unitElement.dataset.id}, scale=${scale}`);
        unitElement.style.width = `${unitBaseSize.width * scale}px`;
        unitElement.style.height = `${unitBaseSize.height * scale}px`;
        const nameSpan = unitElement.querySelector('.unit-name');
        if(nameSpan) nameSpan.style.fontSize = `${unitBaseSize.fontSize * scale * 0.9}px`; // 이름 폰트 크기 약간 작게
        const unitInfo = unitElement.querySelector('.unit-info');
        if (unitInfo) unitInfo.style.fontSize = `${unitBaseSize.fontSize * 0.8 * scale}px`;
        const productsDisplay = unitElement.querySelector('.unit-products-display');
        if(productsDisplay) productsDisplay.style.fontSize = `${unitBaseSize.fontSize * 0.7 * scale}px`;
    }
    
    function applyZoomToAllUnits() {
        log('info', `전체 유닛 크기 변경 적용: unitScale=${unitScale}`);
        units.forEach(unit => updateUnitSize(unit.element, unitScale));
        updateAllConnectionLines();
    }

    function getUnitDataById(id) { return units.find(u => u.id === parseInt(id)); }

    function makeDraggable(element) {
        let pos1=0,pos2=0,pos3=0,pos4=0; element.onmousedown=dMD;
        function dMD(e){if(e.target.closest('.delete-row-btn')||e.target.closest('input')||e.target.closest('select')||e.target.closest('textarea')||e.target.closest('.unit-products-display'))return; e.preventDefault();p3=e.clientX;p4=e.clientY;document.onmouseup=cDE;document.onmousemove=eD;element.style.cursor='grabbing';}
        function eD(e){e.preventDefault();p1=p3-e.clientX;p2=p4-e.clientY;p3=e.clientX;p4=e.clientY;let nT=element.offsetTop-p2;let nL=element.offsetLeft-p1; nL=Math.max(0,Math.min(nL,canvas.scrollWidth-element.offsetWidth));nT=Math.max(0,Math.min(nT,canvas.scrollHeight-element.offsetHeight));element.style.top=nT+"px";element.style.left=nL+"px";const uD=getUnitDataById(element.dataset.id);if(uD){uD.x=nL;uD.y=nT;updateAllConnectionLines();}}
        function cDE(){document.onmouseup=null;document.onmousemove=null;element.style.cursor='grab';}
    }

    function createUnitElement(name, type = 'normal', x = 100, y = 100) {
        log('debug', `유닛 생성: ${name} (타입: ${type}) at (${x},${y})`);
        const unitId = unitIdCounter++; const unitElement = document.createElement('div');
        unitElement.classList.add('unit', `unit-${type}`); unitElement.dataset.id = unitId;
        unitElement.style.left = `${x}px`; unitElement.style.top = `${y}px`;
        const nameSpan = document.createElement('span'); nameSpan.classList.add('unit-name'); 
        nameSpan.innerHTML = name;
        unitElement.appendChild(nameSpan);
        const infoDiv = document.createElement('div'); infoDiv.classList.add('unit-info'); unitElement.appendChild(infoDiv);
        const productsDisplayDiv = document.createElement('div'); productsDisplayDiv.classList.add('unit-products-display'); unitElement.appendChild(productsDisplayDiv);
        
        makeDraggable(unitElement); // DOM에 추가하기 전에 호출해도 괜찮지만, 보통은 추가 후에. 여기서는 무방.
        unitElement.addEventListener('click', (e) => { 
            if (e.target.closest('.delete-row-btn')) return;
            openSidePanel(unitElement); 
        });
        canvas.appendChild(unitElement);
        updateUnitSize(unitElement, unitScale); // DOM 추가 후 크기 최종 적용

        const unitData = { 
            id: unitId, name: name.replace(/<br> /g, ''), type: type, element: unitElement, 
            config: { inputTime:(type==='input'?1:undefined), totalQuantity:(type==='input'?100:undefined), nextUnitId: null, maxCapacity:(type==='normal'?1:(type==='input'||type==='output'?Infinity:10)), actions:[], dischargeInterval:(type==='output'?0:undefined)},
            x:x, y:y,
            products: []
        };
        units.push(unitData);
        return unitElement;
    }

    function updateUnitDisplay(unitData) {
        if (!unitData || !unitData.element) return; // 방어 코드
        const infoDiv = unitData.element.querySelector('.unit-info');
        if (infoDiv) {
            let iT = '';
            if(unitData.type==='input')iT=`시간:${unitData.config.inputTime||0}s<br>수량:${unitData.config.totalQuantity===undefined?'∞':unitData.config.totalQuantity}`;
            else if(unitData.type==='normal')iT=`최대:${unitData.config.maxCapacity||0}개`;
            else if(unitData.type==='output')iT=`배출간격:${unitData.config.dischargeInterval||0}s`;
            infoDiv.innerHTML = iT;
        }
        const pDD = unitData.element.querySelector('.unit-products-display');
        if (pDD) {
            pDD.innerHTML = ''; // 기존 제품 표시 초기화
            if (unitData.products && unitData.products.length > 0) {
                unitData.products.forEach(product => {
                    const productDiv = document.createElement('div');
                    productDiv.classList.add('product-item');
                    productDiv.textContent = `P${product.id}`;
                    // TODO: 제품 위치 및 애니메이션 추가
                    pDD.appendChild(productDiv);
                });
            } else {
                pDD.textContent = '제품: 없음';
            }
        }
    }
    
    function openSidePanel(unitElement) {
        if (!unitElement) { log('warn', 'openSidePanel 호출 시 unitElement가 없습니다.'); return; }
        selectedUnitElement = unitElement; 
        const unitData = getUnitDataById(selectedUnitElement.dataset.id); 
        if (!unitData) { log('warn', `openSidePanel: 유닛 ID ${selectedUnitElement.dataset.id}에 대한 데이터를 찾을 수 없습니다.`); return; }
        
        log('info', `사이드 패널 열기: ${unitData.name}`);
        panelTitle.textContent = `${unitData.name} 설정`; 
        sidePanel.classList.add('active'); sidePanel.classList.remove('minimized');
        minimizePanelBtn.classList.remove('hidden'); maximizePanelBtn.classList.add('hidden');
        
        inputUnitConfigDiv.classList.add('hidden'); generalUnitConfigDiv.classList.add('hidden'); outputUnitConfigDiv.classList.add('hidden');
        if (nextUnitWrapper) nextUnitWrapper.classList.add('hidden');
        if (deleteUnitBtn) deleteUnitBtn.classList.add('hidden');

        if (unitData.type === 'input') {
            inputUnitConfigDiv.classList.remove('hidden'); 
            if (nextUnitWrapper) nextUnitWrapper.classList.remove('hidden');
            inputTimeInput.value = unitData.config.inputTime || 1; 
            totalQuantityInput.value = unitData.config.totalQuantity === undefined ? '' : unitData.config.totalQuantity;
            populateNextUnitSelect(unitData);
        } else if (unitData.type === 'normal') {
            generalUnitConfigDiv.classList.remove('hidden'); 
            if (nextUnitWrapper) nextUnitWrapper.classList.remove('hidden');
            if (deleteUnitBtn) deleteUnitBtn.classList.remove('hidden');
            maxCapacityInput.value = unitData.config.maxCapacity || 1; 
            renderActionsTable(unitData.config.actions); 
            populateNextUnitSelect(unitData);
        } else if (unitData.type === 'output') {
            outputUnitConfigDiv.classList.remove('hidden'); 
            dischargeIntervalInput.value = unitData.config.dischargeInterval || 0;
        }
    }

    if (deleteUnitBtn) deleteUnitBtn.addEventListener('click', () => { /* 이전과 동일 */ });
    function populateNextUnitSelect(currentUnitData) { /* 이전과 동일 */ }
    if(dischargeIntervalInput) dischargeIntervalInput.addEventListener('change', () => { /* 이전과 동일 */ });
    function closeSidePanel() { /* 이전과 동일 */ }
    minimizePanelBtn.addEventListener('click', () => { /* 이전과 동일 */ });
    maximizePanelBtn.addEventListener('click', () => { /* 이전과 동일 */ });
    inputTimeInput.addEventListener('change', () => { /* 이전과 동일 */ });
    totalQuantityInput.addEventListener('change', () => { /* 이전과 동일 */ });
    maxCapacityInput.addEventListener('change', () => { /* 이전과 동일 */ });
    function renderActionsTable(actionGroupsArray) { /* 이전과 동일 */ }
    function addActionGroupRowToTable(actionGroup, rowNum) { /* 이전과 동일 */ }
    if (addActionBtn) addActionBtn.addEventListener('click', () => { /* 이전과 동일 */ });
    function openActionEditModal(aGD,iN=false){
        editingActionGroup=aGD;
        tempCommands=aGD.commands?JSON.parse(JSON.stringify(aGD.commands)):[];
        actionNameEditInput.value=aGD.name||'';
        renderCommandList();
        actionEditModal.classList.remove('hidden');
        
        isEditingCommand = false;
        editingCommandIndex = -1;
        addCommandToListBtn.textContent = '명령어 목록에 추가';
        commandTypeSelect.value="";
        hideAllCommandParams();

        actionEditModal.dataset.isNew=iN;
    }
    function closeActionEditModal(){
        actionEditModal.classList.add('hidden');
        editingActionGroup=null;
        tempCommands=[];
        isEditingCommand = false;
        editingCommandIndex = -1;
        addCommandToListBtn.textContent = '명령어 목록에 추가';
        commandTypeSelect.value="";
        hideAllCommandParams();
    }
    function hideAllCommandParams(){setSignalParamsDiv.classList.add('hidden');delayParamsDiv.classList.add('hidden');}
    commandTypeSelect.addEventListener('change',()=>{hideAllCommandParams();const sT=commandTypeSelect.value;if(sT==='SET_SIGNAL')setSignalParamsDiv.classList.remove('hidden');else if(sT==='DELAY')delayParamsDiv.classList.remove('hidden');});
    function renderCommandList(){
        commandListUl.innerHTML='';
        tempCommands.forEach((cmd,i)=>{
            const li=document.createElement('li');
            let dT=`${i+1}. [${cmd.type}] `;
            if(cmd.type==='SET_SIGNAL')dT+=`신호 '${cmd.signal}'=${cmd.value?'ON':'OFF'}`;
            else if(cmd.type==='DELAY'){dT+=`딜레이 ${cmd.duration}s`+(cmd.description?` (${cmd.description})`:'');if(cmd.affects_previous)dT+=" (전단 영향)";}
            
            const tS=document.createElement('span');
            tS.textContent=dT;
            li.appendChild(tS);

            const editBtn = document.createElement('button');
            editBtn.textContent = '수정';
            editBtn.classList.add('edit-command-btn');
            editBtn.onclick = () => {
                isEditingCommand = true;
                editingCommandIndex = i;
                commandTypeSelect.value = cmd.type;
                commandTypeSelect.dispatchEvent(new Event('change')); 

                if (cmd.type === 'SET_SIGNAL') {
                    setSignalParamsDiv.querySelector('.param-signal-name').value = cmd.signal;
                    setSignalParamsDiv.querySelector('.param-signal-value').value = cmd.value.toString();
                } else if (cmd.type === 'DELAY') {
                    delayParamsDiv.querySelector('.param-delay-duration').value = cmd.duration;
                    delayParamsDiv.querySelector('.param-delay-affects-previous').checked = cmd.affects_previous;
                    delayParamsDiv.querySelector('.param-delay-description').value = cmd.description || '';
                }
                addCommandToListBtn.textContent = '명령어 수정 적용';
            };
            li.appendChild(editBtn);

            const delB=document.createElement('button');
            delB.textContent='삭제';
            delB.classList.add('delete-command-btn');
            delB.onclick=()=>{
                tempCommands.splice(i,1);
                renderCommandList();
                if (isEditingCommand && editingCommandIndex === i) {
                    isEditingCommand = false;
                    editingCommandIndex = -1;
                    addCommandToListBtn.textContent = '명령어 목록에 추가';
                    commandTypeSelect.value = "";
                    hideAllCommandParams();
                }
            };
            li.appendChild(delB);
            commandListUl.appendChild(li);
        });
    }
    if(saveActionBtn) saveActionBtn.addEventListener('click',()=>{
        if(editingActionGroup&&selectedUnitElement){
            const uD=getUnitDataById(selectedUnitElement.dataset.id);
            if(uD){
                editingActionGroup.name=actionNameEditInput.value.trim()||editingActionGroup.name||'이름없는 행동그룹';
                editingActionGroup.commands=JSON.parse(JSON.stringify(tempCommands));
                if(!uD.config.actions)uD.config.actions=[];
                const iN=actionEditModal.dataset.isNew==='true';
                const eAGI=uD.config.actions.findIndex(ag=>ag.id===editingActionGroup.id);
                if(iN&&eAGI===-1)uD.config.actions.push(editingActionGroup);
                else if(eAGI>-1)uD.config.actions[eAGI]=editingActionGroup;
                else if(iN&&eAGI>-1){editingActionGroup.id=`ag_${actionGroupIdCounter++}`;uD.config.actions.push(editingActionGroup);}
                renderActionsTable(uD.config.actions);
            }
            closeActionEditModal();
        }
    });
    if(cancelActionBtn) cancelActionBtn.addEventListener('click',()=>{closeActionEditModal();});
    addUnitBtn.addEventListener('click',()=>{newUnitNameInput.value='';addUnitModal.classList.remove('hidden');newUnitNameInput.focus();});
    confirmAddUnitBtn.addEventListener('click',()=>{const n=newUnitNameInput.value.trim();if(n){const cC=canvas.parentElement;const x=cC.scrollLeft+(cC.clientWidth/2)-(unitBaseSize.width*unitScale/2);const y=cC.scrollTop+(cC.clientHeight/2)-(unitBaseSize.height*unitScale/2);createUnitElement(n,'normal',x,y);addUnitModal.classList.add('hidden');updateAllConnectionLines();}else alert('유닛 이름을 입력하세요.');});
    cancelAddUnitBtn.addEventListener('click',()=>{addUnitModal.classList.add('hidden');});
    
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            log('debug', "리셋 버튼 클릭됨 - 이벤트 리스너에서");
            if (confirm('모든 설정을 리셋하시겠습니까?')) {
                log('info', "리셋 확인됨, initialize 호출 - 이벤트 리스너에서");
                initialize(); 
            } else {
                log('info', "리셋 취소됨 - 이벤트 리스너에서");
            }
        });
    }

    runToStepBtn.addEventListener('click',()=>{const t=parseInt(targetStepInput.value);
        // 여기서 목표 스텝(t)은 manualStepCount를 기준으로 해야 함.
        if(!isNaN(t) && t > manualStepCount){
            const stepsToRun = t - manualStepCount;
            log('info', `${t} (수동)스텝까지 실행 요청. 현재 ${manualStepCount}, ${stepsToRun}번 추가 실행 필요.`);
            // 주의: 아래 반복문은 각 반복이 비동기 runSingleStep을 완료할 때까지 기다리지 않음.
            // 만약 순차적 실행이 중요하다면 Promise 배열과 Promise.all 또는 for-await-of 루프 필요.
            // 현재는 버튼 클릭 리스너이므로, 복잡도를 낮추기 위해 단순 반복으로 처리. 사용자가 여러번 눌러야 할 수도 있음.
            async function runMultipleManualSteps(numSteps) {
                for (let i = 0; i < numSteps; i++) {
                    if (simulationRunning) {
                        log('warn','전체실행 중 지정스텝 실행시도 중단.');
                        break;
                    }
                    manualStepCount++; // 각 수동 스텝 실행 전에 카운트 증가
                    log('info', `runToStepBtn: 수동 스텝 ${manualStepCount} 실행 시작`);
                    await new Promise(resolve => {
                        simulationStepPromiseResolve = resolve;
                        runSingleStep(true); 
                    });
                    updateDisplays(); // 각 스텝 후 디스플레이 업데이트
                    log('info', `runToStepBtn: 수동 스텝 ${manualStepCount} 실행 완료`);
                    if (manualStepCount >= t) break; // 목표 도달 시 중단
                }
                alert(`${manualStepCount} (수동)스텝까지 진행 완료.`);
                units.forEach(updateUnitDisplay); // 최종 UI 업데이트
                updateAllConnectionLines();
            }
            runMultipleManualSteps(stepsToRun);

        } else if(!isNaN(t) && t <= manualStepCount) alert('목표스텝은 현재 수동 스텝보다 커야합니다.');
        else alert('유효한 스텝 숫자를 입력하세요.');
    });

    runToTimeBtn.addEventListener('click',()=>{const t=parseInt(targetTimeInput.value);if(!isNaN(t)&&t>currentTime){while(currentTime<t&&!simulationRunning)runSingleStep();updateDisplays();alert(`${t}초까지 진행 완료.`);}else if(!isNaN(t)&&t<=currentTime)alert('목표시간은 현재보다 커야함.');else alert('유효시간 입력.');});
    zoomInBtn.addEventListener('click',()=>{unitScale=Math.min(2,unitScale+0.1);applyZoomToAllUnits();});
    zoomOutBtn.addEventListener('click',()=>{unitScale=Math.max(0.5,unitScale-0.1);applyZoomToAllUnits();});
    function updateTotalDischargedDisplay(){totalDischargedProductsDisplay.textContent=`${totalDischargedCount}개`;}
    function updateDisplays(){
        currentStepDisplay.textContent = manualStepCount; // currentStep 대신 manualStepCount 사용
        currentTimeDisplay.textContent=`${currentTime}s`;
        totalSimulationTimeDisplay.textContent=`${currentTime}s`;
        updateTotalDischargedDisplay();
    }
    function clearAllConnectionLines(){const c=Array.from(svgLayer.children);c.forEach(ch=>{if(ch.tagName.toLowerCase()!=='defs')svgLayer.removeChild(ch);});}
    function drawConnectionLine(sU,eU){if(!sU||!eU||!sU.element||!eU.element)return;const l=document.createElementNS(SVG_NS,'line');const sX=sU.element.offsetLeft+sU.element.offsetWidth;const sY=sU.element.offsetTop+sU.element.offsetHeight/2;const eX=eU.element.offsetLeft;const eY=eU.element.offsetTop+eU.element.offsetHeight/2;l.setAttribute('x1',sX);l.setAttribute('y1',sY);l.setAttribute('x2',eX);l.setAttribute('y2',eY);l.setAttribute('stroke','#555');l.setAttribute('stroke-width','2');l.setAttribute('marker-end','url(#arrowhead)');svgLayer.appendChild(l);}
    function updateAllConnectionLines(){clearAllConnectionLines();units.forEach(u=>{if(u.config.nextUnitId!==null&&u.config.nextUnitId!==''){const nU=getUnitDataById(u.config.nextUnitId);if(nU)drawConnectionLine(u,nU);else{u.config.nextUnitId=null;if(selectedUnitElement&&getUnitDataById(selectedUnitElement.dataset.id)===u){const cS=document.getElementById('next-unit-select');if(nextUnitWrapper&&!nextUnitWrapper.classList.contains('hidden')&&cS)cS.value='';}}}});}

    runAllBtn.addEventListener('click', toggleFullSimulation);

    function toggleFullSimulation() {
        if (!simulationRunning) {
            log('info', "전체 시뮬레이션 시작 요청됨");
            simulationRunning = true;
            stopFullSimulationRequested = false;
            runAllBtn.textContent = "실행 중지";
            runFullSimulationLoop();
        } else {
            log('info', "전체 시뮬레이션 중지 요청됨");
            stopFullSimulationRequested = true; // 루프 내에서 이 플래그를 확인하여 중지
            // simulationRunning = false; // 루프가 스스로 종료하도록 유도
            // runAllBtn.textContent = "전체 실행"; // 루프 종료 후 변경
        }
    }

    // ★★★ 시뮬레이션 유닛 처리 함수들 (runSingleStep 보다 먼저 정의) ★★★
    function processInputUnit(unit) {
        log('debug', `${currentTime}s: [투입 ${unit.name}] 처리. 제품:${(unit.products || []).length}, 상태:${unit.status}, 마지막투입:${lastInputTime}, 다음제품ID:${nextProductId}`);
        if ((unit.products || []).length > 0) { 
            if (currentTime >= unit.delayEndTime) {
                const productToTransfer = unit.products[0]; 
                const nextUnit = getUnitDataById(unit.config.nextUnitId);
                log('debug', `${currentTime}s: [투입 ${unit.name}] 딜레이완료. 제품 ${productToTransfer.id} -> ${nextUnit?nextUnit.name.replace(/<br> /g, ''):'다음유닛없음'} 전송시도.`);
                if (nextUnit && canTransferProduct(unit, nextUnit)) {
                    if (transferProduct(productToTransfer, unit, nextUnit)) {
                        lastInputTime = currentTime; 
                        log('info', `${currentTime}s: [투입 ${unit.name}] 제품 ${productToTransfer.id} -> ${nextUnit.name.replace(/<br> /g, '')} 전송성공. 다음투입가능: ${lastInputTime + (unit.config.inputTime || 0)}s`);
                    } else log('warn', `${currentTime}s: [투입 ${unit.name}] 제품 ${productToTransfer.id} 전송실패(canTransfer 후).`);
                } else log('debug', `${currentTime}s: [투입 ${unit.name}] 제품 ${productToTransfer.id} 전송대기 (다음유닛 ${nextUnit?nextUnit.name.replace(/<br> /g, ''):'없음'} 수신불가)`);
                unit.status = 'IDLE';
            } else log('debug', `${currentTime}s: [투입 ${unit.name}] 투입딜레이중 (종료:${unit.delayEndTime})`);
            return; 
        }
        const totalQty = unit.config.totalQuantity;
        const canProduceNew = (totalQty === undefined || nextProductId <= totalQty);
        const nextUnit = getUnitDataById(unit.config.nextUnitId);
        const inputTime = unit.config.inputTime || 0;
        const inputIntervalPassed = (lastInputTime === -Infinity && inputTime >= 0) || (currentTime >= lastInputTime + inputTime);

        if (canProduceNew && nextUnit && inputIntervalPassed && unit.status === 'IDLE') {
            const nextUnitCleanName = nextUnit.name.replace(/<br> /g, '');
            log('debug', `${currentTime}s: [투입 ${unit.name}] 새제품 투입조건 확인중. nextUnit:${nextUnitCleanName}, canTransfer:${canTransferProduct(unit, nextUnit, true)}`);
            if(canTransferProduct(unit, nextUnit, true)) {
                 const nextUnitReadySignalName = `${nextUnitCleanName}_load_enable`;
                 log('debug', `${currentTime}s: [투입 ${unit.name}] 다음유닛 ${nextUnitCleanName}의 ${nextUnitReadySignalName} 신호: ${nextUnit.signals[nextUnitReadySignalName]}`);
                 if (nextUnit.signals[nextUnitReadySignalName] === true || nextUnit.type === 'output') {
                    const newProduct = { id: nextProductId, creationTime: currentTime };
                    log('info', `${currentTime}s: [투입 ${unit.name}] 제품 ${newProduct.id} 생성시도 (inputTime: ${inputTime}s).`);
                    if (inputTime === 0) {
                        if (transferProduct(newProduct, unit, nextUnit)) {
                            lastInputTime = currentTime; nextProductId++;
                            log('info', `${currentTime}s: [투입 ${unit.name}] 제품 ${newProduct.id} 즉시전송성공.`);
                        } else log('warn', `${currentTime}s: [투입 ${unit.name}] 제품 ${newProduct.id} 즉시전송실패.`);
                    } else {
                        unit.products.push(newProduct); unit.status = 'PROCESSING_DELAY'; unit.delayEndTime = currentTime + inputTime;
                        nextProductId++;
                        log('info', `${currentTime}s: [투입 ${unit.name}] 제품 ${newProduct.id} 투입시작 (딜레이 ${inputTime}s, 종료 ${unit.delayEndTime}s).`);
                    }
                } else log('debug', `${currentTime}s: [투입 ${unit.name}] -> 다음유닛 ${nextUnitCleanName} 수신준비안됨 (신호 ${nextUnitReadySignalName}:${nextUnit.signals[nextUnitReadySignalName]})`);
            } else log('debug', `${currentTime}s: [투입 ${unit.name}] -> 다음유닛 ${nextUnitCleanName} 공간없거나 준비안됨 (canTransferProduct false).`);
        } else {
            if (!canProduceNew && totalQty !== undefined) log('debug', `${currentTime}s: [투입 ${unit.name}] 생산수량(${totalQty}) 도달.`);
            else if (!inputIntervalPassed) log('debug', `${currentTime}s: [투입 ${unit.name}] 투입간격(${inputTime}s) 미경과 (마지막:${lastInputTime}).`);
            else if (unit.status !== 'IDLE') log('debug', `${currentTime}s: [투입 ${unit.name}] IDLE 상태 아님 (${unit.status}).`);
        }
    }

    async function processNormalUnit(unit) {
        log('debug', `${currentTime}s: [일반 ${unit.name}] 처리. 제품:${(unit.products || []).map(p=>p.id)}, 상태:${unit.status}, 액션:${unit.currentActionIndex}-${unit.currentCommandIndex}, 신호:${JSON.stringify(unit.signals)}`);
        
        if (unit.status === 'PROCESSING_DELAY_COMMAND' || unit.status === 'PROCESSING_DELAY') {
            if (currentTime >= unit.delayEndTime) {
                log('info', `${currentTime}s: [일반 ${unit.name}] 딜레이완료 (상태:${unit.status}, 시간:${currentTime}s, 종료시간:${unit.delayEndTime}s).`);
                unit.status = 'IDLE'; 
            } else {
                log('debug', `${currentTime}s: [일반 ${unit.name}] 딜레이중 (종료:${unit.delayEndTime})`);
                return; 
            }
        }

        const currentProduct = (unit.products || [])[0];
        const firstActionFirstCommand = unit.currentActionIndex === 0 && unit.currentCommandIndex === 0;
        let currentActionGroupIsLoadEnable = false;
        if (unit.config.actions && unit.config.actions[unit.currentActionIndex] && unit.config.actions[unit.currentActionIndex].commands[unit.currentCommandIndex]) {
            const cmd = unit.config.actions[unit.currentActionIndex].commands[unit.currentCommandIndex];
            if (cmd.type === "SET_SIGNAL" && cmd.signal.includes("_load_enable") && cmd.value === true) {
                currentActionGroupIsLoadEnable = true;
            }
        }

        if (!currentProduct && !firstActionFirstCommand && !currentActionGroupIsLoadEnable) {
            log('debug', `${currentTime}s: [일반 ${unit.name}] 제품대기중 (실행불가행동)`);
            return;
        }

        if (!unit.config.actions || unit.config.actions.length === 0) {
            if (currentProduct && unit.config.nextUnitId) {
                const nextU = getUnitDataById(unit.config.nextUnitId);
                if (nextU && canTransferProduct(unit, nextU)) {
                    log('info', `${currentTime}s: [일반 ${unit.name}] 행동없음. 제품 ${currentProduct.id} -> ${nextU.name.replace(/<br> /g, '')} 전송시도.`);
                    transferProduct(currentProduct, unit, nextU);
                } else {
                    log('debug', `${currentTime}s: [일반 ${unit.name}] 행동없음. 제품 ${currentProduct.id} 전송불가 (다음유닛 ${nextU ? nextU.name.replace(/<br> /g, '') : '없음'} 수신불가).`);
                }
            }
            return;
        }

        let commandExecutedThisStep = false; 
        let actionGroup = unit.config.actions[unit.currentActionIndex];
        
        if (actionGroup && unit.currentCommandIndex >= actionGroup.commands.length) {
            log('debug', `${currentTime}s: [일반 ${unit.name}] 행동그룹 '${actionGroup.name}' 모든 명령어 완료.`);
            unit.currentActionIndex++;
            unit.currentCommandIndex = 0;
            actionGroup = unit.config.actions[unit.currentActionIndex]; 
        }

        if (unit.currentActionIndex >= unit.config.actions.length) {
            log('debug', `${currentTime}s: [일반 ${unit.name}] 모든 행동그룹 완료. 제품:${currentProduct ? currentProduct.id : '없음'}`);
            if (currentProduct && unit.config.nextUnitId) {
                const nextU = getUnitDataById(unit.config.nextUnitId);
                if (nextU && canTransferProduct(unit, nextU)) {
                    log('info', `${currentTime}s: [일반 ${unit.name}] 모든 행동 완료 후 제품 ${currentProduct.id} -> ${nextU.name.replace(/<br> /g, '')} 전송시도.`);
                    transferProduct(currentProduct, unit, nextU);
                } else {
                    log('debug', `${currentTime}s: [일반 ${unit.name}] 모든 행동 완료 후 제품 ${currentProduct.id} 전송불가 (다음유닛 ${nextU ? nextU.name.replace(/<br> /g, '') : '없음'} 수신불가).`);
                }
            }
            unit.currentActionIndex = 0; 
            unit.currentCommandIndex = 0;
            log('debug', `${currentTime}s: [일반 ${unit.name}] 모든 행동 완료 후 액션/커맨드 인덱스 리셋.`);
            return;
        }

        const command = actionGroup ? actionGroup.commands[unit.currentCommandIndex] : null;

        if (!command) {
            log('debug', `${currentTime}s: [일반 ${unit.name}] 현재 액션그룹(${actionGroup ? actionGroup.name : '없음'})에 실행할 명령어 없음. 다음 액션그룹 시도 또는 리셋.`);
            unit.currentActionIndex = 0;
            unit.currentCommandIndex = 0;
            return;
        }
        
        log('debug', `${currentTime}s: [일반 ${unit.name}] 행동 '${actionGroup.name}', 명령어 '${command.type}' (${command.description || command.signal || ''}) 실행시도.`);

        switch (command.type) {
            case 'SET_SIGNAL':
                unit.signals[command.signal] = command.value;
                log('info', `${currentTime}s: [일반 ${unit.name}] 신호 '${command.signal}' = ${command.value}`);
                commandExecutedThisStep = true;
                break;
            case 'DELAY':
                if (unit.status !== 'PROCESSING_DELAY_COMMAND' && unit.status !== 'PROCESSING_DELAY') { 
                    if (!currentProduct && !firstActionFirstCommand && !currentActionGroupIsLoadEnable) {
                        log('debug', `${currentTime}s: [일반 ${unit.name}] 딜레이 '${command.description}' 시작불가 - 제품없음.`);
                        break; 
                    }
                    unit.status = 'PROCESSING_DELAY_COMMAND'; 
                    unit.delayEndTime = currentTime + command.duration;
                    log('info', `${currentTime}s: [일반 ${unit.name}] 딜레이 '${command.description}' ${command.duration}s 시작 (종료 ${unit.delayEndTime}s).`);
                    commandExecutedThisStep = true; 
                } else if (unit.status === 'IDLE') { 
                    log('debug', `${currentTime}s: [일반 ${unit.name}] 딜레이 '${command.description}' 방금 완료됨. 다음 커맨드 진행.`);
                    commandExecutedThisStep = true;
                }
                break;
            default:
                log('warn', `[일반 ${unit.name}] 알수없는 명령어: ${command.type}`);
                commandExecutedThisStep = true; 
                break;
        }

        if (commandExecutedThisStep) {
            unit.currentCommandIndex++;
            log('debug', `${currentTime}s: [일반 ${unit.name}] 명령어 완료/시작 후 다음 명령어 인덱스: ${unit.currentCommandIndex}`);
        }
    }

    function processOutputUnit(unit) {
        log('debug', `${currentTime}s: [배출 ${unit.name}] 처리. 제품:${(unit.products || []).length}, 마지막배출:${unit.lastDischargeTime === -Infinity ? '없음' : unit.lastDischargeTime + 's'}`);
        if (!unit.products || unit.products.length === 0) {
            return;
        }
        const dischargeInterval = unit.config.dischargeInterval || 0;
        if (unit.lastDischargeTime === -Infinity || currentTime >= unit.lastDischargeTime + dischargeInterval) {
            const productToDischarge = unit.products.shift(); 
            if (productToDischarge) {
                totalDischargedCount++;
                unit.lastDischargeTime = currentTime;
                log('info', `${currentTime}s: [배출 ${unit.name}] 제품 ${productToDischarge.id} 배출 완료. 총 배출 수량: ${totalDischargedCount}`);
                updateUnitDisplay(unit); 
                updateTotalDischargedDisplay(); 
            } else {
                log('warn', `${currentTime}s: [배출 ${unit.name}] 제품을 꺼내오려 했으나 실패.`);
            }
        } else {
            log('debug', `${currentTime}s: [배출 ${unit.name}] 다음 배출까지 대기중 (간격: ${dischargeInterval}s, 다음 배출 가능 시간: ${unit.lastDischargeTime + dischargeInterval}s)`);
        }
    }

    function canTransferProduct(sourceUnit, targetUnit, isInputUnitCheck = false) {
        // ... (canTransferProduct 함수 본문은 기존과 동일하게 유지) ...
        if (!targetUnit) { log('debug', `canTransfer: ${sourceUnit.name} -> targetUnit 없음`); return false; }
        const targetMaxCap = targetUnit.config.maxCapacity === Infinity ? Number.MAX_SAFE_INTEGER : targetUnit.config.maxCapacity;
        if (targetUnit.products.length >= targetMaxCap) { log('debug', `canTransfer: ${sourceUnit.name} -> ${targetUnit.name.replace(/<br> /g, '')} 용량초과 (${targetUnit.products.length}/${targetMaxCap})`); return false; }
        if (targetUnit.type !== 'output') {
            const targetReadySignalName = `${targetUnit.name.replace(/\s|<br> /g, '')}_load_enable`;
            if (targetUnit.signals[targetReadySignalName] !== true) {
                log('debug', `canTransfer: ${sourceUnit.name} -> ${targetUnit.name.replace(/<br> /g, '')} 수신준비안됨 (신호 ${targetReadySignalName}: ${targetUnit.signals[targetReadySignalName]})`);
                return false;
            }
        }
        log('debug', `canTransfer: ${sourceUnit.name} -> ${targetUnit.name.replace(/<br> /g, '')} 가능`);
        return true;
    }

    function transferProduct(product, sourceUnit, targetUnit) {
        // ... (transferProduct 함수 본문은 기존과 동일하게 유지) ...
        if (!product || !targetUnit) { log('error', "transferProduct: product 또는 targetUnit 없음"); return false; }
        const productIndexInSource = sourceUnit.products.findIndex(p => p.id === product.id);
        if (productIndexInSource > -1) sourceUnit.products.splice(productIndexInSource, 1);
        else { if(!(sourceUnit.type === 'input' && (sourceUnit.config.inputTime || 0) === 0)) log('warn', `transferProduct: 제품 ${product.id} 을(를) ${sourceUnit.name} 에서 찾을 수 없음. 현재 제품: ${(sourceUnit.products || []).map(p=>p.id)}`); }
        targetUnit.products.push(product);
        log('info', `${currentTime}s: 제품 ${product.id} 이동완료: ${sourceUnit.name} (${(sourceUnit.products || []).length}개) -> ${targetUnit.name.replace(/<br> /g, '')} (${(targetUnit.products || []).length}개)`);
        if (targetUnit.type !== 'output') {
             const targetReadySignalName = `${targetUnit.name.replace(/\s|<br> /g, '')}_load_enable`;
             targetUnit.signals[targetReadySignalName] = false; 
             log('debug', `${currentTime}s: [유닛 ${targetUnit.name.replace(/<br> /g, '')}] 제품수신 후 ${targetReadySignalName} 신호 OFF`);
        }
        return true;
    }

    // ★★★ 시뮬레이션 메인 스텝 함수 ★★★
    // Promise<boolean>을 반환하도록 수정: 중요 이벤트 발생 여부
    async function runSingleStep(isManualStep = false) {
        // log('info', `스텝 실행 시작 (현재 시간: ${currentTime}, 내부 스텝: ${currentStep}, 수동 스텝: ${manualStepCount})`); 

        let productMovedThisCall = false;       
        let significantEventThisCall = false;   

        const maxMicroSteps = 200; 
        let microStepCount = 0;

        do {
            currentTime++; 
            currentStep = currentTime; 
            microStepCount++;
            log('debug', `마이크로 스텝 ${microStepCount} 시작 (전체 스텝: ${currentStep}, 시간: ${currentTime}s)`);
            
            const productsBeforeMicroStep = units.map(u => u.products.length);
            const signalsBeforeMicroStep = units.map(u => JSON.stringify(u.signals));

            for (const unit of units) {
                if (unit.type === 'input') {
                    processInputUnit(unit);
                } else if (unit.type === 'normal') {
                    await processNormalUnit(unit);
                } else if (unit.type === 'output') {
                    processOutputUnit(unit);
                }
            }
            
            const productsAfterMicroStep = units.map(u => u.products.length);
            if (JSON.stringify(productsBeforeMicroStep) !== JSON.stringify(productsAfterMicroStep)) {
                if (!productMovedThisCall) {
                    log('info', `제품 이동 발생 (마이크로 스텝 ${microStepCount}에서).`);
                }
                productMovedThisCall = true;      
                significantEventThisCall = true;  
            }

            const signalsAfterMicroStep = units.map(u => JSON.stringify(u.signals));
            if (JSON.stringify(signalsBeforeMicroStep) !== JSON.stringify(signalsAfterMicroStep)) {
                if (!significantEventThisCall) { 
                     log('info', `신호 변경 발생 (마이크로 스텝 ${microStepCount}에서).`);
                }
                significantEventThisCall = true; 
            }
            
            updateDisplays(); 
            updateAllConnectionLines();

            if (microStepCount >= maxMicroSteps) {
                log('warn', `최대 마이크로 스텝(${maxMicroSteps}) 실행. 루프 강제 종료.`);
                break;
            }

            if (isManualStep) {
                if (productMovedThisCall) {
                    log('debug', '수동 스텝: "제품 이동"이 감지되어 마이크로 루프를 종료합니다.');
                    break; 
                }
            } else { 
                if (significantEventThisCall) {
                    log('debug', '자동 스텝: "중요 이벤트"가 감지되어 마이크로 루프(runSingleStep 내부)를 종료합니다.');
                    break;
                }
            }
        } while (microStepCount < maxMicroSteps);

        if (isManualStep) {
            let summary = `수동 스텝 완료 (총 마이크로 스텝: ${microStepCount}). `;
            if (productMovedThisCall) {
                summary += "제품 이동 발생함.";
            } else if (significantEventThisCall) {
                summary += "제품 이동은 없었으나 신호 등 기타 중요 이벤트 발생함.";
            } else {
                summary += "제품 이동이나 기타 중요 이벤트 없이 종료됨.";
            }
            log('info', summary);
            
            if (simulationStepPromiseResolve) {
                simulationStepPromiseResolve();
                simulationStepPromiseResolve = null;
            }
            return productMovedThisCall; 
        } else {
            log('debug', `자동 스텝 runSingleStep 완료. 이벤트 발생: ${significantEventThisCall}`);
            return significantEventThisCall;
        }
    }

    // ★★★ 시뮬레이션 전체 실행 루프 ★★★
    async function runFullSimulationLoop() {
        log('info', "전체 시뮬레이션 루프 시작됨.");
        let consecutiveNoEventSteps = 0;
        const maxConsecutiveNoEventSteps = 10; 

        while (simulationRunning && !stopFullSimulationRequested) {
            const inputUnit = units.find(u => u.type === 'input');
            if (inputUnit && inputUnit.config.totalQuantity !== undefined) {
                if (nextProductId > inputUnit.config.totalQuantity && inputUnit.products.length === 0) {
                    const allOtherUnitsEmpty = units.filter(u => u.type !== 'input' && u.type !== 'output')
                                                  .every(u => u.products.length === 0);
                    if (allOtherUnitsEmpty) {
                        log('info', `전체 시뮬레이션: 투입 유닛(${inputUnit.name})의 목표 수량(${inputUnit.config.totalQuantity}) 생산 완료 및 모든 중간 유닛 비었음. 자동 중지.`);
                        simulationRunning = false;
                        break;
                    }
                }
            }

            const significantEventOccurredInStep = await runSingleStep(false); 

            if (significantEventOccurredInStep) {
                consecutiveNoEventSteps = 0; 
            } else {
                consecutiveNoEventSteps++;
                log('debug', `전체 시뮬레이션: ${consecutiveNoEventSteps}번째 연속 이벤트 없는 스텝.`);
            }

            if (consecutiveNoEventSteps >= maxConsecutiveNoEventSteps) {
                const allUnitsIdleOrEmpty = units.every(u => 
                    u.status === 'IDLE' || 
                    (u.type === 'input' && (u.config.totalQuantity !== undefined && nextProductId > u.config.totalQuantity) && u.products.length === 0) ||
                    ((u.type === 'normal' || u.type ==='output') && u.products.length === 0)
                );
                const allProductsDischarged = inputUnit && inputUnit.config.totalQuantity !== undefined && totalDischargedCount >= inputUnit.config.totalQuantity;

                if (allUnitsIdleOrEmpty || allProductsDischarged) {
                    log('info', "전체 시뮬레이션: 더 이상 진행할 이벤트가 없거나 모든 제품이 배출되어 자동 중지합니다.");
                    simulationRunning = false;
                    break;
                }
            }

            await new Promise(resolve => setTimeout(resolve, 10)); 
        }

        if (stopFullSimulationRequested) {
            log('info', "전체 시뮬레이션이 사용자에 의해 중지되었습니다.");
        } else if (!simulationRunning) {
            log('info', "전체 시뮬레이션 루프가 조건을 만족하여 자동 종료되었습니다.");
        } 
        
        simulationRunning = false; 
        stopFullSimulationRequested = false; 
        runAllBtn.textContent = "전체 실행";
        log('info', "전체 시뮬레이션 루프 종료됨.");

        // 루프 종료 후 UI 업데이트 강제 실행
        updateDisplays();
        units.forEach(updateUnitDisplay);
        updateAllConnectionLines();
    }

    if (stepRunBtn) {
        stepRunBtn.addEventListener('click', async () => {
            log('debug', "스텝 실행 버튼 클릭됨");
            if (simulationRunning) {
                log('warn', "전체 시뮬레이션 실행 중에는 스텝 실행을 할 수 없습니다.");
                alert("전체 시뮬레이션 실행 중에는 스텝 실행을 할 수 없습니다.");
                return;
            }
            manualStepCount++; // 수동 스텝 카운트 증가
            log('info', `수동 스텝 ${manualStepCount} 실행 시작`);
            await new Promise(resolve => {
                simulationStepPromiseResolve = resolve; // runSingleStep 내부에서 호출될 resolve 함수를 설정
                runSingleStep(true); // 수동 스텝임을 알림
            });
            // runSingleStep이 완료된 후 (simulationStepPromiseResolve가 호출된 후) 아래 로직 실행
            updateDisplays();
            units.forEach(updateUnitDisplay); // 각 유닛의 제품 표시 등 업데이트
            updateAllConnectionLines(); // 연결선 업데이트
            log('info', `수동 스텝 ${manualStepCount} 실행 완료`);
        });
    }

    initialize();
});