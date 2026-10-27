/**
 * Script Principal da Aplicação - Utilitários Globais, Máscaras e CRUDs
 * Fornece feedback visual assíncrono (Toast), máscaras de input para CPF e Placa,
 * e gerenciamento de modais para Motoristas e Veículos sem recarregamento de página.
 */

document.addEventListener('DOMContentLoaded', () => {
  setupInputMasks();
  setupDriverEvents();
  setupVehicleEvents();
});

// ==============================================================================
// UTILITÁRIO DE NOTIFICAÇÕES (TOAST NOTIFICATIONS)
// ==============================================================================

/**
 * Exibe uma notificação flutuante (Toast) no canto superior direito.
 * @param {string} message - Texto da notificação
 * @param {string} type - 'success' | 'danger' | 'warning' | 'info'
 */
function showToast(message, type = 'success') {
  const toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) return;

  const bgClass = {
    success: 'text-bg-success',
    danger: 'text-bg-danger',
    warning: 'text-bg-warning text-dark',
    info: 'text-bg-info text-dark'
  }[type] || 'text-bg-primary';

  const iconClass = {
    success: 'bi-check-circle-fill',
    danger: 'bi-exclamation-triangle-fill',
    warning: 'bi-exclamation-circle-fill',
    info: 'bi-info-circle-fill'
  }[type] || 'bi-bell-fill';

  const toastEl = document.createElement('div');
  toastEl.className = `toast align-items-center ${bgClass} border-0 shadow-lg mb-2`;
  toastEl.setAttribute('role', 'alert');
  toastEl.setAttribute('aria-live', 'assertive');
  toastEl.setAttribute('aria-atomic', 'true');

  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body d-flex align-items-center gap-2">
        <i class="bi ${iconClass} fs-5"></i>
        <span>${escapeHtml(message)}</span>
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
    </div>
  `;

  toastContainer.appendChild(toastEl);
  const bsToast = new bootstrap.Toast(toastEl, { delay: 4500 });
  bsToast.show();

  toastEl.addEventListener('hidden.bs.toast', () => {
    toastEl.remove();
  });
}

/**
 * Escapa caracteres especiais HTML para prevenir XSS no client-side.
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}

// ==============================================================================
// CLIENTE HTTP PARA API REST (FETCH WRAPPER)
// ==============================================================================

/**
 * Executa requisições assíncronas à API e lida centralizadamente com erros HTTP e conflitos.
 */
async function apiRequest(url, options = {}) {
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  };

  options.headers = { ...defaultHeaders, ...(options.headers || {}) };

  try {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMessage = data.message || `Erro na operação (${response.status})`;
      const error = new Error(errorMessage);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (error) {
    console.error('Falha na requisição API:', error);
    throw error;
  }
}

// ==============================================================================
// MÁSCARAS DE PREENCHIMENTO E SANITIZAÇÃO
// ==============================================================================

/**
 * Aplica máscaras nos campos sensíveis (CPF e Placa de Veículo).
 */
function setupInputMasks() {
  // 1. Máscara de CPF: 000.000.000-00
  document.querySelectorAll('.mask-cpf').forEach(input => {
    input.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v.length > 11) v = v.substring(0, 11);

      if (v.length > 9) {
        v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, '$1.$2.$3-$4');
      } else if (v.length > 6) {
        v = v.replace(/(\d{3})(\d{3})(\d{1,3})/, '$1.$2.$3');
      } else if (v.length > 3) {
        v = v.replace(/(\d{3})(\d{1,3})/, '$1.$2');
      }
      e.target.value = v;
    });
  });

  // 2. Máscara de Placa de Veículo: Converte para maiúsculas e remove caracteres especiais
  document.querySelectorAll('.mask-plate').forEach(input => {
    input.addEventListener('input', (e) => {
      let v = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, '');
      if (v.length > 8) v = v.substring(0, 8);
      e.target.value = v;
    });
  });
}

// ==============================================================================
// MODAL DE CONFIRMAÇÃO GENÉRICO PARA AÇÕES DESTRUTIVAS
// ==============================================================================

let confirmCallback = null;

/**
 * Abre o modal de confirmação para exclusões ou ações críticas.
 */
function openConfirmModal({ title, message, confirmBtnText = 'Confirmar Exclusão', onConfirm }) {
  const modalEl = document.getElementById('genericConfirmModal');
  if (!modalEl) {
    if (confirm(message)) onConfirm();
    return;
  }

  document.getElementById('confirmModalTitle').textContent = title || 'Confirmação';
  document.getElementById('confirmModalBody').textContent = message || 'Tem certeza que deseja prosseguir?';
  const confirmBtn = document.getElementById('confirmModalActionBtn');
  confirmBtn.textContent = confirmBtnText;

  confirmCallback = onConfirm;

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

// Dispara a ação confirmada
const confirmActionBtn = document.getElementById('confirmModalActionBtn');
if (confirmActionBtn) {
  confirmActionBtn.addEventListener('click', () => {
    const modalEl = document.getElementById('genericConfirmModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    if (typeof confirmCallback === 'function') {
      confirmCallback();
      confirmCallback = null;
    }
  });
}

// ==============================================================================
// MÓDULO: GERENCIAMENTO DE MOTORISTAS (DRIVERS)
// ==============================================================================

function setupDriverEvents() {
  const driverForm = document.getElementById('driverForm');
  if (!driverForm) return;

  // Submissão do formulário de criação/edição de motorista
  driverForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const driverId = document.getElementById('driverId').value;
    const name = document.getElementById('driverName').value.trim();
    const taxId = document.getElementById('driverTaxId').value.trim();

    if (!name || name.length < 3) {
      showToast('O nome deve ter no mínimo 3 caracteres.', 'warning');
      return;
    }

    const saveBtn = document.getElementById('driverSaveBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Salvando...';

    try {
      const url = driverId ? `/api/drivers/${driverId}` : '/api/drivers';
      const method = driverId ? 'PUT' : 'POST';

      const response = await apiRequest(url, {
        method,
        body: JSON.stringify({ name, tax_id: taxId })
      });

      showToast(response.message || 'Motorista salvo com sucesso!', 'success');
      
      const modalEl = document.getElementById('driverModal');
      bootstrap.Modal.getInstance(modalEl).hide();

      // Recarrega a listagem ou a tela
      setTimeout(() => window.location.reload(), 700);
    } catch (err) {
      showToast(err.message, 'danger');
    } finally {
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Salvar Motorista';
    }
  });

  // Botões de edição de motorista
  document.querySelectorAll('.btn-edit-driver').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      try {
        const response = await apiRequest(`/api/drivers/${id}`);
        const d = response.data;

        document.getElementById('driverModalTitle').innerText = 'Editar Motorista';
        document.getElementById('driverId').value = d.id;
        document.getElementById('driverName').value = d.name;
        document.getElementById('driverTaxId').value = d.formatted_tax_id || d.tax_id;

        const modal = new bootstrap.Modal(document.getElementById('driverModal'));
        modal.show();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  });

  // Botões de exclusão de motorista
  document.querySelectorAll('.btn-delete-driver').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const name = btn.getAttribute('data-name');

      openConfirmModal({
        title: 'Excluir Motorista',
        message: `Deseja realmente remover o motorista "${name}"? A operação só será permitida se não houver agendamentos ativos vinculados.`,
        confirmBtnText: 'Excluir Motorista',
        onConfirm: async () => {
          try {
            const res = await apiRequest(`/api/drivers/${id}`, { method: 'DELETE' });
            showToast(res.message, 'success');
            setTimeout(() => window.location.reload(), 700);
          } catch (err) {
            showToast(err.message, 'danger');
          }
        }
      });
    });
  });

  // Botão "Novo Motorista" para limpar o formulário
  const btnNewDriver = document.getElementById('btnNewDriver');
  if (btnNewDriver) {
    btnNewDriver.addEventListener('click', () => {
      document.getElementById('driverModalTitle').innerText = 'Cadastrar Novo Motorista';
      document.getElementById('driverForm').reset();
      document.getElementById('driverId').value = '';
    });
  }
}

// ==============================================================================
// MÓDULO: GERENCIAMENTO DE VEÍCULOS (VEHICLES)
// ==============================================================================

function setupVehicleEvents() {
  const vehicleForm = document.getElementById('vehicleForm');
  if (!vehicleForm) return;

  // Submissão do formulário de veículo
  vehicleForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const vehicleId = document.getElementById('vehicleId').value;
    const model = document.getElementById('vehicleModel').value.trim();
    const color = document.getElementById('vehicleColor').value.trim();
    const plate = document.getElementById('vehiclePlate').value.trim();
    const isActive = document.getElementById('vehicleIsActive').checked;

    if (!model || !color || !plate) {
      showToast('Por favor, preencha Modelo, Cor e Placa do veículo.', 'warning');
      return;
    }

    const saveBtn = document.getElementById('vehicleSaveBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Salvando...';

    try {
      const url = vehicleId ? `/api/vehicles/${vehicleId}` : '/api/vehicles';
      const method = vehicleId ? 'PUT' : 'POST';

      const response = await apiRequest(url, {
        method,
        body: JSON.stringify({
          model,
          color,
          license_plate: plate,
          is_active: isActive
        })
      });

      showToast(response.message || 'Veículo salvo com sucesso!', 'success');
      
      const modalEl = document.getElementById('vehicleModal');
      bootstrap.Modal.getInstance(modalEl).hide();

      setTimeout(() => window.location.reload(), 700);
    } catch (err) {
      showToast(err.message, 'danger');
    } finally {
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Salvar Veículo';
    }
  });

  // Botões de edição de veículo
  document.querySelectorAll('.btn-edit-vehicle').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      try {
        const response = await apiRequest(`/api/vehicles/${id}`);
        const v = response.data;

        document.getElementById('vehicleModalTitle').innerText = 'Editar Veículo';
        document.getElementById('vehicleId').value = v.id;
        document.getElementById('vehicleModel').value = v.model;
        document.getElementById('vehicleColor').value = v.color;
        document.getElementById('vehiclePlate').value = v.license_plate || v.raw_license_plate;
        document.getElementById('vehicleIsActive').checked = !!v.is_active;

        const modal = new bootstrap.Modal(document.getElementById('vehicleModal'));
        modal.show();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  });

  // Botões de exclusão de veículo
  document.querySelectorAll('.btn-delete-vehicle').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const model = btn.getAttribute('data-model');
      const plate = btn.getAttribute('data-plate');

      openConfirmModal({
        title: 'Excluir Veículo da Frota',
        message: `Deseja realmente remover o veículo "${model} - ${plate}"? A exclusão só será permitida caso não haja ordens de serviço ativas.`,
        confirmBtnText: 'Excluir Veículo',
        onConfirm: async () => {
          try {
            const res = await apiRequest(`/api/vehicles/${id}`, { method: 'DELETE' });
            showToast(res.message, 'success');
            setTimeout(() => window.location.reload(), 700);
          } catch (err) {
            showToast(err.message, 'danger');
          }
        }
      });
    });
  });

  // Botão "Novo Veículo"
  const btnNewVehicle = document.getElementById('btnNewVehicle');
  if (btnNewVehicle) {
    btnNewVehicle.addEventListener('click', () => {
      document.getElementById('vehicleModalTitle').innerText = 'Cadastrar Novo Veículo';
      document.getElementById('vehicleForm').reset();
      document.getElementById('vehicleId').value = '';
      document.getElementById('vehicleIsActive').checked = true;
    });
  }
}

// Botão para carregar dados de demonstração
const btnSeedDemo = document.getElementById('btnSeedDemo');
if (btnSeedDemo) {
  btnSeedDemo.addEventListener('click', async () => {
    btnSeedDemo.disabled = true;
    btnSeedDemo.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Populando...';
    try {
      const res = await apiRequest('/api/seed?force=true', { method: 'POST' });
      showToast(res.message || 'Dados de demonstração populados!', 'success');
      setTimeout(() => window.location.reload(), 800);
    } catch (err) {
      showToast(err.message, 'danger');
    } finally {
      btnSeedDemo.disabled = false;
      btnSeedDemo.innerHTML = '<i class="bi bi-database-fill-gear me-1"></i> Carregar Dados Demo';
    }
  });
}
