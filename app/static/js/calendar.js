/**
 * Script do Painel de Agendamento - Integração com FullCalendar 6.x
 * Implementa visualização mensal e semanal, cliques em datas para novo agendamento,
 * edição e cancelamento de ordens de serviço, e alerta para conflito de disponibilidade de frotas.
 */

let calendar = null;

document.addEventListener('DOMContentLoaded', () => {
  initFullCalendar();
  setupScheduleModalEvents();
  setupCalendarFilters();
  refreshMetrics();
});

// ==============================================================================
// INICIALIZAÇÃO DO FULLCALENDAR 6.X
// ==============================================================================

function initFullCalendar() {
  const calendarEl = document.getElementById('calendar');
  if (!calendarEl) return;

  calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    locale: 'pt-br',
    height: 'auto',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,listWeek'
    },
    buttonText: {
      today: 'Hoje',
      month: 'Mês',
      week: 'Semana',
      list: 'Lista'
    },
    navLinks: true,
    selectable: true,
    editable: false,
    dayMaxEvents: 3,

    // Fonte de eventos dinâmica com passagem de parâmetros dos filtros
    events: function(info, successCallback, failureCallback) {
      const driverFilter = document.getElementById('filterDriver')?.value || '';
      const vehicleFilter = document.getElementById('filterVehicle')?.value || '';
      const statusFilter = document.getElementById('filterStatus')?.value || '';

      const params = new URLSearchParams({
        start: info.startStr,
        end: info.endStr
      });
      if (driverFilter) params.append('driver_id', driverFilter);
      if (vehicleFilter) params.append('vehicle_id', vehicleFilter);
      if (statusFilter) params.append('status', statusFilter);

      fetch(`/api/schedules/calendar?${params.toString()}`)
        .then(response => {
          if (!response.ok) throw new Error('Erro ao carregar eventos da agenda.');
          return response.json();
        })
        .then(events => {
          successCallback(events);
        })
        .catch(err => {
          console.error(err);
          failureCallback(err);
          showToast('Falha ao carregar eventos no calendário.', 'danger');
        });
    },

    // 1. Clique em um dia vazio do calendário: abre modal para novo agendamento
    dateClick: function(info) {
      openScheduleModalForCreate(info.dateStr);
    },

    // 2. Clique em um evento existente: abre modal com dados carregados para edição
    eventClick: function(info) {
      const props = info.event.extendedProps;
      openScheduleModalForEdit(props);
    }
  });

  calendar.render();
}

// ==============================================================================
// CONTROLE DO MODAL DE AGENDAMENTO (CREATE / EDIT / CANCEL)
// ==============================================================================

/**
 * Prepara e abre o modal para um novo agendamento na data clicada.
 */
