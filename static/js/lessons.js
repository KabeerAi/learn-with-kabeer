/**
 * Learn with Kabeer - Lesson Page Logic
 */

document.addEventListener("DOMContentLoaded", function() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    let isSidebarOpen = false;

    // --- Copy to Clipboard Utility ---
    window.copyToClipboard = function(btn) {
        const code = btn.getAttribute('data-code');
        const textSpan = btn.querySelector('.copy-text');
        const icon = btn.querySelector('i');

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(code).then(() => {
                updateButton();
            });
        } else {
            // Fallback for non-secure contexts
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
            const originalText = textSpan.textContent;
            textSpan.textContent = 'Copied!';
            btn.classList.add('text-[#16A34A]');
            
            if (window.lucide) {
                btn.querySelector('i').setAttribute('data-lucide', 'check');
                lucide.createIcons();
            }

            setTimeout(() => {
                textSpan.textContent = originalText;
                btn.classList.remove('text-[#16A34A]');
                if (window.lucide) {
                    btn.querySelector('i').setAttribute('data-lucide', 'copy');
                    lucide.createIcons();
                }
            }, 2000);
        }
    };

    // --- Quiz Utility ---
    window.checkQuiz = function(btn, index) {
        const container = btn.closest('.quiz-container');
        if (container.hasAttribute('data-answered')) return;
        
        const correctIndex = parseInt(container.getAttribute('data-correct-index'));
        const options = container.querySelectorAll('.quiz-option');
        
        container.setAttribute('data-answered', 'true');
        
        options.forEach((opt, idx) => {
            opt.disabled = true;
            opt.classList.remove('hover:border-[#1C1C1C]', 'border-[#E5E5E5]');
            
            if (idx === correctIndex) {
                opt.classList.add('bg-green-100', 'border-green-600', 'text-green-700', 'border-2');
                const checkIcon = document.createElement('i');
                checkIcon.setAttribute('data-lucide', 'check-circle-2');
                checkIcon.classList.add('w-4', 'h-4', 'ml-auto');
                opt.appendChild(checkIcon);
            } else if (idx === index) {
                opt.classList.add('bg-red-100', 'border-red-600', 'text-red-700', 'border-2');
                const xIcon = document.createElement('i');
                xIcon.setAttribute('data-lucide', 'x-circle');
                xIcon.classList.add('w-4', 'h-4', 'ml-auto');
                opt.appendChild(xIcon);
            } else {
                opt.classList.add('opacity-40');
            }
        });

        if (window.lucide) {
            lucide.createIcons();
        }
    };

    if (menuToggle && sidebar && sidebarOverlay) {
        function toggleSidebar() {
            isSidebarOpen = !isSidebarOpen;

            if (isSidebarOpen) {
                sidebar.classList.remove('-translate-x-full');
                sidebarOverlay.classList.remove('opacity-0', 'pointer-events-none');
                menuToggle.innerHTML = '<i data-lucide="x" class="w-5 h-5"></i>';
            } else {
                sidebar.classList.add('-translate-x-full');
                sidebarOverlay.classList.add('opacity-0', 'pointer-events-none');
                menuToggle.innerHTML = '<i data-lucide="menu" class="w-5 h-5"></i>';
            }

            if (window.lucide) {
                lucide.createIcons();
            }
        }

        menuToggle.addEventListener('click', toggleSidebar);
        sidebarOverlay.addEventListener('click', () => { if (isSidebarOpen) toggleSidebar(); });
        
        window.addEventListener('resize', () => {
            if (window.innerWidth >= 1024 && isSidebarOpen) {
                toggleSidebar();
            }
        });
    }
});
