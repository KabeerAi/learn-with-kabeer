/**
 * Learn with Kabeer — Forge (Course on Demand) Frontend
 * Premium chat interface with character-by-character typing animation.
 */

document.addEventListener('DOMContentLoaded', () => {
    const codContainer = document.getElementById('cod-container');
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
    let isChatActive = false;
    let currentTypingAbort = null; // allows canceling a typing animation

    // ─── Form Submit ───────────────────────────────────────────────
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message || isThinking) return;

        if (!isChatActive) activateChat();

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
            appendMessage('assistant', '**Error:** Could not connect to the server.');
        } finally {
            setThinking(false);
        }
    });

    // ─── State Management ──────────────────────────────────────────
    function activateChat() {
        isChatActive = true;
        codContainer.classList.remove('state-initial');
        codContainer.classList.add('state-chat');
    }

    window.useSuggestion = function(btn) {
        // Get just the text from the span inside the button
        const span = btn.querySelector('span');
        userInput.value = span ? span.innerText.trim() : btn.innerText.trim();
        chatForm.dispatchEvent(new Event('submit'));
    };

    window.resetChat = function() {
        window.location.href = '/cod?reset=1';
    };

    // ─── Generate Confirmation ─────────────────────────────────────
    finalGenerateBtn.addEventListener('click', async () => {
        hideModal();
        setThinking(true, 'Generating course');

        try {
            const response = await fetch('/cod/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();

            if (data.status === 'success') {
                showSuccess(data.url);
            } else {
                appendMessage('assistant', `**Something went wrong:** ${data.error}`);
                setThinking(false);
            }
        } catch (err) {
            appendMessage('assistant', '**Error:** Could not save the course.');
            setThinking(false);
        }
    });

    // ─── Message Rendering ─────────────────────────────────────────
    function appendMessage(role, content) {
        const wrapper = document.createElement('div');
        wrapper.className = `flex flex-col ${role === 'assistant' ? 'items-start' : 'items-end'} message-enter w-full`;

        const messageBox = document.createElement('div');

        if (role === 'user') {
            messageBox.className = 'max-w-[75%] rounded-2xl bg-[#F4F4F5] px-5 py-3 text-[14px] leading-relaxed text-[#1C1C1C] font-normal';
            messageBox.innerText = content;
            wrapper.appendChild(messageBox);
            chatMessages.querySelector('.max-w-3xl').appendChild(wrapper);
        } else {
            messageBox.className = 'w-full chat-content';
            wrapper.appendChild(messageBox);
            chatMessages.querySelector('.max-w-3xl').appendChild(wrapper);
            typeMessageCharByChar(messageBox, formatMarkdown(content));
        }

        scrollToBottom();
        if (window.lucide) lucide.createIcons();
    }

    // ─── Character-by-Character Typing Animation ───────────────────
    async function typeMessageCharByChar(element, htmlContent) {
        // Create an abort controller for this typing session
        const abortController = { aborted: false };
        currentTypingAbort = abortController;

        // Parse HTML into a temporary container
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlContent;

        // Add a blinking cursor to the element
        const cursor = document.createElement('span');
        cursor.className = 'typing-cursor';
        element.appendChild(cursor);

        // Walk through all nodes and type them out
        await typeNodes(element, tempDiv.childNodes, cursor, abortController);

        // Remove cursor when done
        cursor.remove();
        scrollToBottom();
    }

    async function typeNodes(parent, nodes, cursor, abort) {
        for (const node of nodes) {
            if (abort.aborted) {
                // If aborted, dump remaining content instantly
                parent.insertBefore(node.cloneNode(true), cursor);
                continue;
            }

            if (node.nodeType === Node.TEXT_NODE) {
                // Type text character by character
                const text = node.textContent;
                const textNode = document.createTextNode('');
                parent.insertBefore(textNode, cursor);

                for (let i = 0; i < text.length; i++) {
                    if (abort.aborted) {
                        textNode.textContent = text; // dump rest instantly
                        break;
                    }
                    textNode.textContent += text[i];

                    // Variable speed: faster for spaces/punctuation, slower for letters
                    const ch = text[i];
                    let delay = 8;
                    if (ch === '.' || ch === '!' || ch === '?') delay = 60;
                    else if (ch === ',') delay = 30;
                    else if (ch === '\n') delay = 20;
                    else if (ch === ' ') delay = 5;

                    await sleep(delay);

                    // Scroll periodically (every 3 chars to avoid jank)
                    if (i % 3 === 0) scrollToBottom();
                }
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                // For block elements like <pre>, <ul>, etc., insert whole then animate children
                const tagName = node.tagName.toLowerCase();

                if (['pre', 'img', 'hr', 'br'].includes(tagName)) {
                    // Insert code blocks and media whole (no char-by-char for code)
                    const clone = node.cloneNode(true);
                    parent.insertBefore(clone, cursor);
                    await sleep(80);
                    scrollToBottom();
                } else {
                    // Create the element shell, then type its children
                    const shell = node.cloneNode(false); // clone without children
                    parent.insertBefore(shell, cursor);
                    shell.appendChild(cursor); // move cursor inside this element
                    await typeNodes(shell, node.childNodes, cursor, abort);
                    parent.insertBefore(cursor, shell.nextSibling); // move cursor back out
                }
            }
        }
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ─── Markdown Formatting ───────────────────────────────────────
    function formatMarkdown(text) {
        if (!text) return '';

        let html = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Code blocks
        html = html.replace(/```(\w+)?\n?([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
        });

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Italics
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Blockquotes
        html = html.replace(/^&gt; (.*$)/gm, '<blockquote>$1</blockquote>');

        // Headings
        html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>');

        // Lists
        const lines = html.split('\n');
        let result = '';
        let inList = false;

        lines.forEach(line => {
            const listMatch = line.match(/^[\-\*] (.*$)/);
            if (listMatch) {
                if (!inList) { result += '<ul>'; inList = true; }
                result += `<li>${listMatch[1]}</li>`;
            } else {
                if (inList) { result += '</ul>'; inList = false; }
                const trimmed = line.trim();
                if (trimmed.length > 0 && !line.startsWith('<h') && !line.startsWith('<blockquote') && !line.startsWith('<pre')) {
                    result += `<p>${line}</p>`;
                } else {
                    result += line;
                }
            }
        });
        if (inList) result += '</ul>';

        return result;
    }

    // ─── Thinking State ────────────────────────────────────────────
    function setThinking(thinking, text = 'Thinking') {
        isThinking = thinking;
        userInput.disabled = thinking;
        sendBtn.disabled = thinking;

        if (thinking) {
            statusIndicator.classList.remove('hidden');
            statusText.innerText = text;
            scrollToBottom();
        } else {
            statusIndicator.classList.add('hidden');
        }
    }

    // ─── Modal ─────────────────────────────────────────────────────
    function showModal(cost) {
        modalCost.innerText = formatNumber(cost);
        confirmModal.classList.remove('opacity-0', 'pointer-events-none');
        confirmModal.querySelector('div').classList.remove('scale-95');
    }

    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    window.hideModal = function() {
        confirmModal.classList.add('opacity-0', 'pointer-events-none');
        confirmModal.querySelector('div').classList.add('scale-95');
    };

    function showSuccess(url) {
        successOverlay.classList.remove('opacity-0', 'pointer-events-none');
        setTimeout(() => { window.location.href = url; }, 2000);
    }

    // ─── Helpers ───────────────────────────────────────────────────
    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }
});
