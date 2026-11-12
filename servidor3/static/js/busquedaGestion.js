document.addEventListener('DOMContentLoaded', function () {
    const modules = {
        tablaEmpresas: { placeholder: 'Buscar empresa...', selectors: [] },
        tablaAreas: { placeholder: 'Buscar por área…', selectors: ['.area-nombre'] },
        tablaDepartamentos: { placeholder: 'Buscar por departamento…', selectors: ['.departamento-nombre'] },
        tablaCargos: { placeholder: 'Buscar por área o cargo…', selectors: ['.cargo-area', '.cargo-descripcion'], areaSelector: '.cargo-area', departmentSelector: '.cargo-departamento' },
        tablaUbicaciones: { placeholder: 'Buscar por ubicación…', selectors: ['.ubicacion-descripcion'] },
        tablaColaboradores: { placeholder: 'Buscar por cédula, nombre o cargo…', selectors: ['.col-cedula', '.col-nombre', '.col-cargo'], areaSelector: '.col-area', departmentSelector: '.col-departamento' },
        tablaExtensiones: { placeholder: 'Buscar por nombre o extensión…', selectors: ['.ext-nombre', '.ext-extension'], areaSelector: '.ext-area', departmentSelector: '.ext-departamento' },
        tablaCelulares: { placeholder: 'Buscar por nombre o celular…', selectors: ['.cel-nombre', '.cel-celular'], areaSelector: '.cel-area', departmentSelector: '.cel-departamento' },
        tablaCorreos: { placeholder: 'Buscar por nombre o correo…', selectors: ['.cor-nombre', '.cor-correo'], areaSelector: '.cor-area', departmentSelector: '.cor-departamento' },
        tablaVehiculos: { placeholder: 'Buscar por placa, marca, modelo, color o conductor…' },
        tablaJerarquia: { placeholder: 'Buscar por cargo, superior o planta…', selectors: ['.jerarquia-cargo', '.jerarquia-superior', '.jerarquia-planta'], areaSelector: '.jerarquia-area', departmentSelector: '.jerarquia-departamento' },
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
    const existingSearchInput = null;
    const toolbarSource = existingSearchInput
        || controls.find(control => control.tagName === 'INPUT')
        || container.querySelector('.action-toolbar input[type="search"]');
    if (!toolbarSource) return;

    const toolbar = toolbarSource.closest('.row') || toolbarSource.closest('.d-flex') || toolbarSource.closest('.action-toolbar');
    if (!toolbar) return;
    toolbar.classList.add('crud-search-toolbar');

    const addButton = toolbar.querySelector('.btn-warning, .btn-add');
    const addWrapper = addButton && addButton.closest('.col-auto');
    if (addButton) {
        addButton.classList.add('crud-search-add');
        if (addWrapper) {
            addWrapper.classList.add('crud-search-add-wrapper');
        } else {
            addButton.classList.add('crud-search-add-wrapper');
        }
    }

    controls.forEach(function (control) {
        if (control === existingSearchInput) return;
        const wrapper = control.closest('.col, .col-auto, .col-4, .col-md-6, .col-lg-4, .input-group');
        (wrapper || control).classList.add('d-none');
    });

    let searchInput = existingSearchInput;
    let searchWrapper;
    if (searchInput) {
        searchWrapper = searchInput.closest('.col, .col-auto, .col-4, .col-md-6, .col-lg-4');
        if (searchWrapper) searchWrapper.className = 'crud-search-field';
    } else {
        searchWrapper = document.createElement('div');
        searchWrapper.className = 'crud-search-field';
        searchInput = document.createElement('input');
        searchInput.type = 'search';
        searchInput.className = 'form-control';
        searchInput.autocomplete = 'off';
        searchInput.setAttribute('data-crud-search', 'true');
        searchWrapper.appendChild(searchInput);
        toolbar.insertBefore(searchWrapper, addWrapper || addButton || null);
    }

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

    const areaFilter = module.areaSelector ? createFacetFilter('area', 'Filtrar por Área', module.areaSelector) : null;
    const departmentFilter = module.departmentSelector
        ? createFacetFilter('department', 'Filtrar por departamento', module.departmentSelector)
        : null;

    [departmentFilter, areaFilter].filter(Boolean).forEach(function (filter) {
        const wrapper = document.createElement('div');
        wrapper.className = 'crud-filter-field';
        if (filter.dataset.facet === 'department') {
            wrapper.classList.add('crud-filter-field--department');
        }
        wrapper.appendChild(filter);
        toolbar.insertBefore(wrapper, addWrapper || addButton || null);
    });

    function createFacetFilter(type, placeholder, selector) {
        const select = document.createElement('select');
        select.className = 'form-select crud-facet-filter';
        select.setAttribute('aria-label', `Filtrar por ${type === 'area' ? 'área' : 'departamento'}`);
        select.dataset.facet = type;
        select.dataset.valueSelector = selector;
        select.add(new Option(placeholder, ''));
        return select;
    }

    let emptyResults = container.querySelector('.crud-search-empty') || container.querySelector('#sinResultados');
    if (!emptyResults) {
        emptyResults = document.createElement('div');
        emptyResults.className = 'crud-search-empty d-none';
        emptyResults.innerHTML = '<i class="bi bi-search me-2" aria-hidden="true"></i>No se encontraron registros con ese filtro.';
        table.insertAdjacentElement('afterend', emptyResults);
    }
    emptyResults.classList.add('crud-search-empty');

    let filterData = {};
    let timer;
    let controller;
    let requestId = 0;
    let lastLoadedUrl = new URL(window.location.href).href;

    function readFilters(root) {
        const data = root.querySelector('.gestion-filter-data');
        filterData = data ? JSON.parse(data.textContent) : {};
    }

    function refreshAreas(value) {
        if (!areaFilter) return;
        const department = departmentFilter ? departmentFilter.value : '';
        const areas = department
            ? [...new Set((filterData.relaciones || [])
                .filter(item => item.departamento === department).map(item => item.area))]
            : (filterData.areas || []);
        areaFilter.replaceChildren(new Option('Todas las áreas', ''));
        areas.sort((a, b) => a.localeCompare(b, 'es'))
            .forEach(area => areaFilter.add(new Option(area, area)));
        areaFilter.value = areas.includes(value) ? value : '';
    }

    function syncFilters(url, restoreSearch = false) {
        if (restoreSearch) searchInput.value = url.searchParams.get('q') || '';
        if (departmentFilter) {
            departmentFilter.replaceChildren(new Option('Todos los departamentos', ''));
            (filterData.departamentos || []).forEach(value => departmentFilter.add(new Option(value, value)));
            departmentFilter.value = url.searchParams.get('departamento') || '';
        }
        refreshAreas(url.searchParams.get('area') || '');
    }

    function searchUrl() {
        const url = new URL(window.location.href);
        const values = {
            q: searchInput.value.trim(),
            departamento: departmentFilter ? departmentFilter.value : '',
            area: areaFilter ? areaFilter.value : '',
        };
        Object.entries(values).forEach(([key, value]) => {
            if (value) url.searchParams.set(key, value);
            else url.searchParams.delete(key);
        });
        url.searchParams.delete('page');
        return url;
    }

    function cancelPending() {
        window.clearTimeout(timer);
        if (controller) controller.abort();
        requestId += 1;
    }

    async function loadPage(url, historyMode, restoreSearch = false) {
        cancelPending();
        if (historyMode === 'replace' && url.href === lastLoadedUrl) {
            table.removeAttribute('aria-busy');
            return;
        }
        controller = new AbortController();
        const id = requestId;
        table.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(url, {
                credentials: 'same-origin', signal: controller.signal,
                headers: { Accept: 'text/html' },
            });
            if (id !== requestId) return;
            if (response.status === 401) {
                window.redirigirALoginGestion();
                return;
            }
            if (response.redirected) {
                window.top.location.replace(response.url);
                return;
            }
            if (!response.ok) throw new Error('No se pudo consultar la lista.');
            const html = await response.text();
            if (id !== requestId) return;
            const documentResult = new DOMParser().parseFromString(html, 'text/html');
            const newTable = documentResult.getElementById(table.id);
            const newPagination = documentResult.querySelector('.server-pagination');
            const oldPagination = container.querySelector('.server-pagination');
            if (!newTable || !newPagination || !oldPagination) throw new Error('Respuesta incompleta.');
            // Se conservan los formularios y sus listeners. Las acciones de cada fila
            // conservan sus atributos escapados y la confirmación delegada de borrado.
            table.tBodies[0].replaceWith(document.importNode(newTable.tBodies[0], true));
            oldPagination.replaceWith(document.importNode(newPagination, true));
            // El texto y el cursor pertenecen al usuario mientras escribe.
            // Solo se restauran controles al navegar por el historial.
            if (restoreSearch) {
                readFilters(container);
                syncFilters(new URL(url), true);
            }
            lastLoadedUrl = url.href;
            emptyResults.classList.add('d-none');
            if (historyMode === 'push') history.pushState({}, '', url);
            else if (historyMode === 'replace') history.replaceState({}, '', url);
        } catch (error) {
            if (id === requestId && error.name !== 'AbortError') {
                emptyResults.textContent = 'No se pudieron cargar los resultados. Intenta de nuevo.';
                emptyResults.classList.remove('d-none');
            }
        } finally {
            if (id === requestId) table.removeAttribute('aria-busy');
        }
    }

    searchInput.addEventListener('input', function () {
        cancelPending();
        timer = window.setTimeout(() => loadPage(searchUrl(), 'replace'), 150);
    });
    searchInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            loadPage(searchUrl(), 'replace');
        }
    });
    if (departmentFilter) departmentFilter.addEventListener('change', function () {
        refreshAreas('');
        loadPage(searchUrl(), 'replace');
    });
    if (areaFilter) areaFilter.addEventListener('change', function () {
        loadPage(searchUrl(), 'replace');
    });
    container.addEventListener('click', function (event) {
        const link = event.target.closest('.server-pagination a');
        if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        loadPage(new URL(link.href), 'push');
    });
    window.addEventListener('popstate', function () {
        loadPage(new URL(window.location.href), 'none', true);
    });
    readFilters(container);
    syncFilters(new URL(window.location.href), true);
    emptyResults.classList.add('d-none');
});

