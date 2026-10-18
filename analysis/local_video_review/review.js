'use strict';
(() => {
  const records = window.REVIEW_MANIFEST.records;
  const storageKey = 'forte-local-review-v1';
  const $ = (id) => document.getElementById(id);
  const player = $('player');
  let reviews = {};
  let selectedId = records[0].id;
  let pendingSeek = null;
  let storageWorks = true;
  try { reviews = JSON.parse(localStorage.getItem(storageKey) || '{}'); }
  catch { storageWorks = false; $('storage-status').textContent = 'Автосохранение недоступно. Экспортируйте JSON после каждого проверенного ролика.'; }
  if (!reviews || typeof reviews !== 'object' || Array.isArray(reviews)) reviews = {};

  function currentRecord() { return records.find((r) => r.id === selectedId); }
  function reviewFor(id) {
    if (!reviews[id]) reviews[id] = {status: 'not_reviewed', full_clip_watched: false, verdict: 'unreviewed', notes: '', events: []};
    return reviews[id];
  }
  function save() {
    reviewFor(selectedId).updated_at = new Date().toISOString();
    try { localStorage.setItem(storageKey, JSON.stringify(reviews)); }
    catch { storageWorks = false; $('storage-status').textContent = 'Браузер не сохранил изменения. Нажмите «Экспорт JSON» перед закрытием страницы.'; }
    $('save-indicator').textContent = storageWorks ? 'Сохранено в этом браузере' : 'Изменения в памяти — экспортируйте JSON';
    renderList();
  }
  function visibleRecords() {
    const filter = $('filter').value;
    return records.filter((r) => filter === 'positive' ? r.positive : filter === 'negative' ? !r.positive : filter === 'pending' ? reviewFor(r.id).status !== 'reviewed' : filter === 'uncertain' ? reviewFor(r.id).status === 'uncertain' || reviewFor(r.id).events.some((e) => e.uncertain) : true);
  }
  function element(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  }
  function button(text, onClick) { const el = element('button', text); el.type = 'button'; el.addEventListener('click', onClick); return el; }
  function renderList() {
    $('video-list').replaceChildren();
    const visible = visibleRecords();
    for (const r of visible) {
      const rev = reviewFor(r.id);
      const b = button('', () => selectClip(r.id));
      b.className = 'clip-row' + (r.id === selectedId ? ' active' : '');
      b.setAttribute('aria-current', r.id === selectedId ? 'true' : 'false');
      b.append(element('span', (rev.status === 'reviewed' ? '✓ ' : '') + r.source_labels.map((x) => x.file).join(' / '), 'row-title'));
      const timestamps = r.timestamps_sec.length ? ' · ' + r.timestamps_sec.join(', ') + ' с' : '';
      b.append(element('span', (r.positive ? 'Нарушение по разметке' : 'Без нарушения по разметке') + timestamps + ' · ' + Math.round(r.duration_sec) + ' с', 'row-meta'));
      $('video-list').append(b);
    }
    if (!visible.length) $('video-list').append(element('p', 'Нет роликов с таким фильтром.', 'empty'));
    $('progress').textContent = records.filter((r) => reviewFor(r.id).status === 'reviewed').length + ' / ' + records.length + ' проверено';
  }
  function seek(time) {
    const target = Math.max(0, Math.min(Number(time), Number.isFinite(player.duration) ? player.duration : currentRecord().duration_sec));
    if (player.readyState >= 1) { player.currentTime = target; pendingSeek = null; }
    else { pendingSeek = target; player.load(); }
  }
  player.addEventListener('loadedmetadata', () => { if (pendingSeek !== null) seek(pendingSeek); });
  player.addEventListener('timeupdate', () => { $('clock').textContent = player.currentTime.toFixed(2) + ' с'; });
  player.addEventListener('error', () => { $('media-error').hidden = false; });
  player.addEventListener('play', () => { if (reviewFor(selectedId).status === 'not_reviewed') { reviewFor(selectedId).status = 'in_progress'; $('review-status').value = 'in_progress'; save(); } });

  function selectClip(id) {
    player.pause();
    selectedId = id;
    const r = currentRecord();
    const rev = reviewFor(id);
    $('clip-title').textContent = r.source_labels.map((x) => x.file).join(' / ');
    $('clip-meta').textContent = r.duration_sec.toFixed(2) + ' секунд · ' + (r.source_labels.length > 1 ? 'Байт-в-байт одинаковые файлы объединены. ' : '') + (r.timestamps_sec.length > 1 ? 'Два исходных таймкода: проверьте оба.' : '');
    $('label-badge').textContent = r.positive ? 'Исходная метка: нарушение' : 'Исходная метка: без нарушения';
    $('label-badge').className = 'badge' + (r.positive ? ' positive' : '');
    $('media-error').hidden = true;
    $('clock').textContent = '0.00 с';
    pendingSeek = r.timestamps_sec.length ? Math.max(0, r.timestamps_sec[0] - 5) : 0;
    const src = '../../open/videos/' + encodeURIComponent(r.file);
    player.src = src;
    player.playbackRate = Number($('speed').value);
    $('source-link').href = src;
    $('source-link').download = r.file;
    $('seek-buttons').replaceChildren();
    $('seek-buttons').append(button('Начало', () => seek(0)));
    for (const t of r.timestamps_sec) {
      for (const offset of [-5, 0, 5]) {
        const target = Math.max(0, Math.min(r.duration_sec, t + offset));
        $('seek-buttons').append(button(offset === 0 ? 'Метка ' + t + ' с' : 'Метка ' + t + (offset > 0 ? ' +5' : ' −5') + ' с', () => seek(target)));
      }
    }
    $('review-status').value = rev.status;
    $('full-clip').checked = rev.full_clip_watched;
    $('human-verdict').value = rev.verdict;
    $('clip-notes').value = rev.notes;
    $('save-indicator').textContent = rev.updated_at ? 'Есть сохранённая разметка' : 'Разметка ещё не заполнена';
    renderEvents();
    renderList();
  }
  function inputField(parent, labelText, value, onChange, type = 'text') {
    const label = element('label', labelText);
    const input = document.createElement(type === 'textarea' ? 'textarea' : 'input');
    if (type !== 'textarea') input.type = type;
    else input.rows = 3;
    input.value = value == null ? '' : value;
    if (type === 'number') { input.min = '0'; input.max = String(currentRecord().duration_sec); input.step = '0.1'; }
    input.addEventListener('input', () => { onChange(type === 'number' ? input.value === '' ? null : Number(input.value) : input.value); save(); });
    label.append(input);
    parent.append(label);
    return input;
  }
  function renderEvents() {
    const rev = reviewFor(selectedId);
    $('events').replaceChildren();
    rev.events.forEach((event, index) => {
      const box = element('div', undefined, 'event');
      const heading = element('div', undefined, 'event-heading');
      heading.append(element('strong', 'Событие ' + (index + 1)), button('Удалить', () => {
        if (window.confirm('Удалить это событие из локальной разметки?')) { rev.events.splice(index, 1); save(); renderEvents(); }
      }));
      box.append(heading);
      inputField(box, 'Категория / тип действия', event.category, (v) => { event.category = v; });
      const times = element('div', undefined, 'time-fields');
      for (const [key, label] of [['start_sec', 'Начало, с'], ['end_sec', 'Конец, с']]) {
        const cell = element('div', undefined, 'time-field');
        const input = inputField(cell, label, event[key], (v) => { event[key] = v; }, 'number');
        cell.append(button('Текущее время', () => { event[key] = Math.round(player.currentTime * 100) / 100; input.value = event[key]; save(); }));
        times.append(cell);
      }
      box.append(times);
      inputField(box, 'Что непосредственно видно', event.visible_observation, (v) => { event.visible_observation = v; }, 'textarea');
      inputField(box, 'ID правила / пункт / ссылка (если подтверждены)', event.rule_id, (v) => { event.rule_id = v; });
      const uncertain = element('label', undefined, 'check');
      const check = document.createElement('input'); check.type = 'checkbox'; check.checked = event.uncertain;
      check.addEventListener('change', () => { event.uncertain = check.checked; save(); });
      uncertain.append(check, document.createTextNode('Есть сомнения в наблюдении или трактовке'));
      box.append(uncertain);
      $('events').append(box);
    });
    if (!rev.events.length) $('events').append(element('p', 'События пока не добавлены.', 'empty'));
  }
  $('filter').addEventListener('change', renderList);
  $('review-status').addEventListener('change', () => { reviewFor(selectedId).status = $('review-status').value; save(); });
  $('full-clip').addEventListener('change', () => { reviewFor(selectedId).full_clip_watched = $('full-clip').checked; save(); });
  $('human-verdict').addEventListener('change', () => { reviewFor(selectedId).verdict = $('human-verdict').value; save(); });
  $('clip-notes').addEventListener('input', () => { reviewFor(selectedId).notes = $('clip-notes').value; save(); });
  $('speed').addEventListener('change', () => { player.playbackRate = Number($('speed').value); });
  $('back-five').addEventListener('click', () => seek(player.currentTime - 5));
  $('forward-five').addEventListener('click', () => seek(player.currentTime + 5));
  $('add-event').addEventListener('click', () => {
    reviewFor(selectedId).events.push({category: '', start_sec: null, end_sec: null, visible_observation: '', rule_id: '', uncertain: false});
    if (reviewFor(selectedId).status === 'not_reviewed') { reviewFor(selectedId).status = 'in_progress'; $('review-status').value = 'in_progress'; }
    save(); renderEvents();
  });
  function navigate(direction) {
    const visible = visibleRecords();
    if (!visible.length) return;
    const index = visible.findIndex((r) => r.id === selectedId);
    selectClip(visible[(index + direction + visible.length) % visible.length].id);
  }
  $('previous').addEventListener('click', () => navigate(-1));
  $('next').addEventListener('click', () => navigate(1));
  $('export').addEventListener('click', () => {
    const data = {schema_version: 1, exported_at: new Date().toISOString(), source: 'human_local_review', videos: records.map((r) => ({...r, review: reviewFor(r.id)}))};
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
    const a = document.createElement('a'); a.href = url; a.download = 'forte-video-review-' + new Date().toISOString().replace(/[:.]/g, '-') + '.json';
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  selectClip(selectedId);
})();
