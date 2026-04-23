const BACKEND_URL = 'https://www.canbet.live/api/canvas/sync/';

let pendingPayload = null;

function doSync(user_data, courses) {
  const submissions = [];

  courses.forEach(({ COURSE_ID, courseName, data }) => {
    if (!Array.isArray(data)) return;

    data.forEach((sub) => {
      if (!sub.submitted_at) return;

      submissions.push({
        course_id: String(COURSE_ID),
        course_name: courseName,
        assignment_id: String(sub.assignment_id),
        submitted_at: sub.submitted_at,
        score: sub.score ?? null,
      });
    });
  });

  if (submissions.length === 0) return;

  chrome.storage.local.get(['authToken'], ({ authToken }) => {
    if (chrome.runtime.lastError) {
      console.error('[canBet] Failed to read auth token:', chrome.runtime.lastError.message);
      return;
    }

    if (!authToken) {
      console.warn('[canBet] No auth token yet — sync queued, will retry on login.');
      pendingPayload = { user_data, courses };
      return;
    }

    pendingPayload = null;

    fetch(BACKEND_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Token ${authToken}`,
      },
      body: JSON.stringify({
        canvas_user_id: String(user_data.id),
        submissions,
      }),
    })
      .then(async (res) => {
        let data = null;

        try {
          data = await res.json();
        } catch (err) {
          data = { error: 'Non-JSON response' };
        }

        if (!res.ok) {
          console.error('[canBet] Sync failed:', res.status, JSON.stringify(data, null, 2));
        } else {
          const created = data?.created ?? 0;
          const bits = data?.bits_awarded ?? 0;
          console.log(`[canBet] Synced ${created} new submission(s). Bits awarded: ${bits}`);

          if (bits > 0) {
            chrome.notifications.create({
              type: 'basic',
              iconUrl: 'icons/canbet.png',
              title: 'canBet — Bits Earned!',
              message: `+${bits} bits for turning in ${created} assignment${created !== 1 ? 's' : ''}!`,
            });
          }
        }
      })
  });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) return;

  if (message.type === 'CANBET_TOKEN') {
    chrome.storage.local.set({ authToken: message.token }, () => {
      if (chrome.runtime.lastError) {
        console.error('[canBet] Failed to save auth token:', chrome.runtime.lastError.message);
        return;
      }

      console.log('[canBet] Auth token saved.');

      if (pendingPayload) {
        console.log('[canBet] Retrying queued sync with new token...');
        const { user_data, courses } = pendingPayload;
        doSync(user_data, courses);
      }
    });

    sendResponse({ ok: true });
    return true;
  }

  if (message.type === 'CANVAS_ASSIGNMENTS') {
    const { user_data, courses } = message.payload || {};

    if (user_data && courses) {
      doSync(user_data, courses);
      sendResponse({ ok: true });
    } else {
      console.error('[canBet] Missing assignment payload.');
      sendResponse({ ok: false, error: 'Missing payload' });
    }

    return true;
  }
});