browser.runtime.onMessage.addListener((message) => {
  if (message.type === 'CANVAS_ASSIGNMENTS') {
    const { user_data, courses } = message.payload;

    console.log('[canBet] User:', user_data.name, '| STUDENT_ID:', user_data.id);

    courses.forEach(({ COURSE_ID, courseName, data }) => {
      console.log(`[canBet] Course: ${courseName} | COURSE_ID: ${COURSE_ID}`);

      if (!Array.isArray(data) || data.length === 0) return;

      data.forEach(sub => {
        const submitted_at = sub.submitted_at ?? 'N/A';
        const score = sub.score ?? 'N/A';
        console.log(`  - ${sub.title} | Score: ${score} / ${sub.points_possible} | Submitted: ${submitted_at} | State: ${sub.workflow_state}`);
      });
    });

    browser.storage.local.set({
      user_data,
      courses,
      CANVAS_DOMAIN: message.domain
    });
  }
});