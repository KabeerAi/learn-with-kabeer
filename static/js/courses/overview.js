(function initCourseOverviewLoader() {
    const loader = document.getElementById('course-overview-loader');
    if (!loader) return;

    const solidIntroMs = 1000;
    const transparentBehindDelayMs = 720;
    const solidHoldMs = 1800;
    const loadingCompleteMs = 480;
    const solidEaseOutMs = 920;
    const transparentHoldMs = 1400;
    const transparentEndingMs = 1900;
    
    const plates = Array.from(loader.querySelectorAll('img'));
    const solidPlate = loader.querySelector('.course-loader__plate--solid');

    function waitForWindowLoad() {
        if (document.readyState === 'complete') return Promise.resolve();
        return new Promise((resolve) => {
            window.addEventListener('load', resolve, { once: true });
            // Safety timeout for window load
            setTimeout(resolve, 5000);
        });
    }

    function waitForImage(image) {
        if (!image) return Promise.resolve();
        if (image.complete && image.naturalWidth > 0) return Promise.resolve();
        return new Promise((resolve) => {
            let settled = false;
            const finish = () => {
                if (settled) return;
                settled = true;
                resolve();
            };

            image.addEventListener('load', finish, { once: true });
            image.addEventListener('error', finish, { once: true });
            if (typeof image.decode === 'function') {
                image.decode().then(finish).catch(finish);
            }
            // Safety timeout for large image loading
            setTimeout(finish, 4000);
        });
    }

    function delay(ms) {
        return new Promise((resolve) => window.setTimeout(resolve, ms));
    }

    const solidSequence = waitForImage(solidPlate).then(() => {
        loader.classList.add('is-solid-in');

        window.setTimeout(() => {
            loader.classList.add('is-transparent-ready');
        }, transparentBehindDelayMs);

        return delay(solidIntroMs + solidHoldMs);
    });

    Promise.all([
        waitForWindowLoad(),
        Promise.all(plates.map(waitForImage)),
        solidSequence
    ]).then(() => {
        loader.classList.add('is-loaded');
        return delay(loadingCompleteMs);
    }).then(() => {
        document.body.classList.add('course-overview-ready');
        loader.classList.add('is-content-live');
        loader.classList.add('is-solid-exiting');

        return delay(solidEaseOutMs + transparentHoldMs);
    }).then(() => {
        loader.classList.add('is-transparent-ending');

        return delay(transparentEndingMs);
    }).then(() => {
        window.setTimeout(() => {
            loader.remove();
        }, 80);
    });
})();

