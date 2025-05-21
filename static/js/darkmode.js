document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('toggleDarkMode');
    const icon = toggleBtn.querySelector('i');
    const body = document.body;

    // Función para activar/desactivar
    function applyDarkMode(enable) {
        body.classList.toggle('dark-mode', enable);
        icon.className = enable ? 'bi bi-sun' : 'bi bi-moon';
        localStorage.setItem('darkMode', enable);
    }

    // Aplicar si ya hay preferencia
    const savedMode = localStorage.getItem('darkMode');
    if (savedMode !== null) {
        applyDarkMode(savedMode === 'true');
    } else {
        // Detectar preferencia del sistema
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        applyDarkMode(prefersDark);
    }

    // Al hacer clic en el botón
    toggleBtn.addEventListener('click', () => {
        const isDark = body.classList.contains('dark-mode');
        applyDarkMode(!isDark);
    });
});