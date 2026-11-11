document.addEventListener('DOMContentLoaded', function () {
    const deleteForms = document.querySelectorAll('form.js-delete-confirmation');
    if (!deleteForms.length) return;

    const modalMarkup = `
        <div class="modal fade" id="deleteConfirmationModal" tabindex="-1" aria-labelledby="deleteConfirmationTitle" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content delete-confirmation-card">
                    <div class="modal-header border-0 pb-0">
                        <div class="delete-confirmation-icon" aria-hidden="true"><i class="bi bi-trash3-fill"></i></div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
                    </div>
                    <div class="modal-body pt-2">
                        <h2 class="modal-title fs-5 mb-2" id="deleteConfirmationTitle">Confirmar eliminación</h2>
                        <p class="mb-0 text-muted" id="deleteConfirmationMessage"></p>
                        <div class="delete-confirmation-warning mt-3"><i class="bi bi-exclamation-triangle-fill me-2" aria-hidden="true"></i>Esta acción no se puede deshacer.</div>
                    </div>
                    <div class="modal-footer border-0 pt-0">
                        <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-danger" id="confirmDeleteButton"><i class="bi bi-trash3 me-2" aria-hidden="true"></i>Eliminar</button>
                    </div>
                </div>
            </div>
        </div>`;

    const style = document.createElement('style');
    style.textContent = `
        #deleteConfirmationModal .delete-confirmation-card { border: 1px solid #e2eaf0; border-radius: 18px; box-shadow: 0 20px 55px rgba(13, 59, 78, .2); }
        #deleteConfirmationModal .modal-header, #deleteConfirmationModal .modal-body, #deleteConfirmationModal .modal-footer { padding-inline: 1.5rem; }
        #deleteConfirmationModal .modal-header { padding-top: 1.35rem; }
        #deleteConfirmationModal .modal-title { color: #163348; font-weight: 750; }
        #deleteConfirmationModal .delete-confirmation-icon { display: grid; width: 48px; height: 48px; place-items: center; border-radius: 14px; background: #fff0ef; color: #c43f3b; font-size: 1.25rem; }
        #deleteConfirmationModal .delete-confirmation-warning { padding: .7rem .85rem; border-radius: 9px; background: #fff8e8; color: #805d17; font-size: .85rem; }
        #deleteConfirmationModal .modal-footer .btn { min-width: 110px; border-radius: 9px; font-weight: 650; }
        @media (max-width: 575.98px) { #deleteConfirmationModal .modal-header, #deleteConfirmationModal .modal-body, #deleteConfirmationModal .modal-footer { padding-inline: 1.1rem; } }
    `;
    document.head.appendChild(style);
    document.body.insertAdjacentHTML('beforeend', modalMarkup);

    const modalElement = document.getElementById('deleteConfirmationModal');
    const modal = window.bootstrap && window.bootstrap.Modal
        ? window.bootstrap.Modal.getOrCreateInstance(modalElement)
        : null;
    const message = document.getElementById('deleteConfirmationMessage');
    const confirmButton = document.getElementById('confirmDeleteButton');
    let pendingForm = null;

    document.addEventListener('submit', function (event) {
        const form = event.target.closest('form.js-delete-confirmation');
        if (!form) return;

        // Captures the event before page-specific handlers and replaces old browser prompts.
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!modal) return;

        pendingForm = form;
        const entity = form.dataset.deleteEntity || 'registro';
        const item = form.dataset.deleteItem || '';
        message.textContent = item
            ? `¿Deseas eliminar el registro de ${entity} “${item}”?`
            : `¿Deseas eliminar este registro de ${entity}?`;
        modal.show();
    }, true);

    confirmButton.addEventListener('click', function () {
        if (!pendingForm) return;
        const form = pendingForm;
        pendingForm = null;
        modal.hide();
        // Native submit skips legacy submit listeners and submits the original POST form.
        HTMLFormElement.prototype.submit.call(form);
    });

    modalElement.addEventListener('hidden.bs.modal', function () {
        pendingForm = null;
    });
});
