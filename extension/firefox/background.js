const BACKEND_URL = 'https://canbet.live/api/canvas/sync/';

browser.runtime.onMessage.addListener((message) => {
  if (message.type !== 'CANVAS_ASSIGNMENTS') return;

  const { user_data, courses } = message.payload;

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
  browser.runtime.onMessage.addListener(async (message) => {
    if (message.type === "fetchCanvas") {
      const response = await fetch("https://canbet.live/api/canvas/sync/");
      const data = await response.json();
      return data;
    }
  });
  

  if (submissions.length === 0) return;

  fetch(BACKEND_URL, {
    method: 'POST',
    credentials: 'include',    
    headers: { 'Content-Type': 'application/json' },
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
        console.log(`[canBet] Synced ${data.created} new submission(s). Bits awarded: ${data.bits_awarded}`);
      }
    })
    .catch(err => console.error('[canBet] Sync error:', err));
});
