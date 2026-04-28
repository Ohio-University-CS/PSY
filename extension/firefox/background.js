const BACKEND_URL = 'https://www.canbet.live/api/canvas/sync/';

let pendingPayload = null;

function doSync(user_data, courses) {
  const submissions = [];
  courses.forEach(({ COURSE_ID, courseName, data }) => {
    if (!Array.isArray(data)) return;
    data.forEach(sub => {
      if (!sub.submitted_at) return;
      submissions.push({
        course_id:     String(COURSE_ID),
        course_name:   courseName,
        assignment_id: String(sub.assignment_id),
        submitted_at:  sub.submitted_at,
        score:         sub.score ?? null,
      });
    });
  });

  if (submissions.length === 0) return;

  browser.storage.local.get('authToken').then(({ authToken }) => {
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
      .then(async res => {
        const data = await res.json();
        if (!res.ok) {
          console.error('[canBet] Sync failed:', data);
        } else {
          const created = data.created ?? 0;
          const bits = data.bits_awarded ?? 0;
          console.log(`[canBet] Synced ${created} new submission(s). Bits awarded: ${bits}`);

          if (bits > 0) {
            browser.notifications.create({
              type: 'basic',
              iconUrl: 'icons/canbet.png',
              title: 'canBet — Bits Earned!',
              message: `+${bits} bits for turning in ${created} assignment${created !== 1 ? 's' : ''}!`,
            });
          }
        }
      })
      .catch(err => console.error('[canBet] Sync error:', err));
  });
}

browser.runtime.onMessage.addListener((message) => {
  if (message.type === 'CANBET_TOKEN') {
    browser.storage.local.set({ authToken: message.token }).then(() => {
      console.log('[canBet] Auth token saved.');

      if (pendingPayload) {
        console.log('[canBet] Retrying queued sync with new token...');
        const { user_data, courses } = pendingPayload;
        doSync(user_data, courses);
      }
    });
    return;
  }

  if (message.type !== 'CANVAS_ASSIGNMENTS') return;

  const { user_data, courses } = message.payload;
  doSync(user_data, courses);
});