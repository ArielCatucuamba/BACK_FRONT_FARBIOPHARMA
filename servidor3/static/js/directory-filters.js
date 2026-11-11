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

    const rows = Array.from(tbody.querySelectorAll('tr')).filter(row =>
        settings.textFields.every(selector => row.querySelector(selector)) &&
        row.querySelector(settings.areaField) && row.querySelector(settings.departmentField)
    );
    const hasServerPagination = Boolean(document.querySelector('.server-pagination'));
    const pageSize = hasServerPagination ? Math.max(rows.length, 1) : 10;
    let currentPage = 1;
    if (hasServerPagination) summary.closest('.directory-table-footer').hidden = true;

    function normalize(value) {
        return (value || '').toString().normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '').trim().toLocaleLowerCase();
    }

    function buildDepartmentAreaOptions(selectedDepartment, previousArea) {
        const selectedKey = normalize(selectedDepartment);
        const areas = new Map();
        rows.forEach(row => {
            const department = row.querySelector(settings.departmentField).textContent.trim();
            const area = row.querySelector(settings.areaField).textContent.trim();
            if (area && (!selectedKey || normalize(department) === selectedKey)) {
                areas.set(normalize(area), area);
            }
        });

        const options = Array.from(areas.values()).sort((a, b) => a.localeCompare(b, 'es'));
        areaSelect.replaceChildren(new Option('Todas las áreas', ''));
        options.forEach(area => areaSelect.add(new Option(area, area)));
        if (options.some(area => normalize(area) === normalize(previousArea))) {
            areaSelect.value = options.find(area => normalize(area) === normalize(previousArea));
        }
    }

    function getFilteredRows() {
        const query = normalize(search.value);
        const selectedArea = normalize(areaSelect.value);
        const selectedDepartment = normalize(departmentSelect.value);

        return rows.filter(row => {
            const textMatches = settings.textFields.some(selector =>
                normalize(row.querySelector(selector).textContent).includes(query)
            );
            const areaMatches = !selectedArea ||
                normalize(row.querySelector(settings.areaField).textContent) === selectedArea;
            const departmentMatches = !selectedDepartment ||
                normalize(row.querySelector(settings.departmentField).textContent) === selectedDepartment;
            return textMatches && areaMatches && departmentMatches;
        });
    }

    function createPageButton(label, page, options = {}) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'directory-page-button';
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
            render();
        });
        return button;
    }

    function getPageNumbers(totalPages) {
        if (totalPages <= 7) return Array.from({ length: totalPages }, (_, index) => index + 1);

        const pages = new Set([1, totalPages]);
        const start = Math.max(2, Math.min(currentPage - 1, totalPages - 4));
        const end = Math.min(totalPages - 1, Math.max(currentPage + 1, 5));
        for (let page = start; page <= end; page += 1) pages.add(page);
        return Array.from(pages).sort((left, right) => left - right);
    }

    function renderPagination(totalPages) {
        pagination.replaceChildren();
        if (totalPages <= 1) return;

        pagination.appendChild(createPageButton('‹', Math.max(1, currentPage - 1), {
            disabled: currentPage === 1,
            ariaLabel: 'Página anterior'
        }));

        let previousPage = 0;
        getPageNumbers(totalPages).forEach(function (page) {
            if (previousPage && page - previousPage > 1) {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'directory-page-ellipsis';
                ellipsis.textContent = '…';
                ellipsis.setAttribute('aria-hidden', 'true');
                pagination.appendChild(ellipsis);
            }
            pagination.appendChild(createPageButton(String(page), page, { active: page === currentPage }));
            previousPage = page;
        });

        pagination.appendChild(createPageButton('›', Math.min(totalPages, currentPage + 1), {
            disabled: currentPage === totalPages,
            ariaLabel: 'Página siguiente'
        }));
    }

    function render() {
        const filteredRows = getFilteredRows();
        const totalRows = filteredRows.length;
        const totalPages = Math.ceil(totalRows / pageSize);
        currentPage = totalPages ? Math.min(currentPage, totalPages) : 1;
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = Math.min(startIndex + pageSize, totalRows);
        const pageRows = new Set(filteredRows.slice(startIndex, endIndex));

        rows.forEach(row => { row.hidden = !pageRows.has(row); });
        noResults.hidden = totalRows > 0;
        noResults.textContent = settings.emptyText;
        summary.textContent = totalRows
            ? `Mostrando ${startIndex + 1} - ${endIndex} de ${totalRows} registros`
            : 'Mostrando 0 registros';
        summary.closest('.directory-table-footer').hidden = hasServerPagination || totalRows === 0;
        renderPagination(totalPages);
    }

    function resetAndRender() {
        currentPage = 1;
        render();
    }

    buildDepartmentAreaOptions('', '');
    search.addEventListener('input', resetAndRender);
    departmentSelect.addEventListener('change', function () {
        const previousArea = areaSelect.value;
        buildDepartmentAreaOptions(departmentSelect.value, previousArea);
        resetAndRender();
    });
    areaSelect.addEventListener('change', resetAndRender);
    render();
});
