document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('courses-container');
    if (!container) return;

    const pathId = container.dataset.pathId;
    new Sortable(container, {
        animation: 200,
        handle: '.course-grip',
        ghostClass: 'sortable-ghost',
        dragClass: 'sortable-drag',
        onEnd: function() {
            const courseIds = Array.from(container.querySelectorAll('.course-item'))
                .map(el => el.dataset.courseId);
            
            fetch(`/admin/career-paths/${pathId}/courses/reorder`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ course_ids: courseIds })
            }).then(res => {
                if (!res.ok) throw new Error("Failed to save reorder");
                
                // Refresh numbering
                container.querySelectorAll('.tabular-nums').forEach((el, idx) => {
                    el.textContent = (idx + 1).toString().padStart(2, '0');
                });
            }).catch(err => {
                alert("Error: " + err.message + ". Please reload the page.");
            });
        }
    });
});
