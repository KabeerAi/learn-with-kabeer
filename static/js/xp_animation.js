/**
 * Learn with Kabeer - Premium XP Reward Animation
 * Redesigned for a minimal, high-end feel (Apple/Vercel/Linear style).
 * Features: Fly-to-destination effect, glassmorphism, and snappier motion.
 */

async function playXpAnimation(awards) {
    if (!awards || awards.length === 0) return;

    // Wait for any loading screens to be removed
    const waitForLoaders = () => {
        return new Promise((resolve) => {
            const check = () => {
                const loaders = document.querySelectorAll('[id*="loader"], [class*="loader"]');
                const activeLoader = Array.from(loaders).find(l => {
                    const style = window.getComputedStyle(l);
                    return style.display !== 'none' && style.visibility !== 'hidden' && l.isConnected;
                });

                if (!activeLoader) {
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    };

    await waitForLoaders();

    const xpPill = document.querySelector('.xp-pill');
    const xpValue = document.querySelector('.xp-value');
    if (!xpPill || !xpValue) return;

    // 1. Fix the "Double Counting" issue
    const totalAwardedXp = awards.reduce((sum, a) => sum + (parseInt(a.xp) || 0), 0);
    const databaseXp = parseInt(xpValue.innerText.replace(/[^0-9]/g, '')) || 0;
    let currentDisplayXp = databaseXp - totalAwardedXp;
    
    // Set initial display to pre-award value so we can animate up
    xpValue.innerText = currentDisplayXp;

    const container = document.createElement('div');
    container.id = 'xp-animation-container';
    container.className = 'fixed inset-0 z-[100] pointer-events-none flex items-center justify-center overflow-hidden';
    document.body.appendChild(container);

    // Play awards in sequence
    for (const award of awards) {
        await showAward(award, container, (addedXp) => {
            const startVal = currentDisplayXp;
            currentDisplayXp += addedXp;
            
            // Animate the number in the header
            animateNumber(xpValue, startVal, currentDisplayXp);
            
            // Subtle pulse on the pill
            xpPill.style.transform = 'scale(1.1)';
            xpPill.style.borderColor = 'rgba(251, 191, 36, 0.5)';
            xpPill.style.boxShadow = '0 0 20px rgba(251, 191, 36, 0.2)';
            
            setTimeout(() => {
                xpPill.style.transform = '';
                xpPill.style.borderColor = '';
                xpPill.style.boxShadow = '';
            }, 600);
        });

        await new Promise(r => setTimeout(r, 150));
    }

    // Ensure we end at exactly what the database says
    xpValue.innerText = databaseXp;
    
    setTimeout(() => container.remove(), 2000);
}

function showAward(award, container, onAddedXp) {
    return new Promise((resolve) => {
        // Create a clean, professional announcement
        const msg = document.createElement('div');
        msg.className = 'absolute flex flex-col items-center transition-all duration-[800ms] ease-premium transform scale-90 opacity-0';
        msg.innerHTML = `
            <div class="relative flex flex-col items-center">
                <div class="flex items-center gap-4 bg-white/80 border border-gray-200 p-2 pr-8 rounded-full shadow-[0_30px_60px_-12px_rgba(0,0,0,0.25)] backdrop-blur-xl">
                    <div class="flex h-11 w-11 items-center justify-center rounded-full bg-[#1C1C1C] text-amber-400 shadow-inner">
                        <i data-lucide="zap" class="w-5 h-5 fill-current"></i>
                    </div>
                    <div class="flex flex-col">
                        <div class="flex items-baseline gap-1.5">
                            <span class="text-2xl font-black text-[#1C1C1C] leading-none tracking-tight">+${award.xp}</span>
                            <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">XP</span>
                        </div>
                        <span class="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em] leading-none mt-1">${award.type}</span>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(msg);
        
        // Initialize icons if lucide is available
        if (window.lucide) {
            window.lucide.createIcons({
                props: { "stroke-width": 3 }
            });
        }

        // Entrance animation
        requestAnimationFrame(() => {
            msg.style.transform = 'scale(1) translateY(0)';
            msg.style.opacity = '1';
        });

        // Small "float" up
        setTimeout(() => {
            msg.style.transform = 'translateY(-15px)';
        }, 1000);

        // Award the XP to the counter after a short delay
        setTimeout(() => {
            onAddedXp(parseInt(award.xp) || 0);
            
            // Fly to pill effect
            const xpPill = document.querySelector('.xp-pill');
            const pillRect = xpPill.getBoundingClientRect();
            const msgRect = msg.getBoundingClientRect();
            
            const deltaX = (pillRect.left + pillRect.width/2) - (msgRect.left + msgRect.width/2);
            const deltaY = (pillRect.top + pillRect.height/2) - (msgRect.top + msgRect.height/2);
            
            msg.className = 'absolute flex flex-col items-center transition-all duration-700 ease-spring transform';
            msg.style.transform = `translate(${deltaX}px, ${deltaY}px) scale(0.1)`;

            msg.style.opacity = '0';
            msg.style.filter = 'blur(10px)';

            setTimeout(() => {
                msg.remove();
                resolve();
            }, 700);
        }, 1800);
    });
}

function animateNumber(el, start, end) {
    const duration = 1000;
    const startTime = performance.now();

    const update = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Smooth ease out
        const easeOutQuart = t => 1 - (--t) * t * t * t;
        const current = Math.floor(start + (end - start) * easeOutQuart(progress));
        
        el.innerText = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            el.innerText = end;
        }
    };

    requestAnimationFrame(update);
}

