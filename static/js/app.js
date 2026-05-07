// ============================================================
// CONFIGURACIÓN Y ESTADO GLOBAL
// ============================================================
const API = '';  // URL base (vacío = misma origen)
let token = localStorage.getItem('token') || null;
let docenteData = JSON.parse(localStorage.getItem('docente') || 'null');
let asignaciones = [];

// ============================================================
// INICIALIZACIÓN
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  if (token && docenteData) {
    mostrarApp();
  }
});

// ============================================================
// HELPERS DE API
// ============================================================
async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.body instanceof FormData) delete headers['Content-Type'];

  const res = await fetch(API + path, { ...options, headers: { ...headers, ...options.headers } });

  if (res.status === 401) {
    logout();
    return null;
  }

  const data = res.status === 204 ? null : await res.json();
  if (!res.ok) throw new Error(data?.detail || 'Error en la solicitud');
  return data;
}

// ============================================================
// AUTH
// ============================================================
function showAuthTab(tab) {
  document.getElementById('login-form').style.display = tab === 'login' ? 'block' : 'none';
  document.getElementById('registro-form').style.display = tab === 'registro' ? 'block' : 'none';
  document.querySelectorAll('.tab-auth .tab-btn').forEach((b, i) => {
    b.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'registro'));
  });
  document.getElementById('auth-error').style.display = 'none';
}

async function login() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  try {
    const data = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    token = data.access_token;
    docenteData = { id: data.docente_id, nombre: data.nombre, email: data.email };
    localStorage.setItem('token', token);
    localStorage.setItem('docente', JSON.stringify(docenteData));
    mostrarApp();
  } catch (e) {
    showError('auth-error', e.message);
  }
}

async function registro() {
  const nombre = document.getElementById('reg-nombre').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  try {
    await apiFetch('/api/auth/registro', {
      method: 'POST',
      body: JSON.stringify({ nombre, email, password }),
    });
    showAuthTab('login');
    document.getElementById('login-email').value = email;
    showError('auth-error', '✅ Cuenta creada. Podés ingresar ahora.');
    document.getElementById('auth-error').style.color = 'var(--success)';
  } catch (e) {
    showError('auth-error', e.message);
  }
}

function logout() {
  token = null;
  docenteData = null;
  localStorage.removeItem('token');
  localStorage.removeItem('docente');
  document.getElementById('auth-section').style.display = 'flex';
  document.getElementById('app-section').style.display = 'none';
}

// ============================================================
// MOSTRAR APP Y CARGAR DATOS INICIALES
// ============================================================
async function mostrarApp() {
  document.getElementById('auth-section').style.display = 'none';
  document.getElementById('app-section').style.display = 'block';
  document.getElementById('header-nombre').textContent = docenteData?.nombre || '';

  // Cargar datos iniciales
  await cargarGrupos();
  await cargarAsignaciones();
  await cargarArchivos();
  cargarPerfil();
  poblarSelectsAsignaciones();
}

