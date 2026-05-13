/**
 * Learn with Kabeer - Account Settings
 */

function confirmDeletion() {
    const confirmation = confirm("Are you absolutely sure you want to delete your account? This action is permanent and all your progress, XP, and rankings will be lost forever.");
    if (confirmation) {
        document.getElementById('delete-account-form').submit();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Reveal animation for settings groups
    const sections = document.querySelectorAll('.settings-section');
    sections.forEach((section, index) => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(10px)';
        section.style.transition = 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
        
        setTimeout(() => {
            section.style.opacity = '1';
            section.style.transform = 'translateY(0)';
        }, 100 * index);
    });
});
