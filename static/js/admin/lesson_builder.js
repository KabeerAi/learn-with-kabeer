const canvas = document.getElementById('canvas');
const palette = document.getElementById('palette-items');
const emptyState = document.getElementById('canvas-empty');
let builderData = [];
let editingBlockId = null;
let monacoEditor = null;
let currentImageTab = 'url';

// --- Monaco Initialization ---
require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });

function initMonaco(value = '', language = 'python') {
    if (monacoEditor) {
        monacoEditor.setValue(value);
        updateMonacoLanguage(language);
        return;
    }

    require(['vs/editor/editor.main'], function () {
        monacoEditor = monaco.editor.create(document.getElementById('monaco-editor-container'), {
            value: value,
            language: language,
            theme: 'vs-dark',
            automaticLayout: true,
            fontSize: 14,
            fontFamily: 'JetBrains Mono, monospace',
            minimap: { enabled: false },
            padding: { top: 20, bottom: 20 },
            lineNumbers: 'on',
            roundedSelection: true,
            scrollBeyondLastLine: false,
            readOnly: false,
            cursorStyle: 'line',
        });
    });
}

function updateMonacoLanguage(lang) {
    if (!monacoEditor) return;
    const model = monacoEditor.getModel();
    monaco.editor.setModelLanguage(model, lang === 'terminal' ? 'shell' : lang);
}

// --- Core Engine ---

function generateId() {
    return 'blk-' + Math.random().toString(36).substr(2, 9);
}

function createBlock(type, data = null) {
    return {
        id: generateId(),
        type: type,
        data: data || getDefaultDataForType(type)
    };
}

