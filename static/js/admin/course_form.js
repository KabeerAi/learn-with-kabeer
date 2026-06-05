document.getElementById('title').addEventListener('input', function() {
    if (!document.querySelector('input[name="course_id"]')) {
        const title = this.value;
        const slug = title.toLowerCase()
            .replace(/[^\w\s-]/g, '') 
            .replace(/\s+/g, '-')     
            .replace(/-+/g, '-')      
            .trim();
        document.getElementById('slug').value = slug;
    }
});
