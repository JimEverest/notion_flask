// 自定义脚本

document.addEventListener('DOMContentLoaded', function() {
    // Toggle 功能
    document.querySelectorAll('.toggle-block .toggle-title').forEach(function(title) {
        title.addEventListener('click', function() {
            const toggleBlock = this.parentElement;
            toggleBlock.classList.toggle('open');
        });
    });
});





document.addEventListener('change', function(event) {
    if (event.target.matches('input[type="checkbox"][data-notion-block-id]')) {
        const blockId = event.target.getAttribute('data-notion-block-id');
        const checked = event.target.checked;

        // Update the text style
        const toDoText = event.target.nextElementSibling;
        if (checked) {
            toDoText.style.textDecoration = 'line-through';
            toDoText.style.color = 'gray';
        } else {
            toDoText.style.textDecoration = 'none';
            toDoText.style.color = 'inherit';
        }

        // Optionally, update the Notion block via an API call
        fetch(`/update_todo/${blockId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': '{{ csrf_token() }}'
            },
            body: JSON.stringify({ checked: checked })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Failed to update to-do block.');
            }
        })
        .catch(error => {
            console.error('Error updating to-do block:', error);
        });
    }
});
