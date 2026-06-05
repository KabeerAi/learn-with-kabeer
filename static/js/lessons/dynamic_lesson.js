document.addEventListener("DOMContentLoaded", function() {
    initGenerationLoader();
    initSlideNavigation();
});

function initGenerationLoader() {
    const loader = document.getElementById('course-overview-loader');
    if (!loader) return;

    const generateUrl = window.LESSON_CONFIG.generateUrl;
    
    // Start sequence
    setTimeout(() => loader.classList.add('is-solid-in'), 100);
    setTimeout(() => loader.classList.add('is-transparent-ready'), 800);

    async function pollStatus(jobId) {
        const statusUrl = `/lesson/generate/status/${jobId}`;
        try {
            const res = await fetch(statusUrl);
            const data = await res.json();
            
            if (data.status === "complete") {
                return true;
            } else if (data.status === "error") {
                throw new Error(data.error || "Generation failed");
            } else {
                // Still processing, wait and poll again
                await new Promise(resolve => setTimeout(resolve, 2000));
                return pollStatus(jobId);
            }
        } catch (err) {
            throw err;
        }
    }

    // Start generation and poll for results
    fetch(generateUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === "success") {
            // Already exists
            return true;
        } else if (data.status === "processing") {
            // Start polling
            return pollStatus(data.job_id);
        } else {
            throw new Error(data.error || "Failed to start generation");
        }
    })
    .then(() => {
        loader.classList.add('is-loaded');
        setTimeout(() => {
            loader.classList.add('is-solid-exiting');
            setTimeout(() => {
                loader.classList.add('is-transparent-ending');
                setTimeout(() => window.location.reload(), 800);
            }, 920);
        }, 480);
    })
    .catch(err => {
        loader.remove();
        const errorEl = document.getElementById('generation-error');
        if (errorEl) {
            errorEl.classList.remove('hidden');
            document.getElementById('error-message').textContent = err.message || 'A connection error occurred.';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }
    });
}

