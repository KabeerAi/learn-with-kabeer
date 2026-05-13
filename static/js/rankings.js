/**
 * Learn with Kabeer - Rankings & Leaderboards
 * Logic for UI enhancements and dynamic updates.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Re-initialize Lucide icons if they were dynamically loaded
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // Add smooth reveals for leaderboard rows
    const rows = document.querySelectorAll('.leaderboard-row');
    rows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateY(10px)';
        row.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
        
        setTimeout(() => {
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, 50 * index);
    });
});

/**
 * Switch leaderboard timeframe without full page refresh (Progressive Enhancement)
 * Currently uses standard links, but can be upgraded to AJAX if needed.
 */
function switchTimeframe(period) {
    const url = new URL(window.location);
    url.searchParams.set('timeframe', period);
    window.location.href = url.toString();
}
