const root = document.querySelector('#app');

function applyEnhancements() {
  const version = document.querySelector('.version');
  if (version && version.textContent !== 'YS X STUDIO / 2.3.1') {
    version.textContent = 'YS X STUDIO / 2.3.1';
  }
  const syncButton = document.querySelector('#sync-scripts');
  if (syncButton && syncButton.textContent !== '↻ Sincronizar textos brutos') {
    syncButton.textContent = '↻ Sincronizar textos brutos';
  }
  const search = document.querySelector('#search');
  if (search && search.placeholder !== 'Buscar por texto, arquivo ou tag:itens…') {
    search.placeholder = 'Buscar por texto, arquivo ou tag:itens…';
  }
  const filters = document.querySelector('.filters');
  if (filters && !document.querySelector('.tag-search-map')) {
    const tagMap = [
      ['dialogos', 'Diálogos'], ['menus', 'Menus'], ['itens', 'Itens'],
      ['habilidades', 'Habilidades'], ['descricoes', 'Descrições'],
      ['tutoriais', 'Tutoriais'], ['missoes', 'Missões'], ['perfis', 'Perfis'],
      ['vozes', 'Vozes'], ['escolhas', 'Escolhas'], ['interface', 'Interface'],
      ['notificacoes', 'Notificações'], ['diario', 'Diário'], ['personagens', 'Personagens'],
      ['bestiario', 'Bestiário'], ['mapas', 'Mapas'], ['lojas', 'Lojas'],
      ['navio', 'Navio'], ['conquistas', 'Conquistas'], ['minijogos', 'Minijogos'],
      ['eventos', 'Eventos'], ['configuracoes', 'Configurações'], ['controles', 'Controles'],
    ];
    const details = document.createElement('details');
    details.className = 'tag-search-map';
    details.innerHTML = `<summary>Tags de categoria</summary><div class="tag-chip-list">${tagMap
      .map(([slug, label]) => `<button type="button" class="tag-chip" data-search-tag="${slug}">tag:${slug} · ${label}</button>`)
      .join('')}</div><div class="tag-search-hint">É possível combinar texto e várias tags: <code>Adol tag:dialogos tag:vozes</code>. Veja o mapa completo em <code>Documentacao/MAPA_TAGS.md</code>.</div>`;
    filters.after(details);
    details.querySelectorAll('[data-search-tag]').forEach(button => {
      button.onclick = () => {
        const field = document.querySelector('#search');
        if (!field) return;
        field.value = `tag:${button.dataset.searchTag}`;
        field.dispatchEvent(new Event('input', { bubbles: true }));
      };
    });
  }
  const original = document.querySelector('.original');
  if (original && original.tagName !== 'TEXTAREA') {
    const copyField = document.createElement('textarea');
    copyField.className = original.className + ' original-copy';
    copyField.value = original.textContent;
    copyField.readOnly = true;
    copyField.setAttribute('aria-label', 'Texto original em inglês');
    original.replaceWith(copyField);
  }
  const originalLabel = [...document.querySelectorAll('.editor-pane .field-label')]
    .find(label => (label.firstElementChild?.textContent || '').startsWith('01 ·'));
  if (originalLabel && !originalLabel.querySelector('#copy-original')) {
    const detail = originalLabel.lastElementChild;
    if (detail) {
      const copyButton = document.createElement('button');
      copyButton.id = 'copy-original';
      copyButton.className = 'inline-copy';
      copyButton.type = 'button';
      copyButton.textContent = 'Copiar original';
      copyButton.onclick = async () => {
        const field = document.querySelector('.original-copy');
        if (!field) return;
        try {
          await navigator.clipboard.writeText(field.value);
          copyButton.textContent = 'Copiado!';
        } catch {
          field.focus();
          field.select();
          document.execCommand('copy');
          copyButton.textContent = 'Copiado!';
        }
        setTimeout(() => { copyButton.textContent = 'Copiar original'; }, 1400);
      };
      detail.replaceWith(copyButton);
    }
  }
  for (const id of ['translation', 'reviewed']) {
    const editor = document.querySelector(`#${id}`);
    if (editor && editor.getAttribute('wrap') !== 'off') {
      editor.setAttribute('wrap', 'off');
      editor.style.fontFamily = 'Consolas, "Cascadia Mono", monospace';
      editor.style.overflowX = 'auto';
    }
  }
  const labels = document.querySelectorAll('.editor-pane .field-label');
  for (const label of labels) {
    const title = label.firstElementChild?.textContent || '';
    const detail = label.lastElementChild;
    if (detail && title.startsWith('02 ·') && detail.textContent !== 'quebra automática · 72 colunas') {
      detail.textContent = 'quebra automática · 72 colunas';
    }
    if (detail && title.startsWith('03 ·') && detail.textContent !== 'prioridade · quebra em 72 colunas') {
      detail.textContent = 'prioridade · quebra em 72 colunas';
    }
  }
  const saveButton = document.querySelector('#save');
  if (saveButton && saveButton.textContent !== '▣ Salvar trecho') {
    saveButton.textContent = '▣ Salvar trecho';
  }
  const translation = document.querySelector('#translation');
  const reviewed = document.querySelector('#reviewed');
  const validation = document.querySelector('.validation');
  if (translation && reviewed && validation) {
    let effective = document.querySelector('.effective-source');
    if (!effective) {
      effective = document.createElement('div');
      effective.className = 'effective-source';
      validation.before(effective);
    }
    const updateEffective = () => {
      let text;
      let source;
      if (reviewed.value.trim()) {
        text = 'Texto usado no jogo: revisão final';
        source = 'reviewed';
      } else if (translation.value.trim()) {
        text = 'Texto usado no jogo: tradução automática';
        source = 'automatic';
      } else {
        text = 'Texto usado no jogo: aguardando tradução';
        source = 'empty';
      }
      if (effective.textContent !== text) effective.textContent = text;
      if (effective.dataset.source !== source) effective.dataset.source = source;
    };
    if (!reviewed.dataset.effectiveBound) {
      translation.addEventListener('input', updateEffective);
      reviewed.addEventListener('input', updateEffective);
      reviewed.dataset.effectiveBound = 'true';
    }
    updateEffective();
  }
}

applyEnhancements();
const enhancementObserver = new MutationObserver(() => {
  enhancementObserver.disconnect();
  try {
    applyEnhancements();
  } finally {
    enhancementObserver.observe(root, {childList: true, subtree: true});
  }
});
enhancementObserver.observe(root, {childList: true, subtree: true});