function openScheduleModalForCreate(dateStr) {
  const modalEl = document.getElementById('scheduleModal');
  const form = document.getElementById('scheduleForm');
  form.reset();

  document.getElementById('scheduleModalTitle').innerHTML = '<i class="bi bi-calendar-plus me-2 text-primary"></i>Novo Agendamento de Serviço';
  document.getElementById('scheduleId').value = '';
  document.getElementById('scheduleDate').value = dateStr;
  document.getElementById('scheduleStatus').value = 'SCHEDULED';

  // Esconde o botão de exclusão
  const btnDelete = document.getElementById('btnDeleteSchedule');
  if (btnDelete) btnDelete.classList.add('d-none');

  // Limpa alertas de conflito
  clearConflictAlert();

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

/**
 * Prepara e abre o modal com os dados de um agendamento já existente.
 */
function openScheduleModalForEdit(props) {
  const modalEl = document.getElementById('scheduleModal');
  const form = document.getElementById('scheduleForm');
  form.reset();

  document.getElementById('scheduleModalTitle').innerHTML = `<i class="bi bi-pencil-square me-2 text-primary"></i>Ordem de Serviço #${props.schedule_id}`;
  document.getElementById('scheduleId').value = props.schedule_id;
  document.getElementById('scheduleDate').value = props.schedule_date;
  document.getElementById('scheduleDriver').value = props.driver_id;
  document.getElementById('scheduleVehicle').value = props.vehicle_id;
  document.getElementById('scheduleClient').value = props.client_name;
  document.getElementById('scheduleAddress').value = props.delivery_address;
  document.getElementById('scheduleOrderNumber').value = props.order_number || '';
  document.getElementById('scheduleNotes').value = props.notes || '';
  document.getElementById('scheduleStatus').value = props.status;

  // Exibe o botão de exclusão
  const btnDelete = document.getElementById('btnDeleteSchedule');
  if (btnDelete) {
    btnDelete.classList.remove('d-none');
    btnDelete.setAttribute('data-id', props.schedule_id);
    btnDelete.setAttribute('data-client', props.client_name);
  }

  clearConflictAlert();

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

/**
 * Exibe mensagem de erro ou conflito destacada no topo do modal.
 */
function showConflictAlert(message) {
  const alertContainer = document.getElementById('scheduleConflictAlert');
  if (!alertContainer) return;
  alertContainer.innerHTML = `
    <div class="alert alert-danger d-flex align-items-center gap-2 mb-3 shadow-sm border-danger" role="alert">
      <i class="bi bi-exclamation-octagon-fill fs-5 flex-shrink-0 text-danger"></i>
      <div><strong>Atenção:</strong> ${escapeHtml(message)}</div>
    </div>
  `;
}

function clearConflictAlert() {
  const alertContainer = document.getElementById('scheduleConflictAlert');
  if (alertContainer) alertContainer.innerHTML = '';
}

/**
 * Configura o envio do formulário de agendamento e botão de exclusão.
 */
function setupScheduleModalEvents() {
  const form = document.getElementById('scheduleForm');
  if (!form) return;

  // Submissão do formulário
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearConflictAlert();

    const scheduleId = document.getElementById('scheduleId').value;
    const scheduleDate = document.getElementById('scheduleDate').value;
    const driverId = document.getElementById('scheduleDriver').value;
    const vehicleId = document.getElementById('scheduleVehicle').value;
    const clientName = document.getElementById('scheduleClient').value.trim();
    const deliveryAddress = document.getElementById('scheduleAddress').value.trim();
    const orderNumber = document.getElementById('scheduleOrderNumber').value.trim();
    const notes = document.getElementById('scheduleNotes').value.trim();
    const status = document.getElementById('scheduleStatus').value;

    if (!scheduleDate || !driverId || !vehicleId || !clientName || !deliveryAddress) {
      showToast('Por favor, preencha todos os campos obrigatórios (*).', 'warning');
      return;
    }

    const saveBtn = document.getElementById('btnSaveSchedule');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Verificando disponibilidade...';

    const payload = {
      schedule_date: scheduleDate,
      driver_id: parseInt(driverId, 10),
      vehicle_id: parseInt(vehicleId, 10),
      client_name: clientName,
      delivery_address: deliveryAddress,
      order_number: orderNumber,
      notes: notes,
      status: status
    };

    try {
      const url = scheduleId ? `/api/schedules/${scheduleId}` : '/api/schedules';
      const method = scheduleId ? 'PUT' : 'POST';

      const response = await apiRequest(url, {
        method,
        body: JSON.stringify(payload)
      });

      showToast(response.message || 'Agendamento registrado com sucesso!', 'success');

      // Fecha o modal
      const modalEl = document.getElementById('scheduleModal');
      bootstrap.Modal.getInstance(modalEl).hide();

      // Atualiza calendário e métricas
      if (calendar) calendar.refetchEvents();
      refreshMetrics();
    } catch (err) {
      if (err.status === 409) {
        // Conflito de escala (motorista ou veículo ocupados na data)
        showConflictAlert(err.message);
        showToast('Conflito detectado na data selecionada.', 'warning');
      } else {
        showToast(err.message || 'Erro ao salvar agendamento.', 'danger');
      }
    } finally {
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i> Confirmar Agendamento';
    }
  });

  // Botão de Excluir Agendamento
  const btnDelete = document.getElementById('btnDeleteSchedule');
  if (btnDelete) {
    btnDelete.addEventListener('click', () => {
      const scheduleId = btnDelete.getAttribute('data-id');
      const client = btnDelete.getAttribute('data-client');

      openConfirmModal({
        title: 'Cancelar / Excluir Agendamento',
        message: `Deseja realmente remover a ordem de serviço para "${client}"?`,
        confirmBtnText: 'Excluir Ordem',
        onConfirm: async () => {
          try {
            const res = await apiRequest(`/api/schedules/${scheduleId}`, { method: 'DELETE' });
            showToast(res.message || 'Agendamento removido.', 'success');

            const modalEl = document.getElementById('scheduleModal');
            bootstrap.Modal.getInstance(modalEl).hide();

            if (calendar) calendar.refetchEvents();
            refreshMetrics();
          } catch (err) {
            showToast(err.message, 'danger');
          }
        }
      });
    });
  }
}

// ==============================================================================
// FILTROS REATIVOS DO CALENDÁRIO
// ==============================================================================

function setupCalendarFilters() {
  const driverFilter = document.getElementById('filterDriver');
  const vehicleFilter = document.getElementById('filterVehicle');
  const statusFilter = document.getElementById('filterStatus');
  const btnResetFilters = document.getElementById('btnResetFilters');

  const onFilterChange = () => {
    if (calendar) calendar.refetchEvents();
  };

  if (driverFilter) driverFilter.addEventListener('change', onFilterChange);
  if (vehicleFilter) vehicleFilter.addEventListener('change', onFilterChange);
  if (statusFilter) statusFilter.addEventListener('change', onFilterChange);

  if (btnResetFilters) {
    btnResetFilters.addEventListener('click', () => {
      if (driverFilter) driverFilter.value = '';
      if (vehicleFilter) vehicleFilter.value = '';
      if (statusFilter) statusFilter.value = '';
      if (calendar) calendar.refetchEvents();
    });
  }
}

// ==============================================================================
// ATUALIZAÇÃO ASSÍNCRONA DE MÉTRICAS OPERACIONAIS
// ==============================================================================

async function refreshMetrics() {
  try {
    const res = await apiRequest('/api/metrics');
    const m = res.data;

    const elTotal = document.getElementById('metricTotal');
    const elToday = document.getElementById('metricToday');
    const elInProgress = document.getElementById('metricInProgress');
    const elCompleted = document.getElementById('metricCompleted');

    if (elTotal) elTotal.textContent = m.total;
    if (elToday) elToday.textContent = m.today;
    if (elInProgress) elInProgress.textContent = m.in_progress;
    if (elCompleted) elCompleted.textContent = m.completed;
  } catch (err) {
    console.error('Falha ao atualizar métricas:', err);
  }
}
