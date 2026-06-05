/**
 * Learn with Kabeer - Global Script
 * Core utilities, notifications, and animations.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // 2. Initialize Toast Notifications
    initToasts();

    // 3. Initialize Global Utility Listeners
    initGlobalUtilities();
});

/**
 * Toast Notification System
 */
function initToasts() {
    const container = document.getElementById('toast-container');
    if (!container || container.children.length === 0) return;

    const showToasts = () => {
        container.classList.remove('opacity-0', 'invisible');
        
        // Auto-dismiss toasts after 5 seconds
        setTimeout(() => {
            const toasts = container.querySelectorAll('.toast-item');
            toasts.forEach((toast, index) => {
                setTimeout(() => {
                    toast.classList.add('animate-out', 'fade-out', 'slide-out-to-right-4');
                    setTimeout(() => toast.remove(), 300);
                }, index * 100);
            });
        }, 5000);
    };

    const checkLoaders = () => {
        // Look for anything with 'loader' in ID or class
        const loaders = document.querySelectorAll('[id*="loader"], [class*="loader"]');
        const activeLoader = Array.from(loaders).find(l => {
            const style = window.getComputedStyle(l);
            // Consider it active if it's in the DOM and not explicitly hidden
            return style.display !== 'none' && style.visibility !== 'hidden' && l.isConnected;
        });

        if (!activeLoader) {
            // Give it one more tiny beat to ensure transitions finished
            setTimeout(showToasts, 100);
        } else {
            setTimeout(checkLoaders, 200);
        }
    };

    // Small initial delay to allow page-specific scripts to initialize their loaders
    setTimeout(checkLoaders, 100);
}

/**
 * Global Utility Functions
 */
function initGlobalUtilities() {
    // Shared Copy to Clipboard
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
}

/**
 * XP Award Animation Trigger
 * Called from templates when flashing XP messages.
 */
window.triggerXpAwards = function(allAwards) {
    if (allAwards.length > 0 && typeof playXpAnimation === 'function') {
        // Start animation after a slight delay to ensure UI is ready
        setTimeout(() => {
            playXpAnimation(allAwards);
        }, 500);
    }
};
