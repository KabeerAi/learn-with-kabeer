document.addEventListener('DOMContentLoaded', function() {
    // Initialize Sortable for Sections
    document.querySelectorAll('.sections-container').forEach(container => {
        const courseId = container.dataset.courseId;
        new Sortable(container, {
            animation: 200,
            handle: '.section-grip',
            ghostClass: 'sortable-ghost',
            dragClass: 'sortable-drag',
            onEnd: function() {
                const sectionIds = Array.from(container.querySelectorAll('.section-group'))
                    .map(el => el.dataset.sectionId)
                    .filter(id => id !== 'null');
                
                fetch('/admin/sections/reorder', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ course_id: courseId, section_ids: sectionIds })
                }).then(res => {
                    if (!res.ok) throw new Error("Failed to save section reorder");
                }).catch(err => {
                    alert("Error: " + err.message + ". Please reload the page.");
                });
            }
        });
    });

    // Initialize Sortable for Lessons
    document.querySelectorAll('.lessons-list').forEach(list => {
        new Sortable(list, {
            group: 'lessons',
            animation: 200,
            handle: '.lesson-grip',
            ghostClass: 'sortable-ghost',
            dragClass: 'sortable-drag',
            onEnd: function(evt) {
                const lessonId = evt.item.dataset.lessonId;
                const newSectionId = evt.to.dataset.sectionId;
                const container = evt.to.closest('.sections-container');
                const courseId = container.dataset.courseId;
                
                const lessonIds = Array.from(evt.to.querySelectorAll('[data-lesson-id]'))
                    .map(el => el.dataset.lessonId);

                fetch('/admin/lessons/reorder', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        course_id: courseId, 
                        section_id: newSectionId, 
                        lesson_ids: lessonIds 
                    })
                }).then(res => {
                    if (!res.ok) throw new Error("Failed to save reorder");
                    
                    // Refresh numbering for BOTH lists (source and destination)
                    [evt.from, evt.to].forEach(list => {
                        list.querySelectorAll('.tabular-nums').forEach((el, idx) => {
                            el.textContent = (idx + 1).toString().padStart(2, '0');
                        });
                    });
                    
                    // Update empty states visually
                    document.querySelectorAll('.lessons-list').forEach(l => {
                        const emptyMsg = l.querySelector('.empty-placeholder');
                        const hasLessons = l.querySelectorAll('[data-lesson-id]').length > 0;
                        if (emptyMsg) {
                            emptyMsg.style.display = hasLessons ? 'none' : 'flex';
                        }
                    });
                }).catch(err => {
                    alert("Error: " + err.message + ". Please reload the page.");
                });
            }
        });
    });
});

function openSectionModal() {
    const modal = document.getElementById('section-modal');
    const input = document.getElementById('modal-section-title');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    input.value = '';
    setTimeout(() => input.focus(), 100);
}

function closeSectionModal() {
    const modal = document.getElementById('section-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

function submitSectionModal() {
    const title = document.getElementById('modal-section-title').value.trim();
    const courseId = document.querySelector('.sections-container').dataset.courseId;
    
    if (!title) {
        alert("Please enter a section title.");
        return;
    }

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/admin/courses/${courseId}/sections/new`;
    
    const titleInput = document.createElement('input');
    titleInput.type = 'hidden';
    titleInput.name = 'title';
    titleInput.value = title;
    
    const descInput = document.createElement('input');
    descInput.type = 'hidden';
    descInput.name = 'description';
    descInput.value = '';
    
    form.appendChild(titleInput);
    form.appendChild(descInput);
    document.body.appendChild(form);
    form.submit();
}

function handleAddLesson() {
    const btn = event.currentTarget;
    const sections = document.querySelectorAll('.section-group');
    const hasRealSection = Array.from(sections).some(s => s.dataset.sectionId !== 'null');
    
    if (!hasRealSection) {
        openValidationModal();
    } else {
        window.location.href = btn.dataset.newLessonUrl;
    }
}

function openValidationModal() {
    const modal = document.getElementById('validation-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeValidationModal() {
    const modal = document.getElementById('validation-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

function editSectionTitle(el, sectionId) {
    if (sectionId === 'null') return;
    const currentTitle = el.textContent.trim();
    const currentNumber = el.dataset.number || '1';
    const newTitle = prompt("Edit Section Title:", currentTitle);
    if (newTitle && newTitle !== currentTitle) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/sections/${sectionId}/edit`;
        
        const titleInput = document.createElement('input');
        titleInput.type = 'hidden';
        titleInput.name = 'title';
        titleInput.value = newTitle;
        
        const descInput = document.createElement('input');
        descInput.type = 'hidden';
        descInput.name = 'description';
        descInput.value = ''; 
        
        const numInput = document.createElement('input');
        numInput.type = 'hidden';
        numInput.name = 'number';
        numInput.value = currentNumber;
        
        form.appendChild(titleInput);
        form.appendChild(descInput);
        form.appendChild(numInput);
        document.body.appendChild(form);
        form.submit();
    }
}
