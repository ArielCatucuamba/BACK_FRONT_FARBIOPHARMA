document.addEventListener('DOMContentLoaded', function () {
    const modules = {
        tablaAreas: { placeholder: 'Buscar por área…', selectors: ['.area-nombre'] },
        tablaDepartamentos: { placeholder: 'Buscar por departamento…', selectors: ['.departamento-nombre'] },
        tablaCargos: { placeholder: 'Buscar por área o cargo…', selectors: ['.cargo-area', '.cargo-descripcion'] },
        tablaUbicaciones: { placeholder: 'Buscar por ubicación…', selectors: ['.ubicacion-descripcion'] },
        tablaColaboradores: { placeholder: 'Buscar por área o nombre…', selectors: ['.col-area', '.col-nombre'] },
        tablaExtensiones: { placeholder: 'Buscar por área o nombre…', selectors: ['.ext-area', '.ext-nombre'] },
        tablaCelulares: { placeholder: 'Buscar por área o nombre…', selectors: ['.cel-area', '.cel-nombre'] },
        tablaCorreos: { placeholder: 'Buscar por área o nombre…', selectors: ['.cor-area', '.cor-nombre'] },
        tablaVehiculos: { placeholder: 'Buscar por placa, marca, modelo, color o conductor…' },
        tablaJerarquia: { placeholder: 'Buscar por cargo, superior, departamento, área o planta…' },
        tablaDirectorioExtensiones: { placeholder: 'Buscar por nombre, extensión, área o departamento…', selectors: ['.ext-nombre', '.ext-extension', '.ext-area', '.ext-departamento'] },
        tablaDirectorioCelulares: { placeholder: 'Buscar por nombre, celular, área o departamento…', selectors: ['.cel-nombre', '.cel-celular', '.cel-area', '.cel-departamento'] },
        tablaDirectorioCorreos: { placeholder: 'Buscar por nombre, correo, área o departamento…', selectors: ['.cor-nombre', '.cor-correo', '.cor-area', '.cor-departamento'] }
    };

    let tableElement;
    let module;
    for (const [tableId, settings] of Object.entries(modules)) {
        tableElement = document.getElementById(tableId);
        if (tableElement) {
            module = settings;
            break;
        }
    }
    if (!tableElement) return;

    if (tableElement.tagName.toLowerCase() !== 'table') {
        const directorySettings = {
            tablaExtensiones: modules.tablaDirectorioExtensiones,
            tablaCelulares: modules.tablaDirectorioCelulares,
            tablaCorreos: modules.tablaDirectorioCorreos
        };
        module = directorySettings[tableElement.id] || module;
    }

    const table = tableElement.matches('table') ? tableElement : tableElement.closest('table');
    if (!table) return;
    const container = document.querySelector('body > .container.mt-5')
        || document.querySelector('body > main.page-shell')
        || document.querySelector('.main-content');
    if (!container) return;

    const controls = Array.from(container.querySelectorAll('input[id^="filtro"], select[id^="filtro"]'));
    const searchInput = controls.find(control => control.tagName === 'INPUT')
        || container.querySelector('.action-toolbar input[type="search"]');
    if (!searchInput) return;

    const toolbar = searchInput.closest('.row') || searchInput.closest('.d-flex') || searchInput.closest('.action-toolbar');
    if (!toolbar) return;
    toolbar.classList.add('crud-search-toolbar');

    const addButton = toolbar.querySelector('.btn-warning, .btn-add');
    if (addButton) {
        addButton.classList.add('crud-search-add');
        const addWrapper = addButton.closest('.col-auto');
        if (addWrapper) addWrapper.classList.add('crud-search-add-wrapper');
    }

    controls.forEach(function (control) {
        if (control === searchInput) return;
        const wrapper = control.closest('.col, .col-auto, .col-4, .col-md-6, .col-lg-4');
        (wrapper || control).classList.add('d-none');
    });

    const searchWrapper = searchInput.closest('.col, .col-auto, .col-4, .col-md-6, .col-lg-4');
    if (searchWrapper) searchWrapper.className = 'crud-search-field';
    searchInput.type = 'search';
    searchInput.removeAttribute('list');
    searchInput.setAttribute('aria-label', module.placeholder.replace(/…$/, ''));
    searchInput.setAttribute('placeholder', module.placeholder);
    searchInput.classList.add('crud-search-input');

    let inputGroup = searchInput.closest('.input-group');
    if (!inputGroup) {
        inputGroup = document.createElement('div');
        inputGroup.className = 'input-group';
        searchInput.parentNode.insertBefore(inputGroup, searchInput);
        inputGroup.appendChild(searchInput);
    }
    const existingIcon = inputGroup.querySelector('.input-group-text');
    if (existingIcon) {
        existingIcon.classList.add('crud-search-icon');
    } else {
        const icon = document.createElement('span');
        icon.className = 'input-group-text crud-search-icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.innerHTML = '<i class="bi bi-search"></i>';
        inputGroup.insertBefore(icon, searchInput);
    }

    let emptyResults = container.querySelector('.crud-search-empty') || container.querySelector('#sinResultados');
    if (!emptyResults) {
        emptyResults = document.createElement('div');
        emptyResults.className = 'crud-search-empty d-none';
        emptyResults.innerHTML = '<i class="bi bi-search me-2" aria-hidden="true"></i>No se encontraron registros con ese filtro.';
        table.insertAdjacentElement('afterend', emptyResults);
    }
    emptyResults.classList.add('crud-search-empty');

    const rows = Array.from(table.querySelectorAll('tbody tr')).filter(function (row) {
        return !row.querySelector('[colspan]');
    });

    function normalize(text) {
        return text.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
    }

    function filterRows() {
        const query = normalize(searchInput.value || '');
        let visible = 0;
        rows.forEach(function (row) {
            const values = module.selectors
                ? module.selectors.flatMap(selector => Array.from(row.querySelectorAll(selector)).map(cell => cell.textContent))
                : [row.textContent];
            const matches = !query || values.some(value => normalize(value).includes(query));
            row.classList.toggle('d-none', !matches);
            if (matches) visible += 1;
        });
        emptyResults.classList.toggle('d-none', !query || visible > 0 || rows.length === 0);
    }

    searchInput.addEventListener('input', filterRows);
    filterRows();
});
