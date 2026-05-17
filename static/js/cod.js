/**
 * Learn with Kabeer - Course on Demand (COD) Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chatForm');
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const confirmModal = document.getElementById('confirmModal');
    const modalCost = document.getElementById('modalCost');
    const finalGenerateBtn = document.getElementById('finalGenerateBtn');
    const successOverlay = document.getElementById('successOverlay');

    let isThinking = false;

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message || isThinking) return;

        appendMessage('user', message);
        userInput.value = '';
        setThinking(true);

        try {
            const response = await fetch('/cod/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            const data = await response.json();

            if (data.error) {
                appendMessage('assistant', `**Error:** ${data.error}`);
            } else {
                appendMessage('assistant', data.response);
                
                if (data.needs_confirmation) {
                    showModal(data.cost);
                }
            }
        } catch (err) {
            appendMessage('assistant', "**System Error:** Connection to the architect lost.");
        } finally {
            setThinking(false);
        }
    });

    finalGenerateBtn.addEventListener('click', async () => {
        hideModal();
        setThinking(true, "Forging course content... This may take a moment.");
        
        try {
            const response = await fetch('/cod/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();

            if (data.status === 'success') {
                showSuccess(data.url);
            } else {
                appendMessage('assistant', `**Architectural Failure:** ${data.error}`);
                setThinking(false);
            }
        } catch (err) {
            appendMessage('assistant', "**System Error:** Failed to commit content to database.");
            setThinking(false);
        }
    });

    function appendMessage(role, content) {
        const wrapper = document.createElement('div');
        wrapper.className = `flex gap-4 message-enter`;
        
        const avatar = document.createElement('div');
        avatar.className = `flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${role === 'assistant' ? 'bg-amber-100 text-amber-600' : 'bg-slate-100 text-slate-600'}`;
        avatar.innerHTML = `<i data-lucide="${role === 'assistant' ? 'bot' : 'user'}" class="h-5 w-5"></i>`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'space-y-4 max-w-[85%]';
        
        const bubble = document.createElement('div');
        bubble.className = `rounded-2xl border border-[#E5E5E5] bg-white p-5 shadow-sm`;
        
        // Simple markdown parsing for bold and line breaks
        let formatted = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\n/g, '<br>');
        
        bubble.innerHTML = `<p class="text-[15px] leading-relaxed text-[#404040]">${formatted}</p>`;
        
        contentDiv.appendChild(bubble);
        wrapper.appendChild(avatar);
        wrapper.appendChild(contentDiv);
        
        chatMessages.firstElementChild.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        if (window.lucide) lucide.createIcons();
    }

    function setThinking(thinking, text = "Architecting next step...") {
        isThinking = thinking;
        userInput.disabled = thinking;
        sendBtn.disabled = thinking;
        
        if (thinking) {
            statusIndicator.classList.remove('hidden');
            statusText.innerText = text;
        } else {
            statusIndicator.classList.add('hidden');
        }
    }

    function showModal(cost) {
        modalCost.innerText = cost;
        confirmModal.classList.remove('opacity-0', 'pointer-events-none');
        confirmModal.firstElementChild.classList.remove('scale-95');
    }

    window.hideModal = function() {
        confirmModal.classList.add('opacity-0', 'pointer-events-none');
        confirmModal.firstElementChild.classList.add('scale-95');
    };

    function showSuccess(url) {
        successOverlay.classList.remove('opacity-0', 'pointer-events-none');
        setTimeout(() => {
            window.location.href = url;
        }, 2500);
    }
});
