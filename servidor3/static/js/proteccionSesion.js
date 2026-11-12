(function () {
    const script = document.currentScript;
    const root = document.documentElement;
    const sesionUrl = script.dataset.sesionUrl;
    const loginUrl = script.dataset.loginUrl;
    let controller;
    let generation = 0;
    let aviso;

    function ocultar() { root.setAttribute('data-sesion-pendiente', ''); }
    function irAlLogin() {
        ocultar();
        window.top.location.replace(loginUrl);
    }
    window.redirigirALoginGestion = irAlLogin;

    async function comprobar() {
        ocultar();
        if (controller) controller.abort();
        controller = new AbortController();
        const actual = ++generation;
        try {
            const response = await fetch(sesionUrl, {
                credentials: 'same-origin', cache: 'no-store',
                headers: { Accept: 'application/json' }, signal: controller.signal,
            });
            if (actual !== generation) return;
            if (response.status === 401 || response.status === 403) { irAlLogin(); return; }
            if (!response.ok) throw new Error('No se pudo validar la sesión.');
            const sesion = await response.json();
            if (actual !== generation) return;
            if (sesion.autenticado !== true) { irAlLogin(); return; }
            if (aviso) { aviso.remove(); aviso = null; }
            root.removeAttribute('data-sesion-pendiente');
        } catch (error) {
            if (actual !== generation || error.name === 'AbortError') return;
            if (!aviso) {
                aviso = document.createElement('div');
                aviso.setAttribute('role', 'alert');
                aviso.style.cssText = 'visibility:visible;pointer-events:auto;position:fixed;inset:0;z-index:9999;display:grid;place-content:center;gap:16px;padding:24px;background:#f3f6fa;color:#123f56;font-family:Arial,sans-serif;text-align:center';
                const texto = document.createElement('p');
                texto.textContent = 'No se pudo comprobar tu sesión.';
                const boton = document.createElement('button');
                boton.type = 'button';
                boton.textContent = 'Reintentar';
                boton.addEventListener('click', comprobar);
                aviso.append(texto, boton);
                document.body.appendChild(aviso);
            }
        }
    }
    ocultar();
    window.addEventListener('pageshow', comprobar);
    window.addEventListener('pagehide', function () {
        ocultar();
        generation += 1;
        if (controller) controller.abort();
    });
    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') comprobar();
    });
})();
