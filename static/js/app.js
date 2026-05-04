/* Agrobotic ScanBerry — Frontend Logic */
document.addEventListener('DOMContentLoaded', () => {
  setupUpload();
  setupLoading();
});

function setupUpload() {
  const area = document.getElementById('upload-area');
  const input = document.getElementById('imagem-input');
  const preview = document.getElementById('preview-container');
  if (!area || !input) return;

  area.addEventListener('click', () => input.click());
  area.addEventListener('dragover', e => { e.preventDefault(); area.classList.add('dragover'); });
  area.addEventListener('dragleave', () => area.classList.remove('dragover'));
  area.addEventListener('drop', e => {
    e.preventDefault(); area.classList.remove('dragover');
    if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; showPreview(input.files[0]); }
  });
  input.addEventListener('change', () => { if (input.files[0]) showPreview(input.files[0]); });

  function showPreview(file) {
    if (!file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = e => {
      preview.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
      area.querySelector('.upload-text').style.display = 'none';
    };
    reader.readAsDataURL(file);
  }
}

function setupLoading() {
  const form = document.getElementById('analise-form');
  if (!form) return;
  form.addEventListener('submit', e => {
    const input = document.getElementById('imagem-input');
    if (!input || !input.files.length) { e.preventDefault(); alert('Selecione uma imagem.'); return; }
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `<div class="loading-spinner"></div>
      <p class="loading-text">🍓 Analisando imagem com IA...</p>
      <p style="color:var(--text-muted);font-size:.85rem">Isso pode levar alguns segundos</p>`;
    document.body.appendChild(overlay);
  });
}
