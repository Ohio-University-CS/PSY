const API_ME_URL = 'https://www.canbet.live/api/me/';

const bitsValue = document.getElementById('bitsValue');
const statusText = document.getElementById('statusText');

function setStatus(message) {
  statusText.textContent = message || '';
}

function formatBits(value) {
  return Number(value || 0).toLocaleString();
}

browser.storage.local.get('authToken')
  .then(({ authToken }) => {
    if (!authToken) {
      bitsValue.textContent = '--';
      setStatus('Log in on canbet.live to show your balance.');
      return;
    }

    return fetch(API_ME_URL, {
      headers: {
        'Authorization': `Token ${authToken}`,
      },
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Balance unavailable.');
        bitsValue.textContent = formatBits(data.bit_balance);
        setStatus(`${data.username || 'Account'} is synced.`);
      });
  })
  .catch(() => {
    bitsValue.textContent = '--';
    setStatus('Open canbet.live and log in again.');
  });
