const apiBase = document.getElementById('apiBase');
const output = document.getElementById('output');
const status = document.getElementById('status');

apiBase.value = localStorage.getItem('dukame_api_base') || apiBase.value;

document.getElementById('saveBase').addEventListener('click', () => {
  const value = apiBase.value.trim().replace(/\/$/, '');
  apiBase.value = value;
  localStorage.setItem('dukame_api_base', value);
  status.textContent = 'Saved';
});

async function callEndpoint(path) {
  const base = apiBase.value.trim().replace(/\/$/, '');
  const url = `${base}${path}`;
  status.textContent = 'Loading...';
  output.textContent = `GET ${url}`;

  try {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    const text = await response.text();
    let body;
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }

    status.textContent = `${response.status} ${response.statusText}`;
    output.textContent = typeof body === 'string' ? body : JSON.stringify(body, null, 2);
  } catch (error) {
    status.textContent = 'Request failed';
    output.textContent = `${error.name}: ${error.message}\n\nCheck that the backend is running and CORS allows this frontend origin.`;
  }
}

document.querySelectorAll('.endpoint').forEach((button) => {
  button.addEventListener('click', () => callEndpoint(button.dataset.path));
});