// ============================================================
// NAVEGACIÓN DE TABS
// ============================================================
function showTab(tab) {
  document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
  document.querySelectorAll('.main-tab').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-${tab}`).style.display = 'block';
  event.target.classList.add('active');

  if (tab === 'desarrollo') cargarDesarrollos();
}

function showSubTab(prefix, tab) {
  const parent = document.getElementById(`tab-${prefix === 'config' ? 'config' : 'planificaciones'}`);
  parent.querySelectorAll('.subtab-content').forEach(t => t.style.display = 'none');
  parent.querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
  document.getElementById(`subtab-${prefix}-${tab}`).style.display = 'block';
  event.target.classList.add('active');
}

// ============================================================
// GRUPOS
// ============================================================
async function cargarGrupos() {
  try {
    const grupos = await apiFetch('/api/config/grupos');
    const el = document.getElementById('lista-grupos');
    if (!grupos.length) {
      el.innerHTML = '<p class="empty-state">No tenés grupos registrados todavía.</p>';
      return;
    }
    el.innerHTML = grupos.map(g => `
      <div class="card">
        <h3>📚 ${g.nombre}</h3>
        <p>📅 Año: ${g.anio}</p>
        <p>🏫 ${g.institucion}</p>
        <div class="card-actions">
          <button class="btn-danger" onclick="eliminarGrupo('${g.id}')">Eliminar</button>
        </div>
      </div>
    `).join('');

    // Poblar select de grupos en modal asignación
    const sel = document.getElementById('asig-grupo-id');
    sel.innerHTML = grupos.map(g => `<option value="${g.id}">${g.nombre} - ${g.anio}</option>`).join('');
  } catch (e) {
    console.error(e);
  }
}

async function crearGrupo() {
  const nombre = document.getElementById('grupo-nombre').value.trim();
  const anio = document.getElementById('grupo-anio').value.trim();
  const institucion = document.getElementById('grupo-institucion').value.trim();
  try {
    await apiFetch('/api/config/grupos', {
      method: 'POST',
      body: JSON.stringify({ nombre, anio, institucion }),
    });
    hideModal('modal-grupo');
    await cargarGrupos();
    await cargarAsignaciones();
  } catch (e) {
    showError('grupo-error', e.message);
  }
}

async function eliminarGrupo(id) {
  if (!confirm('¿Eliminar este grupo y todas sus asignaciones?')) return;
  try {
    await apiFetch(`/api/config/grupos/${id}`, { method: 'DELETE' });
    await cargarGrupos();
    await cargarAsignaciones();
  } catch (e) {
    alert(e.message);
  }
}

// ============================================================
// ASIGNACIONES
// ============================================================
async function cargarAsignaciones() {
  try {
    asignaciones = await apiFetch('/api/config/asignaciones');
    const el = document.getElementById('lista-asignaciones');
    if (!asignaciones.length) {
      el.innerHTML = '<p class="empty-state">No tenés asignaciones registradas todavía.</p>';
      return;
    }
    el.innerHTML = asignaciones.map(a => {
      const horario = a.horario.filter(h => h.bloques > 0)
        .map(h => `${h.dia}: ${h.bloques} bloque(s)`).join(' · ');
      return `
        <div class="card">
          <h3>📖 ${a.materia}</h3>
          <p>👥 ${a.grupo_nombre} (${a.grupo_anio})</p>
          <p>🏫 ${a.grupo_institucion}</p>
          <p>⏱ ${a.minutos_por_hora_docente} min/hora docente</p>
          <p>📅 ${horario}</p>
          <p>🕐 Total: ${a.total_horas_docentes_semanales} horas/semana (${a.total_minutos_semanales} min)</p>
          <div class="card-actions">
            <button class="btn-danger" onclick="eliminarAsignacion('${a.id}')">Eliminar</button>
          </div>
        </div>
      `;
    }).join('');

    poblarSelectsAsignaciones();
  } catch (e) {
    console.error(e);
  }
}

async function crearAsignacion() {
  const grupo_id = document.getElementById('asig-grupo-id').value;
  const materia = document.getElementById('asig-materia').value.trim();
  const minutos = parseInt(document.getElementById('asig-minutos').value);

  // Leer horario
  const horario = [];
  document.querySelectorAll('.horario-input').forEach(input => {
    const bloques = parseInt(input.value) || 0;
    if (bloques > 0) {
      horario.push({ dia: input.dataset.dia, bloques });
    }
  });

  if (!horario.length) {
    showError('asig-error', 'Debés especificar al menos un día con bloques.');
    return;
  }

  try {
    await apiFetch('/api/config/asignaciones', {
      method: 'POST',
      body: JSON.stringify({ grupo_id, materia, horario, minutos_por_hora_docente: minutos }),
    });
    hideModal('modal-asignacion');
    await cargarAsignaciones();

    // Resetear horario
    document.querySelectorAll('.horario-input').forEach(i => i.value = 0);
  } catch (e) {
    showError('asig-error', e.message);
  }
}

async function eliminarAsignacion(id) {
  if (!confirm('¿Eliminar esta asignación y todas sus planificaciones?')) return;
  try {
    await apiFetch(`/api/config/asignaciones/${id}`, { method: 'DELETE' });
    await cargarAsignaciones();
  } catch (e) {
    alert(e.message);
  }
}

function poblarSelectsAsignaciones() {
  const selects = [
    'plan-anual-asignacion',
    'plan-unidad-asignacion',
    'plan-diaria-asignacion',
    'desarrollo-asignacion',
    'archivo-asignacion',
  ];
  const options = asignaciones.map(a =>
    `<option value="${a.id}">${a.grupo_nombre} - ${a.materia}</option>`
  ).join('');

  selects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const esArchivo = id === 'archivo-asignacion';
    el.innerHTML = (esArchivo ? '<option value="">Global (todas las asignaciones)</option>' : '') + options;
  });
}

// ============================================================
// ARCHIVOS
// ============================================================
async function cargarArchivos() {
  try {
    const archivos = await apiFetch('/api/config/archivos');
    const el = document.getElementById('lista-archivos');
    if (!archivos.length) {
      el.innerHTML = '<p class="empty-state">No hay archivos subidos todavía.</p>';
      return;
    }
    el.innerHTML = archivos.map(a => `
      <div class="card">
        <h3>📄 ${a.nombre}</h3>
        <p>Tipo: ${a.tipo}</p>
        <p>Tamaño: ${a.tamanio_bytes ? Math.round(a.tamanio_bytes / 1024) + ' KB' : 'N/D'}</p>
        <div class="card-actions">
          <a href="${a.storage_url}" target="_blank" class="btn-secondary">Ver</a>
          <button class="btn-danger" onclick="eliminarArchivo('${a.id}')">Eliminar</button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    console.error(e);
  }
}

