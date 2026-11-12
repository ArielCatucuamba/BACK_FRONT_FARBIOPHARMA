/* El elemento details permite abrir el menú con ratón o teclado sin Bootstrap. */
document.querySelectorAll('[data-menu-usuario]').forEach(function (menu) {
    document.addEventListener('click', function (event) {
        if (!menu.contains(event.target)) menu.open = false;
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && menu.open) {
            menu.open = false;
            menu.querySelector('summary').focus();
            event.preventDefault();
        }
    });
    window.addEventListener('blur', function () { menu.open = false; });
});
