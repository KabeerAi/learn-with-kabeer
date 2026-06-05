document.getElementById('title').addEventListener('input', function() {
    // Assuming we add a hidden path_id or check for existence
    if (!document.querySelector('input[name="path_id"]')) { 
        const title = this.value;
        const slug = title.toLowerCase()
            .replace(/[^\w\s-]/g, '') // Remove special characters
            .replace(/\s+/g, '-')     // Replace spaces with -
            .replace(/-+/g, '-')      // Replace multiple - with single -
            .trim();
        document.getElementById('slug').value = slug;
    }
});