async function subirArchivo() {
  const tipo = document.getElementById('archivo-tipo').value;
  const asignacion_id = document.getElementById('archivo-asignacion').value;
  const fileInput = document.getElementById('archivo-file');
  const status = document.getElementById('upload-status');

  if (!fileInput.files.length) {
    alert('Seleccioná un archivo primero.');
    return;
  }

  const formData = new FormData();
  formData.append('archivo', fileInput.files[0]);
  formData.append('tipo', tipo);
  if (asignacion_id) formData.append('asignacion_id', asignacion_id);

  status.style.display = 'block';
  status.textContent = '⏳ Subiendo archivo...';

  try {
    await apiFetch('/api/config/archivos', { method: 'POST', body: formData });
    status.textContent = '✅ Archivo subido correctamente.';
    fileInput.value = '';
    await cargarArchivos();
  } catch (e) {
    status.textContent = '❌ Error: ' + e.message;
    status.style.color = 'var(--danger)';
  }
}

async function eliminarArchivo(id) {
  if (!confirm('¿Eliminar este archivo?')) return;
  try {
    await apiFetch(`/api/config/archivos/${id}`, { method: 'DELETE' });
    await cargarArchivos();
  } catch (e) {
    alert(e.message);
  }
}

// ============================================================
// PERFIL
// ============================================================
async function cargarPerfil() {
  try {
    const me = await apiFetch('/api/auth/me');
    document.getElementById('perfil-data').innerHTML = `
      <p><strong>Nombre:</strong> ${me.nombre}</p>
      <p><strong>Email:</strong> ${me.email}</p>
      <p><strong>Telegram:</strong> ${me.telegram_chat_id ? '✅ Vinculado (chat_id: ' + me.telegram_chat_id + ')' : '❌ No vinculado'}</p>
    `;
  } catch (e) {
    console.error(e);
  }
}

async function vincularTelegram() {
  const chat_id = parseInt(document.getElementById('telegram-chat-id').value);
  const status = document.getElementById('telegram-status');
  try {
    await apiFetch('/api/auth/vincular-telegram', {
      method: 'PATCH',
      body: JSON.stringify({ telegram_chat_id: chat_id }),
    });
    status.style.display = 'block';
    status.textContent = '✅ Telegram vinculado correctamente.';
    cargarPerfil();
  } catch (e) {
    status.style.display = 'block';
    status.textContent = '❌ ' + e.message;
    status.style.background = '#fef2f2';
    status.style.color = 'var(--danger)';
  }
}

// ============================================================
// PLANIFICACIÓN ANUAL
// ============================================================
async function generarPlanAnual() {
  const asignacion_id = document.getElementById('plan-anual-asignacion').value;
  const semanas_lectivas = parseInt(document.getElementById('plan-anual-semanas').value);
  const porcentaje_emergentes = parseInt(document.getElementById('plan-anual-emergentes').value);
  const directivas = document.getElementById('plan-anual-directivas').value;

  const loading = document.getElementById('plan-anual-loading');
  const resultado = document.getElementById('resultado-plan-anual');

  loading.style.display = 'block';
  resultado.innerHTML = '';

  try {
    const data = await apiFetch('/api/planificaciones/anual', {
      method: 'POST',
      body: JSON.stringify({ asignacion_id, semanas_lectivas, porcentaje_emergentes, directivas }),
    });
    loading.style.display = 'none';
    renderPlanAnual(data, resultado);
  } catch (e) {
    loading.style.display = 'none';
    resultado.innerHTML = `<p class="error-msg">❌ ${e.message}</p>`;
  }
}

