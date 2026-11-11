/* Autocompletado remoto: mantiene los contratos globales de las pantallas existentes. */
(function () {
  'use strict';

  const timers = new WeakMap();
  const activeRequests = new WeakMap();
  const normalized = value => String(value || '').trim().toLocaleLowerCase();

  function getLookupType(input) {
    const listId = input.getAttribute('list') || '';
    if (listId.startsWith('listaColaboradores')) return 'colaboradores';
    if (listId === 'listaCargos') return 'cargos';
    return null;
  }

  function updateLegacyData(type, items) {
    const target = type === 'cargos' ? window.cargos_info : window.colaboradoresInfo;
    if (!Array.isArray(target)) return;
    target.splice(0, target.length, ...items);
  }

  function populateLists(type, items) {
    const prefix = type === 'cargos' ? 'listaCargos' : 'listaColaboradores';
    document.querySelectorAll(`datalist[id^="${prefix}"]`).forEach(list => {
      const fragment = document.createDocumentFragment();
      items.forEach(item => {
        const option = document.createElement('option');
        option.value = item.nombre || '';
        if (item.id !== undefined) option.dataset.id = String(item.id);
        fragment.appendChild(option);
      });
      list.replaceChildren(fragment);
    });
  }

  function search(input, type) {
    const query = input.value.trim();
    if (query.length < 2) {
      updateLegacyData(type, []);
      input.setCustomValidity('');
      const refresh = new Event('input', { bubbles: true });
      refresh.__lookupRefresh = true;
      input.dispatchEvent(refresh);
      populateLists(type, []);
      return;
    }

    clearTimeout(timers.get(input));
    timers.set(input, setTimeout(async () => {
      const previous = activeRequests.get(input);
      if (previous) previous.abort();
      const controller = new AbortController();
      activeRequests.set(input, controller);
      try {
        const response = await fetch(`/api/lookups/${type}?q=${encodeURIComponent(query)}`, {
          credentials: 'same-origin',
          headers: { Accept: 'application/json' },
          signal: controller.signal
        });
        if (!response.ok) throw new Error('No se pudo completar la búsqueda.');
        const items = await response.json();
        if (input.value.trim() !== query) return;
        updateLegacyData(type, items);
        // Ejecuta la lógica existente de sincronización de ID/área/departamento.
        const refresh = new Event('input', { bubbles: true });
        refresh.__lookupRefresh = true;
        input.dispatchEvent(refresh);
        populateLists(type, items);
        const match = items.find(item => normalized(item.nombre) === normalized(query));
        input.setCustomValidity(query && !match ? 'Selecciona un registro de la lista.' : '');
      } catch (error) {
        if (error.name !== 'AbortError') {
          updateLegacyData(type, []);
          populateLists(type, []);
          input.setCustomValidity('No se pudo buscar. Intenta de nuevo.');
        }
      }
    }, 180));
  }

  document.addEventListener('input', event => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || event.__lookupRefresh) return;
    const type = getLookupType(input);
    if (type) search(input, type);
  });

  document.addEventListener('focusin', event => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) return;
    const type = getLookupType(input);
    if (type && input.value.trim().length >= 2) search(input, type);
  });

  document.addEventListener('change', event => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) return;
    const type = getLookupType(input);
    if (!type) return;
    const items = type === 'cargos' ? window.cargos_info : window.colaboradoresInfo;
    const selected = (items || []).find(item => normalized(item.nombre) === normalized(input.value));
    input.setCustomValidity(input.value && !selected ? 'Selecciona un registro de la lista.' : '');
  });
})();
