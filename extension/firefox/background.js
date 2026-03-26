const BACKEND = 'https://canbet.live/api/canvas/sync';

browsrer.runtime.onMessage.addListener((message) => {
  if (message.type !== 'CANVAS_ASSIGNMENTS') return;

  const { user_data, courses } = message.payload;

  const submissions = {};
  courses.forEach(({ COURSE_ID, courseName, data }) => {
    if (!Array.isArray(data)) return;
    data .forEach(sub => {
      if (!sub.submitted_at) return;
      submissions.push({
        course_id: String(COURSE_ID),
        course_name: courseName,
        assignment_id: String(sub.assignment_id),
        submitted_at: sub.submitted_at,
      });
    });
  });

  if (submissions.length === 0) return;

  fetch(BACKEND, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: String(user_data.id),
      submissions,
    }),
  }).catch(err => console.error('Error syncing with backend:', err));
});