function renderPlanAnual(data, container) {
  const c = data.contenido;
  if (c.error) {
    container.innerHTML = `<p class="error-msg">❌ Error en la respuesta de Gemini: ${c.error}</p>`;
    return;
  }

  const objetivos = (c.objetivos_generales || []).map(o => `<li>${o}</li>`).join('');
  const unidades = (c.unidades || []).map(u => `
    <div class="unidad-card">
      <h4>${u.orden}. ${u.titulo}</h4>
      <p>📚 ${u.descripcion || ''}</p>
      <p>⏱ <strong>${u.horas_docentes}</strong> horas docentes</p>
      <ul>${(u.objetivos_especificos || []).map(o => `<li>${o}</li>`).join('')}</ul>
      <ul>${(u.contenidos || []).map(c => `<li>${c}</li>`).join('')}</ul>
    </div>
  `).join('');

  container.innerHTML = `
    <div class="resultado-planif">
      <h3>✨ Planificación Anual generada</h3>
      <p>📅 ${c.semanas_lectivas} semanas · ${c.total_horas_anuales} horas totales · ${c.horas_emergentes} para emergentes</p>
      <h4 style="margin: 16px 0 8px">Objetivos generales:</h4>
      <ul style="margin-left: 18px; font-size: 14px">${objetivos}</ul>
      <h4 style="margin: 16px 0 8px">Unidades (${(c.unidades || []).length}):</h4>
      ${unidades}
      <button class="btn-secondary" style="margin-top: 16px" onclick="aprobarPlanificacion('${data.id}')">
        ✅ Marcar como vigente
      </button>
    </div>
  `;
}

// ============================================================
// PLANIFICACIÓN POR UNIDAD
// ============================================================
function toggleEvaluacion() {
  const checked = document.getElementById('plan-unidad-evaluacion').checked;
  document.getElementById('tipo-evaluacion-container').style.display = checked ? 'block' : 'none';
}

async function generarPlanUnidad() {
  const asignacion_id = document.getElementById('plan-unidad-asignacion').value;
  const titulo_unidad = document.getElementById('plan-unidad-titulo').value.trim();
  const horas_docentes = parseInt(document.getElementById('plan-unidad-horas').value);
  const porcentaje_emergentes = parseInt(document.getElementById('plan-unidad-emergentes').value);
  const incluir_evaluacion = document.getElementById('plan-unidad-evaluacion').checked;
  const tipo_evaluacion = incluir_evaluacion ? document.getElementById('plan-unidad-tipo-eval').value : null;
  const objetivos = document.getElementById('plan-unidad-objetivos').value.split('\n').filter(Boolean);
  const contenidos = document.getElementById('plan-unidad-contenidos').value.split('\n').filter(Boolean);

  const loading = document.getElementById('plan-unidad-loading');
  const resultado = document.getElementById('resultado-plan-unidad');

  loading.style.display = 'block';
  resultado.innerHTML = '';

  try {
    const data = await apiFetch('/api/planificaciones/unidad', {
      method: 'POST',
      body: JSON.stringify({
        asignacion_id, titulo_unidad, horas_docentes, porcentaje_emergentes,
        incluir_evaluacion, tipo_evaluacion, objetivos, contenidos,
      }),
    });
    loading.style.display = 'none';
    renderPlanUnidad(data, resultado);
  } catch (e) {
    loading.style.display = 'none';
    resultado.innerHTML = `<p class="error-msg">❌ ${e.message}</p>`;
  }
}

