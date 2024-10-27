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
