document.addEventListener('DOMContentLoaded', function () {
    const modules = {
        tablaAreas: { placeholder: 'Buscar por área…', selectors: ['.area-nombre'] },
        tablaDepartamentos: { placeholder: 'Buscar por departamento…', selectors: ['.departamento-nombre'] },
        tablaCargos: { placeholder: 'Buscar por área o cargo…', selectors: ['.cargo-area', '.cargo-descripcion'] },
        tablaUbicaciones: { placeholder: 'Buscar por ubicación…', selectors: ['.ubicacion-descripcion'] },
        tablaColaboradores: { placeholder: 'Buscar por nombre, cargo o ubicación…', selectors: ['.col-nombre', '.col-cargo', '.col-ubicacion'], areaSelector: '.col-area', departmentSelector: '.col-departamento' },
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
    const existingSearchInput = tableElement.id === 'tablaJerarquia'
        ? controls.find(control => control.tagName === 'INPUT')
        : null;
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

    const rows = Array.from(table.querySelectorAll('tbody tr')).filter(function (row) {
        return !row.querySelector('[colspan]');
    });

    function uniqueFacetValues(selector, departmentValue) {
        const values = new Map();
        const departmentKey = normalize(departmentValue || '');
        rows.forEach(function (row) {
            const cell = row.querySelector(selector);
            if (!cell) return;
            if (selector === module.areaSelector && departmentKey) {
                const departmentCell = row.querySelector(module.departmentSelector);
                if (!departmentCell || normalize(departmentCell.textContent) !== departmentKey) return;
            }
            const value = cell.textContent.trim();
            if (value) values.set(normalize(value), value);
        });
        return Array.from(values.values()).sort((left, right) => left.localeCompare(right, 'es'));
    }

    function refreshAreaOptions() {
        if (!areaFilter) return;
        const previousValue = areaFilter.value;
        areaFilter.replaceChildren(new Option('Filtrar por Área', ''));
        uniqueFacetValues(module.areaSelector, departmentFilter ? departmentFilter.value : '')
            .forEach(value => areaFilter.add(new Option(value, value)));
        if (Array.from(areaFilter.options).some(option => normalize(option.value) === normalize(previousValue))) {
            areaFilter.value = previousValue;
        }
    }

    if (departmentFilter) {
        uniqueFacetValues(module.departmentSelector, '').forEach(value => departmentFilter.add(new Option(value, value)));
    }
    refreshAreaOptions();

    const pageSize = 10;
    let currentPage = 1;
    const paginationFooter = document.createElement('div');
    paginationFooter.className = 'crud-pagination-footer';

    const paginationSummary = document.createElement('p');
    paginationSummary.className = 'crud-pagination-summary';
    paginationSummary.setAttribute('aria-live', 'polite');

    const paginationControls = document.createElement('nav');
    paginationControls.className = 'crud-pagination-controls';
    paginationControls.setAttribute('aria-label', 'Paginación de registros');

    paginationFooter.append(paginationSummary, paginationControls);
    const tableContainer = table.closest('.table-responsive') || table;
    tableContainer.insertAdjacentElement('afterend', paginationFooter);

    function normalize(text) {
        return text.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
    }

    function createPageButton(label, page, options) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'crud-page-button';
        button.textContent = label;
        button.disabled = Boolean(options.disabled);
        button.setAttribute('aria-label', options.ariaLabel || `Ir a la página ${page}`);
        if (options.active) {
            button.classList.add('is-active');
            button.setAttribute('aria-current', 'page');
        }
        button.addEventListener('click', function () {
            if (button.disabled || page === currentPage) return;
            currentPage = page;
            filterRows();
        });
        return button;
    }

    function getPageNumbers(totalPages) {
        if (totalPages <= 7) return Array.from({ length: totalPages }, (_, index) => index + 1);

        const pages = new Set([1, totalPages]);
        let start;
        let end;
        if (currentPage <= 4) {
            start = 2;
            end = 5;
        } else if (currentPage >= totalPages - 3) {
            start = totalPages - 4;
            end = totalPages - 1;
        } else {
            start = currentPage - 1;
            end = currentPage + 1;
        }
        for (let page = start; page <= end; page += 1) pages.add(page);
        return Array.from(pages).sort((left, right) => left - right);
    }

    function renderPagination(totalPages, startIndex, endIndex, totalRows) {
        paginationControls.replaceChildren();
        paginationSummary.textContent = totalRows
            ? `Mostrando ${startIndex + 1} - ${endIndex} de ${totalRows} registros`
            : 'Mostrando 0 registros';
        paginationFooter.hidden = totalRows === 0;
        if (totalPages <= 1) return;

        paginationControls.appendChild(createPageButton('‹', Math.max(1, currentPage - 1), {
            disabled: currentPage === 1,
            ariaLabel: 'Página anterior'
        }));

        let previousPage = 0;
        getPageNumbers(totalPages).forEach(function (page) {
            if (previousPage && page - previousPage > 1) {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'crud-page-ellipsis';
                ellipsis.textContent = '…';
                ellipsis.setAttribute('aria-hidden', 'true');
                paginationControls.appendChild(ellipsis);
            }
            paginationControls.appendChild(createPageButton(String(page), page, { active: page === currentPage }));
            previousPage = page;
        });

        paginationControls.appendChild(createPageButton('›', Math.min(totalPages, currentPage + 1), {
            disabled: currentPage === totalPages,
            ariaLabel: 'Página siguiente'
        }));
    }

    function filterRows() {
        const query = normalize(searchInput.value || '');
        const selectedArea = areaFilter ? normalize(areaFilter.value) : '';
        const selectedDepartment = departmentFilter ? normalize(departmentFilter.value) : '';
        const filteredRows = [];
        rows.forEach(function (row) {
            const values = module.selectors
                ? module.selectors.flatMap(selector => Array.from(row.querySelectorAll(selector)).map(cell => cell.textContent))
                : [row.textContent];
            const textMatches = !query || values.some(value => normalize(value).includes(query));
            const areaCell = module.areaSelector ? row.querySelector(module.areaSelector) : null;
            const departmentCell = module.departmentSelector ? row.querySelector(module.departmentSelector) : null;
            const areaMatches = !selectedArea || (areaCell && normalize(areaCell.textContent) === selectedArea);
            const departmentMatches = !selectedDepartment ||
                (departmentCell && normalize(departmentCell.textContent) === selectedDepartment);
            const matches = textMatches && areaMatches && departmentMatches;
            if (matches) filteredRows.push(row);
        });

        const totalPages = Math.ceil(filteredRows.length / pageSize);
        currentPage = totalPages ? Math.min(currentPage, totalPages) : 1;
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = Math.min(startIndex + pageSize, filteredRows.length);
        const currentRows = new Set(filteredRows.slice(startIndex, endIndex));
        rows.forEach(function (row) {
            row.classList.toggle('d-none', !currentRows.has(row));
        });

        const hasActiveFilters = Boolean(query || selectedArea || selectedDepartment);
        emptyResults.classList.toggle('d-none', !hasActiveFilters || filteredRows.length > 0 || rows.length === 0);
        renderPagination(totalPages, startIndex, endIndex, filteredRows.length);
    }

    function resetAndFilter() {
        currentPage = 1;
        filterRows();
    }

    searchInput.addEventListener('input', resetAndFilter);
    if (areaFilter) areaFilter.addEventListener('change', resetAndFilter);
    if (departmentFilter) {
        departmentFilter.addEventListener('change', function () {
            refreshAreaOptions();
            resetAndFilter();
        });
    }
    filterRows();
});