document.addEventListener("DOMContentLoaded", function() {
    const mapScrollArea = document.getElementById('map-scroll-area');
    if (!mapScrollArea) return;

    // --- 1. Randomize Foreground Sky Clouds Every Page Load ---
    const randomClouds = document.querySelectorAll('.js-random-cloud');
    const cloudAspectRatio = 975 / 1978;

    randomClouds.forEach((cloud, index) => {
        const baseX = parseFloat(cloud.getAttribute('data-base-x'));
        const isTop = (index % 2 === 0);

        cloud.dataset.edge = isTop ? 'top' : 'bottom';
        cloud.dataset.xDrift = Math.random() * 190 - 95;
        cloud.dataset.widthRatio = 0.34 + Math.random() * 0.28;
        cloud.dataset.edgePeek = isTop
            ? 0.2 + Math.random() * 0.2
            : 0.34 + Math.random() * 0.34;

        const scale = 0.88 + Math.random() * 0.3;
        const stretch = 0.9 + Math.random() * 0.2;
        const rotate = Math.random() * 7 - 3.5;
        const edgePeek = parseFloat(cloud.dataset.edgePeek);
        const speed = 0.11 + ((scale - 0.88) * 0.26) + (edgePeek * 0.12) + (Math.random() * 0.04);
        const blur = 3.6 + Math.random() * 2.2;

        cloud.style.setProperty('--x-pos', baseX + parseFloat(cloud.dataset.xDrift));
        cloud.style.setProperty('--target-scale', scale.toFixed(2));
        cloud.style.setProperty('--cloud-stretch', stretch.toFixed(2));
        cloud.style.setProperty('--cloud-rotate', `${rotate.toFixed(1)}deg`);
        cloud.dataset.speed = speed;
        
        const img = cloud.querySelector('.js-random-cloud-img');
        if (img) img.style.filter = `blur(${blur.toFixed(1)}px)`;
    });

    function positionClouds() {
        const mapHeight = mapScrollArea.clientHeight || 700;
        const viewportWidth = mapScrollArea.clientWidth || window.innerWidth || 1200;

        randomClouds.forEach((cloud) => {
            const widthRatio = parseFloat(cloud.dataset.widthRatio) || 0.44;
            const targetScale = parseFloat(cloud.style.getPropertyValue('--target-scale')) || 1;
            const cloudWidth = Math.max(300, Math.min(viewportWidth * widthRatio, 760));
            const visibleHeight = cloudWidth * cloudAspectRatio * targetScale;
            const edgePeek = parseFloat(cloud.dataset.edgePeek) || 0.5;
            const edgeOffset = (edgePeek - 0.5) * visibleHeight;
            const finalY = cloud.dataset.edge === 'top'
                ? edgeOffset
                : mapHeight - edgeOffset;

            cloud.style.setProperty('--cloud-width', `${cloudWidth.toFixed(0)}px`);
            cloud.style.setProperty('--y-pos', finalY.toFixed(0));
        });
    }

    positionClouds();

    let cloudResizeFrame = null;
    window.addEventListener('resize', () => {
        if (cloudResizeFrame) cancelAnimationFrame(cloudResizeFrame);
        cloudResizeFrame = requestAnimationFrame(positionClouds);
    });

    // --- 2. Dynamic Single Blowing Leaf Engine ---
    const leafContainer = document.getElementById('leaf-container');
    const leafGifUrl = window.OVERVIEW_CONFIG.leafGifUrl;
    
    function spawnLeaf() {
        if (!leafContainer) return;
        // Ensure strictly only one leaf at a time
        leafContainer.innerHTML = ''; 
        
        const wrapper = document.createElement('div');
        wrapper.className = "absolute inset-0 w-full h-full pointer-events-none overflow-hidden";
        
        const img = document.createElement('img');
        // Cache-bust the URL to force the GIF animation to restart from frame 1
        img.src = leafGifUrl + "?t=" + new Date().getTime();
        
        // Random blur for depth-of-field (between 3px and 8px)
        const blur = Math.floor(Math.random() * 6) + 3;
        
        img.className = "w-full h-full object-cover transition-opacity duration-300";
        img.style.filter = `blur(${blur}px)`;
        img.style.opacity = '0';
        img.alt = "Blowing Leaf";

        wrapper.appendChild(img);
        leafContainer.appendChild(wrapper);
        
        requestAnimationFrame(() => {
            img.style.opacity = '1';
        });

        const gifDuration = 2300;
        
        setTimeout(() => {
            img.style.opacity = '0';
        }, gifDuration - 300);

        setTimeout(() => {
            wrapper.remove();
            const nextDelay = 10000 + Math.random() * 15000;
            setTimeout(spawnLeaf, nextDelay);
        }, gifDuration);
    }

    if (leafContainer) {
        setTimeout(spawnLeaf, Math.random() * 5000 + 2000);
    }

    // --- 3. Custom Smooth Momentum Scrolling Engine ---
    let targetScroll = 0;
    let currentScroll = 0;
    let isScrolling = false;

    setTimeout(() => {
        targetScroll = mapScrollArea.scrollLeft;
        currentScroll = mapScrollArea.scrollLeft;
    }, 100);

    mapScrollArea.addEventListener('wheel', (evt) => {
        if (Math.abs(evt.deltaX) > Math.abs(evt.deltaY)) return;
        
        evt.preventDefault(); 
        
        const maxScrollLeft = mapScrollArea.scrollWidth - mapScrollArea.clientWidth;
        targetScroll += evt.deltaY * 2.5; 
        targetScroll = Math.max(0, Math.min(targetScroll, maxScrollLeft));

        if (!isScrolling) {
            isScrolling = true;
            requestAnimationFrame(smoothScrollAnimation);
        }
    }, { passive: false });

    function smoothScrollAnimation() {
        const diff = targetScroll - currentScroll;
        
        if (Math.abs(diff) > 0.5) {
            currentScroll += diff * 0.08; 
            mapScrollArea.scrollLeft = currentScroll;
            requestAnimationFrame(smoothScrollAnimation);
        } else {
            currentScroll = targetScroll;
            mapScrollArea.scrollLeft = currentScroll;
            isScrolling = false;
        }
    }
    
    // --- 4. Gentle Parallax Engine for Foreground Sky Clouds ---
    let cloudParallaxFrame = null;
    mapScrollArea.addEventListener('scroll', () => {
        if (cloudParallaxFrame) return;

        cloudParallaxFrame = requestAnimationFrame(() => {
            cloudParallaxFrame = null;
            const scrolled = mapScrollArea.scrollLeft;

            randomClouds.forEach((wrapper) => {
                const speed = parseFloat(wrapper.dataset.speed) || 0.28;
                wrapper.style.setProperty('--parallax-x', `-${scrolled * speed}px`);
            });
        });
    });

    // --- 5. Atmospheric Music Engine ---
    const backgroundMusicMap = {};
    if (window.OVERVIEW_CONFIG && window.OVERVIEW_CONFIG.music) {
        for (const [key, url] of Object.entries(window.OVERVIEW_CONFIG.music)) {
            backgroundMusicMap[key] = new Audio(url);
            backgroundMusicMap[key].loop = true;
            backgroundMusicMap[key].volume = 0;
        }
    }

    let musicFadeTimers = new Map();

    function fadeMusic(audio, targetVolume, duration = 2500) {
        if (musicFadeTimers.has(audio)) {
            clearInterval(musicFadeTimers.get(audio));
        }

        const startVolume = audio.volume;
        const volumeDiff = targetVolume - startVolume;
        const startTime = Date.now();

        if (targetVolume > 0 && audio.paused) {
            audio.play().catch(e => console.log("Autoplay blocked, waiting for interaction"));
        }

        const timer = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);

            audio.volume = startVolume + (volumeDiff * progress);

            if (progress >= 1) {
                clearInterval(timer);
                musicFadeTimers.delete(audio);
                if (targetVolume === 0) {
                    audio.pause();
                }
            }
        }, 50);

        musicFadeTimers.set(audio, timer);
    }

    const stageContainers = document.querySelectorAll('.js-stage-container');
    let currentLandBackground = null;

    function updateAtmosphericMusic() {
        const viewportCenter = mapScrollArea.scrollLeft + (mapScrollArea.clientWidth / 2);
        let activeBackground = null;

        stageContainers.forEach(stage => {
            const left = parseFloat(stage.style.left);
            const width = parseFloat(stage.style.width);
            if (viewportCenter >= left && viewportCenter <= left + width) {
                activeBackground = stage.getAttribute('data-background');
            }
        });

        if (activeBackground !== currentLandBackground) {
            if (currentLandBackground && backgroundMusicMap[currentLandBackground]) {
                fadeMusic(backgroundMusicMap[currentLandBackground], 0);
            }

            if (activeBackground && backgroundMusicMap[activeBackground]) {
                fadeMusic(backgroundMusicMap[activeBackground], 0.4);
            }

            currentLandBackground = activeBackground;
        }
    }

    mapScrollArea.addEventListener('scroll', updateAtmosphericMusic);

    // --- 7. Auto-Scroll to Current Lesson ---
    const currentNode = document.getElementById('current-lesson-node');
    if (currentNode) {
        const targetX = parseInt(currentNode.getAttribute('data-x'));
        const viewportWidth = mapScrollArea.clientWidth;
        
        const centerOffset = targetX - (viewportWidth / 2);
        const maxScroll = mapScrollArea.scrollWidth - viewportWidth;
        const finalScroll = Math.max(0, Math.min(centerOffset, maxScroll));
        
        mapScrollArea.scrollLeft = finalScroll;
        targetScroll = finalScroll;
        currentScroll = finalScroll;
    }

    setTimeout(updateAtmosphericMusic, 1000);

    const unlockAudio = () => {
        updateAtmosphericMusic();
        document.removeEventListener('click', unlockAudio);
        document.removeEventListener('keydown', unlockAudio);
        document.removeEventListener('touchstart', unlockAudio);
    };
    document.addEventListener('click', unlockAudio);
    document.addEventListener('keydown', unlockAudio);
    document.addEventListener('touchstart', unlockAudio);
});
