document.addEventListener('DOMContentLoaded', function () {
    const config = {
        extensiones: {
            tbody: '#tablaExtensiones',
            textFields: ['.ext-nombre', '.ext-extension'],
            areaField: '.ext-area',
            departmentField: '.ext-departamento',
            emptyText: 'No se encontraron extensiones con esos filtros.'
        },
        celulares: {
            tbody: '#tablaCelulares',
            textFields: ['.cel-nombre', '.cel-celular'],
            areaField: '.cel-area',
            departmentField: '.cel-departamento',
            emptyText: 'No se encontraron celulares con esos filtros.'
        },
        correos: {
            tbody: '#tablaCorreos',
            textFields: ['.cor-nombre', '.cor-correo'],
            areaField: '.cor-area',
            departmentField: '.cor-departamento',
            emptyText: 'No se encontraron correos con esos filtros.'
        }
    };

    const page = document.body.dataset.directoryPage;
    const settings = config[page];
    if (!settings) return;

    const tbody = document.querySelector(settings.tbody);
    const search = document.querySelector('[data-filter="search"]');
    const areaSelect = document.querySelector('[data-filter="area"]');
    const departmentSelect = document.querySelector('[data-filter="department"]');
    const noResults = document.querySelector('.directory-no-results');
    const summary = document.querySelector('[data-pagination="summary"]');
    const pagination = document.querySelector('[data-pagination="controls"]');
    if (!tbody || !search || !areaSelect || !departmentSelect || !noResults || !summary || !pagination) return;

    let rows = Array.from(tbody.querySelectorAll('tr')).filter(row =>
        settings.textFields.every(selector => row.querySelector(selector)) &&
        row.querySelector(settings.areaField) && row.querySelector(settings.departmentField)
    );
    const hasServerPagination = search.dataset.globalSearch === 'true';
    function refreshFacetOptions(filters, selectedDepartment, selectedArea) {
        const departmentValues = filters && Array.isArray(filters.departamentos) ? filters.departamentos : [];
        const areaValues = filters && Array.isArray(filters.areas) ? filters.areas : [];
        departmentSelect.replaceChildren(new Option('Todos los departamentos', ''));
        departmentValues.forEach(value => departmentSelect.add(new Option(value, value)));
        areaSelect.replaceChildren(new Option('Todas las áreas', ''));
        areaValues.forEach(value => areaSelect.add(new Option(value, value)));
        departmentSelect.value = departmentValues.includes(selectedDepartment) ? selectedDepartment : '';
        areaSelect.value = areaValues.includes(selectedArea) ? selectedArea : '';
    }

    function render() {
        // El servidor ya aplica los filtros y devuelve hasta 10 registros.
        rows.forEach(row => { row.hidden = false; });
        noResults.hidden = rows.length > 0;
        noResults.textContent = settings.emptyText;
        summary.closest('.directory-table-footer').hidden = true;
    }

    let searchTimer;
    let activeSearchRequest;
    let searchRequestId = 0;
    let lastLoadedUrl = new URL(window.location.href).href;

    function updateRows(items, filters, selectedDepartment, selectedArea, refreshFilters) {
        const cellClasses = [
            ...settings.textFields.map(selector => selector.slice(1)),
            settings.areaField.slice(1),
            settings.departmentField.slice(1),
        ];
        const fragment = document.createDocumentFragment();
        (items || []).forEach(item => {
            const row = document.createElement('tr');
            const values = [item.nombre, item.dato, item.area, item.departamento];
            values.forEach((value, index) => {
                const cell = document.createElement('td');
                cell.className = cellClasses[index];
                cell.textContent = value == null ? '' : String(value);
                row.appendChild(cell);
            });
            fragment.appendChild(row);
        });
        tbody.replaceChildren(fragment);
        rows = Array.from(tbody.querySelectorAll('tr'));
        if (refreshFilters) refreshFacetOptions(filters, selectedDepartment, selectedArea);
        render();
    }

    function requestUrl(displayUrl) {
        const url = new URL(displayUrl, window.location.origin);
        url.searchParams.set('format', 'json');
        return url;
    }

    function attachPageLink(link) {
        link.addEventListener('click', function (event) {
            if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            loadPage(link.href, 'push');
        });
    }

    function renderServerPagination(pageInfo) {
        const container = document.querySelector('.server-pagination');
        if (!container) return;
        const summaryText = container.querySelector('.crud-pagination-summary');
        const controls = container.querySelector('.crud-pagination-controls');
        if (summaryText) {
            summaryText.textContent = pageInfo.total
                ? `Mostrando ${pageInfo.start} - ${pageInfo.end} de ${pageInfo.total} registros`
                : 'Mostrando 0 registros';
        }
        if (!controls) return;

        controls.replaceChildren();
        const addArrow = (label, url, ariaLabel) => {
            if (!url) {
                const disabled = document.createElement('span');
                disabled.className = 'crud-page-button directory-page-button is-disabled';
                disabled.textContent = label;
                disabled.setAttribute('aria-disabled', 'true');
                controls.appendChild(disabled);
                return;
            }
            const link = document.createElement('a');
            link.className = 'crud-page-button directory-page-button';
            link.href = url;
            link.textContent = label;
            link.setAttribute('aria-label', ariaLabel);
            link.rel = label === '‹' ? 'prev' : 'next';
            attachPageLink(link);
            controls.appendChild(link);
        };

        addArrow('‹', pageInfo.previous_url, 'Página anterior');
        (pageInfo.page_links || []).forEach(item => {
            if (item.ellipsis) {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'crud-page-ellipsis directory-page-ellipsis';
                ellipsis.textContent = '…';
                ellipsis.setAttribute('aria-hidden', 'true');
                controls.appendChild(ellipsis);
            } else if (item.page === pageInfo.page) {
                const current = document.createElement('span');
                current.className = 'crud-page-button directory-page-button is-active';
                current.textContent = String(item.page);
                current.setAttribute('aria-current', 'page');
                controls.appendChild(current);
            } else {
                const link = document.createElement('a');
                link.className = 'crud-page-button directory-page-button';
                link.href = item.url;
                link.textContent = String(item.page);
                link.setAttribute('aria-label', `Ir a la página ${item.page}`);
                attachPageLink(link);
                controls.appendChild(link);
            }
        });
        addArrow('›', pageInfo.next_url, 'Página siguiente');
    }

    function cancelPending() {
        window.clearTimeout(searchTimer);
        if (activeSearchRequest) activeSearchRequest.abort();
        searchRequestId += 1;
    }

    async function loadPage(displayUrl, historyMode, refreshFilters = false, restoreSearch = false) {
        cancelPending();
        const targetUrl = new URL(displayUrl, window.location.origin);
        if (historyMode === 'replace' && targetUrl.href === lastLoadedUrl) return;
        const controller = new AbortController();
        activeSearchRequest = controller;
        const requestId = searchRequestId;
        try {
            const response = await fetch(requestUrl(displayUrl), {
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
                signal: controller.signal,
            });
            if (!response.ok) throw new Error('No se pudo buscar en el directorio.');
            const result = await response.json();
            if (requestId !== searchRequestId) return;

            const url = new URL(displayUrl, window.location.origin);
            url.searchParams.delete('format');
            if (restoreSearch) search.value = url.searchParams.get('q') || '';
            const selectedDepartment = url.searchParams.get('departamento') || '';
            const selectedArea = url.searchParams.get('area') || '';
            if (historyMode === 'push') history.pushState({}, '', `${url.pathname}${url.search}`);
            else if (historyMode === 'replace') history.replaceState({}, '', `${url.pathname}${url.search}`);
            updateRows(result.items, result.filters, selectedDepartment, selectedArea, refreshFilters);
            renderServerPagination(result.pagination);
            lastLoadedUrl = url.href;
        } catch (error) {
            if (requestId === searchRequestId && error.name !== 'AbortError') {
                noResults.textContent = 'No se pudo buscar. Intenta de nuevo.';
                noResults.hidden = false;
            }
        }
    }

    function urlForSearch() {
        const url = new URL(window.location.href);
        const termino = search.value.trim();
        const department = departmentSelect.value;
        const area = areaSelect.value;
        if (termino) url.searchParams.set('q', termino);
        else url.searchParams.delete('q');
        if (department) url.searchParams.set('departamento', department);
        else url.searchParams.delete('departamento');
        if (area) url.searchParams.set('area', area);
        else url.searchParams.delete('area');
        url.searchParams.delete('page');
        url.searchParams.delete('format');
        return `${url.pathname}${url.search}`;
    }

    function onSearchInput() {
        if (!hasServerPagination) return;
        cancelPending();
        searchTimer = window.setTimeout(() => loadPage(urlForSearch(), 'replace'), 150);
    }

    function attachInitialPaginationLinks() {
        document.querySelectorAll('.server-pagination a').forEach(attachPageLink);
    }

    attachInitialPaginationLinks();
    search.addEventListener('input', onSearchInput);
    search.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && hasServerPagination) {
            event.preventDefault();
            window.clearTimeout(searchTimer);
            loadPage(urlForSearch(), 'replace');
        }
    });
    departmentSelect.addEventListener('change', function () {
        areaSelect.value = '';
        window.clearTimeout(searchTimer);
        loadPage(urlForSearch(), 'replace', true);
    });
    areaSelect.addEventListener('change', function () {
        window.clearTimeout(searchTimer);
        loadPage(urlForSearch(), 'replace');
    });
    render();
    window.addEventListener('popstate', function () {
        if (hasServerPagination) loadPage(window.location.href, 'none', true, true);
    });
});
