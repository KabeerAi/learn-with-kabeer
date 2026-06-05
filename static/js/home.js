document.addEventListener('DOMContentLoaded', () => {
    const hero = document.getElementById('home-hero');
    const video = document.getElementById('home-hero-video');
    const content = document.getElementById('hero-content');
    const scroller = document.querySelector('main');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!hero || !video || !scroller || reduceMotion) return;

    let frame = null;

    const updateParallax = () => {
        const scrollTop = scroller.scrollTop;
        const heroHeight = hero.offsetHeight || 1;
        const progress = Math.min(Math.max(scrollTop / heroHeight, 0), 1);
        
        // Background video moves downward (parallax depth)
        const videoTranslate = progress * 120;
        video.style.transform = `translate3d(0, ${videoTranslate}px, 0)`;

        // Content moves upward (cinematic float)
        if (content) {
            const contentTranslate = progress * -120;
            content.style.transform = `translate3d(0, ${contentTranslate}px, 0)`;
            content.style.opacity = 1 - (progress * 1.4);
        }

        frame = null;
    };

    const requestTick = () => {
        if (frame) return;
        frame = window.requestAnimationFrame(updateParallax);
    };

    updateParallax();
    scroller.addEventListener('scroll', requestTick, { passive: true });
    window.addEventListener('resize', requestTick);
});