function initSlideNavigation() {
    const viewport = document.getElementById('slide-viewport');
    const continueBtn = document.getElementById('continue-btn');
    if (!viewport || !continueBtn) return;

    // ─── Step 1: Collect raw block elements ───
    let rawBlocks = Array.from(viewport.querySelectorAll('.lesson-block'));

    // If no builder_json blocks, try legacy content (split by headings)
    if (rawBlocks.length === 0) {
        const legacy = document.getElementById('legacy-content');
        if (legacy) {
            const children = Array.from(legacy.children);
            rawBlocks = children.map(child => {
                const wrapper = document.createElement('div');
                wrapper.className = 'lesson-block w-full';
                const tag = child.tagName || '';
                wrapper.dataset.blockType = /^H[1-6]$/.test(tag) ? 'heading' : 'text';
                wrapper.appendChild(child);
                return wrapper;
            });
            legacy.innerHTML = '';
            rawBlocks.forEach(b => legacy.appendChild(b));
        }
    }

    if (rawBlocks.length === 0) return;

    // ─── Step 2: Group blocks into slides ───
    const slideGroups = [];
    let currentGroup = [];

    rawBlocks.forEach(block => {
        const type = block.dataset.blockType;
        
        if (type === 'separator') {
            if (currentGroup.length > 0) {
                slideGroups.push(currentGroup);
                currentGroup = [];
            }
        } else if (type === 'quiz') {
            if (currentGroup.length > 0) {
                slideGroups.push(currentGroup);
                currentGroup = [];
            }
            slideGroups.push([block]);
        } else if (type === 'heading') {
            if (currentGroup.length > 0) {
                slideGroups.push(currentGroup);
            }
            currentGroup = [block];
        } else {
            currentGroup.push(block);
        }
    });
    if (currentGroup.length > 0) slideGroups.push(currentGroup);

    // If only 1 slide, show everything, no pagination needed
    if (slideGroups.length <= 1) {
        rawBlocks.forEach(b => b.style.display = '');
        const progressFill = document.getElementById('progress-fill');
        if (progressFill) progressFill.style.width = '100%';
        setupSimpleQuizHandlers(rawBlocks, []);
        wireFinalButton();
        return;
    }

    // ─── Step 3: Wrap each group in a slide container ───
    viewport.innerHTML = '';
    const slides = [];

    slideGroups.forEach((group, i) => {
        const slide = document.createElement('div');
        slide.className = 'lesson-slide w-full flex flex-col items-start gap-4';
        slide.style.display = 'none';
        group.forEach(el => slide.appendChild(el));
        viewport.appendChild(slide);
        slides.push(slide);
    });

    // ─── Step 4: Pagination logic ───
    let current = 0;
    let maxReached = 0;
    let prevIndex = 0;
    let quizAnswered = {}; // Track which slides have answered quizzes
    const total = slides.length;
    const backBtn = document.getElementById('back-btn');
    const nextBtn = document.getElementById('next-btn');
    const progressFill = document.getElementById('progress-fill');
    const mainEl = document.getElementById('lesson-main');

    function showSlide(idx) {
        const isGoingForward = idx > prevIndex;
        slides.forEach((s, i) => {
            if (i === idx) {
                s.style.display = 'flex';
                s.classList.remove('slide-enter', 'slide-enter-right', 'slide-exit-left');
                if (isGoingForward) {
                    s.classList.add('slide-enter');
                } else {
                    s.classList.add('slide-enter-right');
                }
                void s.offsetWidth;
            } else {
                s.style.display = 'none';
                s.classList.remove('slide-enter', 'slide-enter-right', 'slide-exit-left');
            }
        });
        prevIndex = idx;

        if (mainEl) mainEl.scrollTop = 0;
        if (progressFill) {
            const progressPercent = ((Math.min(maxReached, total - 1) + 1) / total) * 100;
            progressFill.style.width = progressPercent + '%';
        }
        if (backBtn) backBtn.disabled = idx === 0;
        if (nextBtn) nextBtn.disabled = idx >= maxReached;

        if (typeof lucide !== 'undefined') lucide.createIcons();
        if (typeof Prism !== 'undefined') Prism.highlightAllUnder(slides[idx]);
        
        setupSimpleQuizHandlers(slides, quizAnswered);
        updateContinueButtonState(idx, slides, quizAnswered, total, continueBtn);
    }

    function updateContinueButtonState(idx, slides, quizAnswered, total, continueBtn) {
        const hasQuiz = slides[idx].querySelector('.quiz-option');
        const isAnswered = quizAnswered[idx];
        
        if (hasQuiz && !isAnswered) {
            continueBtn.textContent = 'Select an answer';
            continueBtn.disabled = true;
        } else if (idx === total - 1) {
            if (window.LESSON_CONFIG.isGuest) {
                continueBtn.textContent = "Sign in to Finish";
            } else if (window.LESSON_CONFIG.isLastLesson) {
                continueBtn.textContent = "Complete Course";
                continueBtn.classList.add('bg-16A34A');
            } else {
                continueBtn.textContent = "Finish";
            }
            continueBtn.disabled = false;
        } else {
            continueBtn.textContent = "Continue";
            continueBtn.classList.remove('bg-16A34A');
            continueBtn.disabled = false;
        }
    }

    function setupSimpleQuizHandlers(slides, quizAnswered) {
        document.querySelectorAll('.quiz-option').forEach(option => {
            option.addEventListener('click', function() {
                const slide = this.closest('.lesson-slide') || this.closest('.lesson-block');
                const slideIndex = Array.isArray(slides) ? slides.indexOf(slide) : 0;
                
                // Reset all options in this quiz
                const allOptions = slide.querySelectorAll('.quiz-option');
                allOptions.forEach(opt => {
                    opt.classList.remove('border-green-500', 'bg-green-50', 'border-red-500', 'bg-red-50');
                    opt.classList.add('border-gray-200', 'bg-white');
                });

                // Check if this is correct
                const isCorrect = this.dataset.correct === 'true';
                if (isCorrect) {
                    this.classList.remove('border-gray-200', 'bg-white');
                    this.classList.add('border-green-500', 'bg-green-50');
                } else {
                    this.classList.remove('border-gray-200', 'bg-white');
                    this.classList.add('border-red-500', 'bg-red-50');
                    // Show correct answer
                    allOptions.forEach(opt => {
                        if (opt.dataset.correct === 'true') {
                            opt.classList.remove('border-gray-200', 'bg-white');
                            opt.classList.add('border-green-500', 'bg-green-50');
                        }
                    });
                }

                // Mark quiz as answered
                if (Array.isArray(slides)) {
                    quizAnswered[slideIndex] = true;
                    updateContinueButtonState(slideIndex, slides, quizAnswered, slides.length, continueBtn);
                } else {
                    continueBtn.disabled = false;
                }
            });
        });
    }

    continueBtn.addEventListener('click', function() {
        if (continueBtn.disabled) return;
        
        if (current < total - 1) {
            current++;
            if (current > maxReached) {
                maxReached = current;
            }
            showSlide(current);
        } else {
            doFinalAction();
        }
    });

    if (backBtn) {
        backBtn.addEventListener('click', () => {
            if (current > 0) {
                current--;
                showSlide(current);
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (current < maxReached) {
                current++;
                showSlide(current);
            }
        });
    }

    showSlide(0);

    function doFinalAction() {
        if (window.LESSON_CONFIG.isGuest) {
            window.location.href = window.LESSON_CONFIG.loginUrl;
        } else if (window.LESSON_CONFIG.isCompleted) {
            window.location.href = window.LESSON_CONFIG.nextUrl;
        } else {
            const form = document.getElementById('complete-form');
            if (form) form.submit();
        }
    }

    function wireFinalButton() {
        continueBtn.addEventListener('click', () => {
            if (continueBtn.disabled) return;
            doFinalAction();
        });
    }
}
