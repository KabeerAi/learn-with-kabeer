let slugManuallyEdited = false;

document.addEventListener("DOMContentLoaded", function() {
    const slugInput = document.getElementById('slug');
    if (slugInput) {
        slugInput.addEventListener('input', function() {
            slugManuallyEdited = true;
        });
    }

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
});

window.autoSlug = function(title) {
    // If it's an edit page (lesson object exists), we might want to skip auto-slugging
    // This logic depends on whether window.IS_EDIT_MODE is set
    if (window.IS_EDIT_MODE) return;
    
    if (slugManuallyEdited) return;
    
    const slug = title.toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
    
    const slugInput = document.getElementById('slug');
    if (slugInput) {
        slugInput.value = slug;
    }
};
