async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(data.detail || 'Request failed');
  }
  return response.json();
}

function uploadForm(url, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.responseType = 'json';

    xhr.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable || !onProgress) {
        return;
      }
      onProgress(Math.round((event.loaded / event.total) * 100));
    });

    xhr.addEventListener('load', () => {
      const data = xhr.response || JSON.parse(xhr.responseText || '{}');
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
        return;
      }
      reject(new Error(data.detail || 'Request failed'));
    });

    xhr.addEventListener('error', () => reject(new Error('Сеть недоступна')));
    xhr.send(formData);
  });
}

function statusClass(status) {
  return `status ${status || ''}`;
}

function humanStatus(status) {
  const map = {
    uploaded: 'Файл сохранён',
    queued: 'Задача стоит в очереди',
    transcribing: 'Идёт транскрибация',
    summarizing: 'Формируется extractive summary',
    rendering: 'Собирается итоговый ролик',
    done: 'Обработка завершена',
    failed: 'Обработка завершилась с ошибкой',
  };
  return map[status] || status;
}

function formatTimecode(value) {
  const seconds = Math.max(0, Math.floor(Number(value) || 0));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return [hours, minutes, secs].map((item) => String(item).padStart(2, '0')).join(':');
  }

  return [minutes, secs].map((item) => String(item).padStart(2, '0')).join(':');
}

function formatDateTime(value) {
  if (!value) {
    return '—';
  }

  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