function renderPlanUnidad(data, container) {
  const c = data.contenido;
  if (c.error) {
    container.innerHTML = `<p class="error-msg">❌ ${c.error}</p>`;
    return;
  }

  const clases = (c.clases || []).map(cl => `
    <div class="clase-card">
      <h5>Clase ${cl.numero}: ${cl.titulo}</h5>
      <p>🎯 ${cl.objetivo}</p>
      <p>📖 ${cl.contenido_principal}</p>
      <p>🔧 ${cl.estrategia_didactica}</p>
      <p>⏱ ${cl.duracion_minutos} min ${cl.es_evaluacion ? '📝 EVALUACIÓN' : ''}</p>
    </div>
  `).join('');

  container.innerHTML = `
    <div class="resultado-planif">
      <h3>✨ ${c.titulo}</h3>
      <p>⏱ ${c.total_horas} horas · ${c.horas_emergentes} para emergentes · ${c.horas_contenido} de contenido</p>
      ${c.tiene_evaluacion ? `<p>📝 Evaluación: ${c.tipo_evaluacion}</p>` : ''}
      <h4 style="margin: 16px 0 8px">Secuencia de clases:</h4>
      ${clases}
      <button class="btn-secondary" style="margin-top: 16px" onclick="aprobarPlanificacion('${data.id}')">
        ✅ Marcar como vigente
      </button>
    </div>
  `;
}

// ============================================================
// PLANIFICACIÓN DIARIA
// ============================================================
async function generarPlanDiaria() {
  const asignacion_id = document.getElementById('plan-diaria-asignacion').value;
  const titulo_clase = document.getElementById('plan-diaria-titulo').value.trim();
  const objetivo = document.getElementById('plan-diaria-objetivo').value.trim();
  const contenido_principal = document.getElementById('plan-diaria-contenido').value.trim();
  const estrategia_sugerida = document.getElementById('plan-diaria-estrategia').value.trim();
  const duracion_minutos = parseInt(document.getElementById('plan-diaria-duracion').value);
  const contexto_clases_anteriores = document.getElementById('plan-diaria-contexto').value.trim();

  const loading = document.getElementById('plan-diaria-loading');
  const resultado = document.getElementById('resultado-plan-diaria');

  loading.style.display = 'block';
  resultado.innerHTML = '';

  try {
    const data = await apiFetch('/api/planificaciones/diaria', {
      method: 'POST',
      body: JSON.stringify({
        asignacion_id, titulo_clase, objetivo, contenido_principal,
        estrategia_sugerida, duracion_minutos, contexto_clases_anteriores,
      }),
    });
    loading.style.display = 'none';
    renderPlanDiaria(data, resultado);
  } catch (e) {
    loading.style.display = 'none';
    resultado.innerHTML = `<p class="error-msg">❌ ${e.message}</p>`;
  }
}

function renderPlanDiaria(data, container) {
  const c = data.contenido;
  if (c.error) {
    container.innerHTML = `<p class="error-msg">❌ ${c.error}</p>`;
    return;
  }

  const momentos = (c.momentos || []).map(m => `
    <div class="momento-card">
      <h5>${m.nombre} (${m.duracion_minutos} min)</h5>
      <p>${m.descripcion}</p>
      <p>👨‍🏫 <em>Docente:</em> ${m.rol_docente}</p>
      <p>👥 <em>Estudiantes:</em> ${m.rol_estudiante}</p>
    </div>
  `).join('');

  const recursos = (c.recursos_necesarios || []).map(r => `<li>${r}</li>`).join('');

  container.innerHTML = `
    <div class="resultado-planif">
      <h3>✨ ${c.titulo}</h3>
      <p>🎯 ${c.objetivo}</p>
      <p>⏱ Duración total: ${c.duracion_total_minutos} minutos</p>
      <h4 style="margin: 16px 0 8px">Momentos de la clase:</h4>
      ${momentos}
      ${recursos ? `<h4 style="margin: 16px 0 8px">Recursos:</h4><ul style="margin-left:18px;font-size:14px">${recursos}</ul>` : ''}
      ${c.tarea_sugerida ? `<p style="margin-top:12px"><strong>Tarea:</strong> ${c.tarea_sugerida}</p>` : ''}
      <button class="btn-secondary" style="margin-top: 16px" onclick="aprobarPlanificacion('${data.id}')">
        ✅ Marcar como vigente
      </button>
    </div>
  `;
}

// ============================================================
// APROBAR PLANIFICACIÓN
// ============================================================
async function aprobarPlanificacion(id) {
  try {
    await apiFetch(`/api/planificaciones/${id}/estado?estado=vigente`, { method: 'PATCH' });
    alert('✅ Planificación marcada como vigente.');
  } catch (e) {
    alert('❌ ' + e.message);
  }
}

