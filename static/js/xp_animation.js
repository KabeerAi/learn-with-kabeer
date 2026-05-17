/**
 * Learn with Kabeer - Professional XP Award Animation
 * Refactored to be simpler, more professional, and fix visual double-counting.
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
    // The template already renders the NEW XP from the database.
    // To animate from OLD -> NEW, we subtract the awards from the current value.
    const totalAwardedXp = awards.reduce((sum, a) => sum + (parseInt(a.xp) || 0), 0);
    const databaseXp = parseInt(xpValue.innerText.replace(/[^0-9]/g, '')) || 0;
    let currentDisplayXp = databaseXp - totalAwardedXp;
    
    // Set initial display to pre-award value so we can animate up
    xpValue.innerText = currentDisplayXp;

    const container = document.createElement('div');
    container.className = 'fixed inset-0 z-[100] pointer-events-none flex items-center justify-center overflow-hidden transition-all duration-500';
    document.body.appendChild(container);

    // Play awards in sequence
    for (const award of awards) {
        // Subtle background dimming
        container.style.backgroundColor = 'rgba(0, 0, 0, 0.25)';
        container.style.backdropFilter = 'blur(2px)';

        await showAward(award, container, (addedXp) => {
            const startVal = currentDisplayXp;
            currentDisplayXp += addedXp;
            
            // Animate the number in the header
            animateNumber(xpValue, startVal, currentDisplayXp);
            
            // Subtle pulse on the pill
            xpPill.classList.add('scale-110', 'border-amber-400', 'shadow-[0_0_15px_rgba(245,158,11,0.3)]');
            setTimeout(() => {
                xpPill.classList.remove('scale-110', 'border-amber-400', 'shadow-[0_0_15px_rgba(245,158,11,0.3)]');
            }, 500);
        });

        // Clear dimming between awards
        container.style.backgroundColor = 'transparent';
        container.style.backdropFilter = 'blur(0px)';

        await new Promise(r => setTimeout(r, 400));
    }

    // Ensure we end at exactly what the database says
    xpValue.innerText = databaseXp;
    
    setTimeout(() => container.remove(), 1000);
}

function showAward(award, container, onAddedXp) {
    return new Promise((resolve) => {
        // Create a clean, professional announcement
        const msg = document.createElement('div');
        msg.className = 'absolute flex flex-col items-center transition-all duration-700 ease-out transform translate-y-8 opacity-0';
        msg.innerHTML = `
            <div class="relative flex flex-col items-center">
                <!-- Soft Glow -->
                <div class="absolute inset-0 bg-amber-400/10 blur-[40px] rounded-full scale-150"></div>
                
                <div class="relative flex flex-col items-center">
                    <span class="text-[10px] font-bold text-amber-500 uppercase tracking-[0.3em] mb-3">${award.type}</span>
                    <div class="flex items-center gap-4 bg-[#1C1C1C] border border-white/10 px-8 py-4 rounded-2xl shadow-2xl backdrop-blur-xl">
                        <div class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-tr from-amber-400 to-amber-200 text-[#1C1C1C]">
                            <i data-lucide="zap" class="w-5 h-5 fill-current"></i>
                        </div>
                        <div class="flex flex-col">
                            <span class="text-3xl font-black text-white leading-none tracking-tight">+${award.xp}</span>
                            <span class="text-[10px] font-bold text-[#6B6B6B] uppercase tracking-widest mt-1">Experience Points</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(msg);
        
        // Initialize icons if lucide is available
        if (window.lucide) {
            window.lucide.createIcons();
        }

        // Entrance animation
        requestAnimationFrame(() => {
            msg.style.transform = 'translateY(0)';
            msg.style.opacity = '1';
        });

        // Award the XP to the counter after a short delay
        setTimeout(() => {
            onAddedXp(parseInt(award.xp) || 0);
        }, 600);

        // Exit animation
        setTimeout(() => {
            msg.style.transform = 'translateY(-20px)';
            msg.style.opacity = '0';
            setTimeout(() => {
                msg.remove();
                resolve();
            }, 700);
        }, 2200);
    });
}

function animateNumber(el, start, end) {
    const duration = 800;
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
