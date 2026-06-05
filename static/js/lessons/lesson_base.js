document.addEventListener("DOMContentLoaded", function() {
    if (typeof lucide !== 'undefined') lucide.createIcons();
});

window.copyToClipboard = function(btn) {
    const code = btn.getAttribute('data-code');
    const textSpan = btn.querySelector('.copy-text');
    const icon = btn.querySelector('i');

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(code).then(() => {
            updateButton();
        });
    } else {
        const textArea = document.createElement("textarea");
        textArea.value = code;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            updateButton();
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
        }
        document.body.removeChild(textArea);
    }

    function updateButton() {
        const originalText = textSpan ? textSpan.textContent : 'Copy';
        if (textSpan) textSpan.textContent = 'Copied!';
        btn.classList.add('text-green-500');
        
        if (window.lucide) {
            const iconEl = btn.querySelector('[data-lucide]');
            if (iconEl) {
                iconEl.setAttribute('data-lucide', 'check');
                lucide.createIcons();
            }
        }

        setTimeout(() => {
            if (textSpan) textSpan.textContent = originalText;
            btn.classList.remove('text-green-500');
            if (window.lucide) {
                const iconEl = btn.querySelector('[data-lucide]');
                if (iconEl) {
                    iconEl.setAttribute('data-lucide', 'copy');
                    lucide.createIcons();
                }
            }
        }, 2000);
    }
};