// ============================================================
// DESARROLLO DIARIO
// ============================================================
async function cargarDesarrollos() {
  const asignacion_id = document.getElementById('desarrollo-asignacion').value;
  if (!asignacion_id) return;

  try {
    // Traer los últimos 30 desarrollos de esta asignación
    const data = await apiFetch(`/api/desarrollo/lista?asignacion_id=${asignacion_id}`);
    renderDesarrollos(data);
  } catch (e) {
    document.getElementById('lista-desarrollos').innerHTML =
      `<p class="empty-state">No hay desarrollos registrados todavía.<br>Enviá un mensaje al bot de Telegram para registrar uno.</p>`;
  }
}

function renderDesarrollos(desarrollos) {
  const el = document.getElementById('lista-desarrollos');
  if (!desarrollos?.length) {
    el.innerHTML = '<p class="empty-state">No hay desarrollos registrados todavía.<br>Enviá un mensaje al bot de Telegram para registrar uno.</p>';
    return;
  }

  el.innerHTML = desarrollos.map(d => `
    <div class="desarrollo-card" id="dev-${d.id}">
      <div class="desarrollo-header">
        <span class="desarrollo-fecha">📅 ${formatFecha(d.fecha)}</span>
        <span class="desarrollo-origen ${d.origen === 'manual' ? 'manual' : ''}">
          ${d.origen === 'telegram' ? '🤖 Telegram' : '✏️ Manual'}
        </span>
      </div>
      <p class="desarrollo-texto" id="texto-${d.id}">${d.texto_estructurado}</p>
      <textarea class="desarrollo-textarea" id="textarea-${d.id}">${d.texto_estructurado}</textarea>
      <div class="desarrollo-actions">
        <button class="btn-edit" id="btn-edit-${d.id}" onclick="toggleEdicion('${d.id}')">✏️ EDITAR</button>
        <button class="btn-primary" id="btn-save-${d.id}" style="display:none;width:auto;padding:6px 14px"
          onclick="guardarDesarrollo('${d.id}', '${d.asignacion_id}')">💾 Guardar</button>
        <button class="btn-secondary" id="btn-cancel-${d.id}" style="display:none"
          onclick="cancelarEdicion('${d.id}')">Cancelar</button>
      </div>
    </div>
  `).join('');
}

function toggleEdicion(id) {
  document.getElementById(`texto-${id}`).style.display = 'none';
  document.getElementById(`textarea-${id}`).style.display = 'block';
  document.getElementById(`btn-edit-${id}`).style.display = 'none';
  document.getElementById(`btn-save-${id}`).style.display = 'inline-block';
  document.getElementById(`btn-cancel-${id}`).style.display = 'inline-block';
}

function cancelarEdicion(id) {
  document.getElementById(`texto-${id}`).style.display = 'block';
  document.getElementById(`textarea-${id}`).style.display = 'none';
  document.getElementById(`btn-edit-${id}`).style.display = 'inline-block';
  document.getElementById(`btn-save-${id}`).style.display = 'none';
  document.getElementById(`btn-cancel-${id}`).style.display = 'none';
}

async function guardarDesarrollo(id, asignacion_id) {
  const nuevo_texto = document.getElementById(`textarea-${id}`).value.trim();
  try {
    await apiFetch(`/api/desarrollo/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ texto_estructurado: nuevo_texto, revisado: true }),
    });
    document.getElementById(`texto-${id}`).textContent = nuevo_texto;
    cancelarEdicion(id);
  } catch (e) {
    alert('❌ ' + e.message);
  }
}

// ============================================================
// MODALES
// ============================================================
function showModal(id) {
  document.getElementById(id).style.display = 'block';
  document.getElementById('modal-overlay').style.display = 'block';
}

function hideModal(id) {
  document.getElementById(id).style.display = 'none';
  document.getElementById('modal-overlay').style.display = 'none';
}

function hideAllModals() {
  document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
  document.getElementById('modal-overlay').style.display = 'none';
}

// ============================================================
// HELPERS
// ============================================================
function showError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.style.display = 'block';
}

function formatFecha(fechaStr) {
  const [y, m, d] = fechaStr.split('-');
  return `${d}/${m}/${y}`;
}