function getDefaultDataForType(type) {
    switch(type) {
        case 'heading': return { text: 'New Heading' };
        case 'subheading': return { text: 'New Subheading' };
        case 'text': return { text: 'Type your story here...' };
        case 'list': return { items: ['First list item'] };
        case 'separator': return {};
        case 'image': return { url: '' };
        case 'code': return { lang: 'python', code: '# Add your code\nprint("Hello World")' };
        case 'callout': return { type: 'info', title: 'Did you know?', body: 'Interesting fact goes here.' };
        case 'quiz': return { question: 'What is the correct answer?', options: ['Option A', 'Option B'], correct: 0 };
        default: return {};
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

// --- Rendering ---

function renderCanvas() {
    canvas.innerHTML = '';
    
    if (builderData.length === 0) {
        emptyState.style.display = 'flex';
        emptyState.style.opacity = '1';
    } else {
        emptyState.style.opacity = '0';
        setTimeout(() => {
            if (builderData.length > 0) emptyState.style.display = 'none';
        }, 300);

        builderData.forEach(block => {
            canvas.appendChild(renderBlock(block));
        });
    }

    if (window.lucide) lucide.createIcons();
    if (typeof Prism !== 'undefined') Prism.highlightAllUnder(canvas);
}

function renderBlock(block) {
    try {
        let html = '';
        
        if (block.type === 'heading') {
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="heading">
<h2 contenteditable="true" onblur="updateBlockData('${block.id}', {text: this.innerText})" class="m-0 cursor-text text-2xl font-bold text-gray-900 focus:outline-none w-full text-left">${block.data.text}</h2>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn" onclick="duplicateBlock('${block.id}')" title="Duplicate"><i data-lucide="copy" class="w-4 h-4"></i></button>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        } else if (block.type === 'subheading') {
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="subheading">
<h3 contenteditable="true" onblur="updateBlockData('${block.id}', {text: this.innerText})" class="m-0 cursor-text text-xl font-bold text-gray-800 focus:outline-none w-full text-left">${block.data.text}</h3>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn" onclick="duplicateBlock('${block.id}')" title="Duplicate"><i data-lucide="copy" class="w-4 h-4"></i></button>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        } else if (block.type === 'text') {
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="text">
<p contenteditable="true" onblur="updateBlockData('${block.id}', {text: this.innerText})" class="m-0 p-0 cursor-text text-base leading-7 text-gray-700 focus:outline-none whitespace-pre-wrap w-full text-left" style="margin: 0; padding: 0;">${block.data.text}</p>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn" onclick="duplicateBlock('${block.id}')" title="Duplicate"><i data-lucide="copy" class="w-4 h-4"></i></button>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        } else if (block.type === 'list') {
            let itemsHtml = '';
            for (let i = 0; i < block.data.items.length; i++) {
                const item = block.data.items[i];
                itemsHtml += `<div class="group/opt flex w-full items-start gap-3">
                    <div class="mt-2.5 h-1.5 w-1.5 rounded-full bg-gold-500 shrink-0"></div>
                    <div contenteditable="true" onblur="updateListItem('${block.id}', ${i}, this.innerText)" class="flex-1 text-sm text-gray-700 focus:outline-none py-1">${item}</div>
                    <button onclick="removeListItem('${block.id}', ${i})" class="opacity-0 group-hover/opt:opacity-100 text-gray-400 hover:text-red-500 transition-all shrink-0 mt-1"><i data-lucide="x" class="w-3.5 h-3.5"></i></button>
                </div>`;
            }
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="list">
<div class="not-prose w-full rounded-xl border border-gray-200 bg-white p-6 text-left">
    <div class="flex items-center gap-2 mb-4">
        <i data-lucide="list" class="w-4 h-4 text-gray-400"></i>
        <span class="text-[10px] font-bold uppercase tracking-widest text-gray-400">List Component</span>
    </div>
    <div class="flex flex-col gap-3 mb-4">
        ${itemsHtml}
    </div>
    <button onclick="addListItem('${block.id}')" class="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-900 transition-colors">
        <i data-lucide="plus" class="w-3.5 h-3.5"></i> Add list item
    </button>
</div>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn" onclick="duplicateBlock('${block.id}')" title="Duplicate"><i data-lucide="copy" class="w-4 h-4"></i></button>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        } else if (block.type === 'separator') {
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="separator">
<div class="w-full py-4 flex items-center gap-4">
    <div class="flex-1 h-px bg-gray-200"></div>
    <span class="text-xs font-bold uppercase tracking-widest text-gray-400">CONTINUE</span>
    <div class="flex-1 h-px bg-gray-200"></div>
</div>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        } else if (block.type === 'quiz') {
            let optionsHtml = '';
            for (let i = 0; i < block.data.options.length; i++) {
                const opt = block.data.options[i];
                const isCorrect = i === block.data.correct;
                optionsHtml += `<div class="group/opt flex w-full items-center gap-3 rounded-lg border ${isCorrect ? 'border-gray-900 bg-gray-50' : 'border-gray-200'} px-4 py-3 text-left transition-colors">
                    <div class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full border ${isCorrect ? 'border-gray-900 bg-gray-900' : 'border-gray-300'} transition-colors shrink-0" onclick="setQuizCorrect('${block.id}', ${i})">
                        ${isCorrect ? '<div class="h-1.5 w-1.5 rounded-full bg-white"></div>' : ''}
                    </div>
                    <div contenteditable="true" onblur="updateQuizOption('${block.id}', ${i}, this.innerText)" class="flex-1 text-sm text-gray-700 focus:outline-none">${opt}</div>
                    <button onclick="removeQuizOption('${block.id}', ${i})" class="opacity-0 group-hover/opt:opacity-100 text-gray-400 hover:text-red-500 transition-all shrink-0"><i data-lucide="x" class="w-3.5 h-3.5"></i></button>
                </div>`;
            }
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="quiz">
<div class="not-prose w-full rounded-xl border border-gray-200 bg-white p-6 text-left">
    <h3 contenteditable="true" onblur="updateBlockData('${block.id}', {question: this.innerText})" class="text-base font-semibold text-gray-900 mb-4 focus:outline-none">${block.data.question}</h3>
    <div class="flex flex-col gap-2.5 mb-4">
        ${optionsHtml}
    </div>
    <button onclick="addQuizOption('${block.id}')" class="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-900 transition-colors">
        <i data-lucide="plus" class="w-3.5 h-3.5"></i> Add option
    </button>
</div>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn" onclick="duplicateBlock('${block.id}')" title="Duplicate"><i data-lucide="copy" class="w-4 h-4"></i></button>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        } else if (block.type === 'code') {
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="code">
<div class="relative overflow-hidden rounded-xl border border-[#2A2A2A] bg-[#1C1C1C] w-full shadow-xl">
    <div class="flex items-center justify-between border-b border-[#2A2A2A] bg-black/20 px-5 py-3.5">
        <div class="flex items-center gap-4">
            <div class="flex gap-1.5">
                <div class="h-2.5 w-2.5 rounded-full bg-[#333333]"></div>
                <div class="h-2.5 w-2.5 rounded-full bg-[#333333]"></div>
                <div class="h-2.5 w-2.5 rounded-full bg-[#333333]"></div>
            </div>
            <div class="h-4 w-[1px] bg-[#2A2A2A]"></div>
            <span class="text-[11px] font-bold uppercase tracking-widest text-gray-500 font-mono">${block.data.lang}</span>
        </div>
        <button onclick="openCodeModal('${block.id}')" class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 hover:text-white transition-colors">
            <i data-lucide="edit-3" class="w-3.5 h-3.5"></i> Edit
        </button>
    </div>
    <pre class="language-${block.data.lang}"><code class="language-${block.data.lang}">${escapeHtml(block.data.code)}</code></pre>
</div>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn" onclick="duplicateBlock('${block.id}')" title="Duplicate"><i data-lucide="copy" class="w-4 h-4"></i></button>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        } else if (block.type === 'callout') {
            const isWarning = block.data.type === 'warning';
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="callout">
<div class="my-10 rounded-2xl border ${isWarning ? 'border-amber-200 bg-amber-50' : 'border-sky-200 bg-sky-50'} p-6 flex gap-4 w-full">
    <div class="w-12 h-12 shrink-0 rounded-2xl bg-white border border-inherit flex items-center justify-center cursor-pointer" onclick="toggleCalloutType('${block.id}')">
        <i data-lucide="${isWarning ? 'alert-triangle' : 'info'}" class="w-6 h-6 ${isWarning ? 'text-amber-600' : 'text-sky-600'}"></i>
    </div>
    <div class="flex-1">
        <h4 contenteditable="true" onblur="updateBlockData('${block.id}', {title: this.innerText})" class="text-xs font-bold uppercase tracking-widest text-gray-900 mb-2 focus:outline-none">${block.data.title}</h4>
        <div contenteditable="true" onblur="updateBlockData('${block.id}', {body: this.innerText})" class="text-base font-medium leading-relaxed text-gray-700 focus:outline-none">${block.data.body}</div>
    </div>
</div>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn" onclick="duplicateBlock('${block.id}')" title="Duplicate"><i data-lucide="copy" class="w-4 h-4"></i></button>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        } else if (block.type === 'image') {
            html = `<div class="canvas-item group/blk" id="${block.id}" data-type="image">
<div class="w-full rounded-xl overflow-hidden border border-gray-200 ${block.data.url ? 'shadow-sm' : 'bg-gray-50'}">
    ${block.data.url ? `<img src="${block.data.url}" class="w-full h-auto block" alt="">` : `<div class="p-8 text-center"><i data-lucide="image" class="w-12 h-12 mx-auto text-gray-400 mb-2"></i><p class="text-sm text-gray-500">No image yet</p></div>`}
    <div class="px-4 py-3 border-t border-gray-200 bg-white">
        <button onclick="openImageModal('${block.id}')" class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-gray-500 hover:text-gray-900 transition-colors">
            <i data-lucide="upload-cloud" class="w-3.5 h-3.5"></i> ${block.data.url ? 'Change Image' : 'Add Image'}
        </button>
    </div>
</div>
<div class="item-controls">
    <div class="control-btn drag-handle"><i data-lucide="grip-vertical" class="w-4 h-4"></i></div>
    <button class="control-btn" onclick="duplicateBlock('${block.id}')" title="Duplicate"><i data-lucide="copy" class="w-4 h-4"></i></button>
    <button class="control-btn delete" onclick="deleteBlock('${block.id}')" title="Delete"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
</div>
</div>`;
        }

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        const wrapper = tempDiv.firstElementChild;

        if (!wrapper) return document.createElement('div');

        // Click to select
        wrapper.addEventListener('click', (e) => {
            if (e.target.closest('.control-btn')) return;
            document.querySelectorAll('.canvas-item').forEach(el => el.classList.remove('is-selected'));
            wrapper.classList.add('is-selected');
        });

        return wrapper;
    } catch (e) {
        console.error("Rendering error for " + block.type, e);
        const errorEl = document.createElement('div');
        errorEl.className = "p-4 border border-red-200 bg-red-50 text-red-600 text-xs rounded-xl";
        errorEl.innerText = "Error rendering " + block.type;
        return errorEl;
    }
}

// --- Logic Actions ---

function updateBlockData(id, newData) {
    const blk = builderData.find(b => b.id === id);
    if (blk) {
        blk.data = { ...blk.data, ...newData };
        markUnsaved();
    }
}

function deleteBlock(id) {
    if (!confirm('Remove this block?')) return;
    builderData = builderData.filter(b => b.id !== id);
    renderCanvas();
    markUnsaved();
}

function duplicateBlock(id) {
    const idx = builderData.findIndex(b => b.id === id);
    if (idx !== -1) {
        const copy = JSON.parse(JSON.stringify(builderData[idx]));
        copy.id = generateId();
        builderData.splice(idx + 1, 0, copy);
        renderCanvas();
        markUnsaved();
    }
}

function toggleCalloutType(id) {
    const blk = builderData.find(b => b.id === id);
    if (blk) {
        blk.data.type = blk.data.type === 'info' ? 'warning' : 'info';
        renderCanvas();
        markUnsaved();
    }
}

function updateQuizOption(id, idx, val) {
    const blk = builderData.find(b => b.id === id);
    if (blk) {
        blk.data.options[idx] = val;
        markUnsaved();
    }
}

function addQuizOption(id) {
    const blk = builderData.find(b => b.id === id);
    if (blk) {
        blk.data.options.push('New choice');
        renderCanvas();
        markUnsaved();
    }
}

function removeQuizOption(id, idx) {
    const blk = builderData.find(b => b.id === id);
    if (blk && blk.data.options.length > 2) {
        blk.data.options.splice(idx, 1);
        if (blk.data.correct >= blk.data.options.length) blk.data.correct = 0;
        renderCanvas();
        markUnsaved();
    }
}

function setQuizCorrect(id, idx) {
    const blk = builderData.find(b => b.id === id);
    if (blk) {
        blk.data.correct = idx;
        renderCanvas();
        markUnsaved();
    }
}

// --- List Helpers ---

function updateListItem(id, idx, val) {
    const blk = builderData.find(b => b.id === id);
    if (blk) {
        blk.data.items[idx] = val;
        markUnsaved();
    }
}

function addListItem(id) {
    const blk = builderData.find(b => b.id === id);
    if (blk) {
        blk.data.items.push('New list item');
        renderCanvas();
        markUnsaved();
    }
}

function removeListItem(id, idx) {
    const blk = builderData.find(b => b.id === id);
    if (blk && blk.data.items.length > 1) {
        blk.data.items.splice(idx, 1);
        renderCanvas();
        markUnsaved();
    }
}

// --- Interactions ---

function initSortables() {
    new Sortable(palette, {
        group: { name: 'shared', pull: 'clone', put: false },
        sort: false,
        animation: 250
    });

    new Sortable(canvas, {
        group: 'shared',
        handle: '.drag-handle',
        animation: 250,
        ghostClass: 'sortable-ghost',
        filter: '[contenteditable="true"]', 
        preventOnFilter: false,
        onAdd: (evt) => {
            const type = evt.item.dataset.type;
            const newBlk = createBlock(type);
            builderData.splice(evt.newIndex, 0, newBlk);
            
            // Remove the cloned element added by SortableJS and let renderCanvas handle it
            evt.item.remove(); 
            
            renderCanvas();
            markUnsaved();
        },
        onUpdate: (evt) => {
            const item = builderData.splice(evt.oldIndex, 1)[0];
            builderData.splice(evt.newIndex, 0, item);
            markUnsaved();
        }
    });
}

// --- Modals ---

function openCodeModal(id) {
    editingBlockId = id;
    const blk = builderData.find(b => b.id === id);
    document.getElementById('input-code-lang').value = blk.data.lang;
    initMonaco(blk.data.code, blk.data.lang);
    document.getElementById('modal-code').style.display = 'flex';
}

function applyCodeChanges() {
    updateBlockData(editingBlockId, {
        lang: document.getElementById('input-code-lang').value,
        code: monacoEditor.getValue()
    });
    closeModal('modal-code');
    renderCanvas();
}

function openImageModal(id) {
    editingBlockId = id;
    const blk = builderData.find(b => b.id === id);
    document.getElementById('input-img-url').value = blk.data.url;
    switchImageTab('url');
    document.getElementById('modal-image').style.display = 'flex';
}

function switchImageTab(tab) {
    currentImageTab = tab;
    const urlBtn = document.getElementById('tab-img-url');
    const uploadBtn = document.getElementById('tab-img-upload');
    const urlPanel = document.getElementById('panel-img-url');
    const uploadPanel = document.getElementById('panel-img-upload');

    if (tab === 'url') {
        urlBtn.classList.add('border-gray-900', 'text-gray-900');
        urlBtn.classList.remove('border-transparent', 'text-gray-400');
        uploadBtn.classList.remove('border-gray-900', 'text-gray-900');
        uploadBtn.classList.add('border-transparent', 'text-gray-400');
        urlPanel.classList.remove('hidden');
        uploadPanel.classList.add('hidden');
    } else {
        uploadBtn.classList.add('border-gray-900', 'text-gray-900');
        uploadBtn.classList.remove('border-transparent', 'text-gray-400');
        urlBtn.classList.remove('border-gray-900', 'text-gray-900');
        urlBtn.classList.add('border-transparent', 'text-gray-400');
        uploadPanel.classList.remove('hidden');
        urlPanel.classList.add('hidden');
    }
}

// Image Upload Logic
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('input-img-file');
const uploadStatus = document.getElementById('upload-status');

if (dropZone) {
    dropZone.onclick = () => fileInput.click();
    fileInput.onchange = (e) => handleFileUpload(e.target.files[0]);
}

async function handleFileUpload(file) {
    if (!file) return;
    uploadStatus.classList.remove('hidden');
    
    const formData = new FormData();
    formData.append('image', file);
    formData.append('lesson_id', window.BUILDER_CONFIG.lessonId);

    try {
        const res = await fetch(window.BUILDER_CONFIG.uploadImageUrl, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.url) {
            document.getElementById('input-img-url').value = data.url;
            switchImageTab('url');
        } else {
            alert('Upload failed: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        console.error(e);
        alert('Critical upload error');
    } finally {
        uploadStatus.classList.add('hidden');
    }
}

function applyImageChanges() {
    updateBlockData(editingBlockId, { url: document.getElementById('input-img-url').value });
    closeModal('modal-image');
    renderCanvas();
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
    editingBlockId = null;
}

// --- Save System ---

function markUnsaved() {
    const s = document.getElementById('save-status');
    if (s) {
        s.innerText = 'Unsaved changes';
        s.classList.remove('text-gray-400');
        s.classList.add('text-amber-500');
    }
}

function markSaved() {
    const s = document.getElementById('save-status');
    if (s) {
        s.innerText = 'All changes saved';
        s.classList.remove('text-amber-500');
        s.classList.add('text-gray-400');
    }
}

async function saveLesson() {
    const btn = document.querySelector('button[onclick="saveLesson()"]');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i data-lucide="loader" class="w-3.5 h-3.5 animate-spin"></i> Saving...';
    btn.disabled = true;

    const html = generateFinalHtml();
    const jsonStr = JSON.stringify(builderData);

    const formData = new FormData();
    formData.append('content', html);
    formData.append('builder_json', jsonStr);

    try {
        const res = await fetch(window.location.href, { method: 'POST', body: formData });
        if (res.ok) markSaved();
        else alert('Sync failure. Please check your connection.');
    } catch (e) {
        console.error(e);
        alert('CRITICAL: Server unreachable.');
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        if (window.lucide) lucide.createIcons();
    }
}

function generateFinalHtml() {
    let html = '';
    builderData.forEach(blk => {
        switch(blk.type) {
            case 'heading':
                html += `<h2 class="mb-8 mt-12 text-3xl font-extrabold tracking-tight text-gray-900">${blk.data.text}</h2>\n`;
                break;
            case 'subheading':
                html += `<h3 class="subheading-text">${blk.data.text}</h3>\n`;
                break;
            case 'text':
                html += `<p class="text-lg leading-relaxed text-gray-600 mb-6 font-medium">${blk.data.text}</p>\n`;
                break;
            case 'list':
                html += `<ul class="lesson-content">\n${blk.data.items.map(item => `    <li>${item}</li>`).join('\n')}\n</ul>\n`;
                break;
            case 'separator':
                // Separator doesn't render anything in final HTML, used for slide splitting
                break;
            case 'image':
                if (blk.data.url) {
                    html += `<div class="my-12 rounded-2xl overflow-hidden border border-gray-200 shadow-sm"><img src="${blk.data.url}" class="w-full h-auto block"></div>\n`;
                }
                break;
            case 'code':
                html += `
<div class="relative overflow-hidden rounded-xl border border-gray-800 bg-[#0D1117] shadow-xl my-10 not-prose group">
<div class="flex items-center justify-between border-b border-gray-800 bg-black/20 px-5 py-3.5">
    <div class="flex items-center gap-4">
        <span class="text-[11px] font-bold uppercase tracking-widest text-gray-500 font-mono">${blk.data.lang}</span>
    </div>
    <button onclick="copyToClipboard(this)" data-code="${escapeHtml(blk.data.code)}" class="flex items-center gap-2 rounded-md bg-gray-800 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 transition-all hover:bg-gray-700 hover:text-white">
        <i data-lucide="copy" class="w-3.5 h-3.5"></i>
        <span class="copy-text">Copy</span>
    </button>
</div>
<div class="overflow-x-auto">
    <pre class="language-${blk.data.lang}"><code class="language-${blk.data.lang}">${escapeHtml(blk.data.code)}</code></pre>
</div>
</div>\n`;
                break;
            case 'callout':
                const isWarn = blk.data.type === 'warning';
                html += `
<div class="my-10 rounded-2xl border ${isWarn ? 'border-amber-200 bg-amber-50' : 'border-sky-200 bg-sky-50'} p-8 flex gap-6 not-prose shadow-sm">
<div class="w-14 h-14 shrink-0 rounded-2xl bg-white border border-inherit flex items-center justify-center shadow-sm">
    <i data-lucide="${isWarn ? 'alert-triangle' : 'info'}" class="w-6 h-6 ${isWarn ? 'text-amber-600' : 'text-sky-600'}"></i>
</div>
<div>
    <h4 class="text-xs font-bold uppercase tracking-widest text-gray-900 mb-2">${blk.data.title}</h4>
    <div class="text-base font-medium leading-relaxed text-gray-700">${blk.data.body}</div>
</div>
</div>\n`;
                break;
            case 'quiz':
                html += `
<div class="quiz-container my-12 p-10 rounded-2xl border border-gray-200 bg-white shadow-sm" data-correct="${blk.data.correct}">
<div class="flex items-center gap-4 mb-8">
    <div class="w-8 h-8 rounded-xl bg-gray-900 flex items-center justify-center text-xs text-white font-bold">?</div>
    <h3 class="text-xl font-bold tracking-tight text-gray-900">${blk.data.question}</h3>
</div>
<div class="grid gap-3">
    ${blk.data.options.map((opt, i) => `
    <button type="button" onclick="checkQuiz(this, ${i})" class="group flex items-center justify-between p-5 border border-gray-100 rounded-xl text-left font-bold transition-all hover:border-gray-900 hover:bg-gray-50">
        <span class="text-gray-700">${opt}</span>
        <div class="w-5 h-5 rounded-full border border-gray-200 group-hover:border-gray-900"></div>
    </button>
    `).join('')}
</div>
</div>\n`;
                break;
        }
    });
    return html;
}

function previewLesson() {
    saveLesson().then(() => {
        window.open(window.BUILDER_CONFIG.lessonPreviewUrl, '_blank');
    });
}

function localEscapeHtml(t) {
    const d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML;
}

// --- Boot ---

document.addEventListener('DOMContentLoaded', () => {
    if (window.BUILDER_CONFIG) {
        builderData = window.BUILDER_CONFIG.initialData;
        renderCanvas();
        initSortables();

        // Keyboard save
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                saveLesson();
            }
        });
    }
});
