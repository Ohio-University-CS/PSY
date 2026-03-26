(function () {
  const CANVAS_DOMAIN = window.location.hostname;

  if (!CANVAS_DOMAIN.match(/^[^.]+\.instructure\.com$/) || CANVAS_DOMAIN.includes('login')) {
    return;
  }

  const safeJson = (res) => {
    if (!res.ok || res.headers.get('content-type')?.includes('text/html')) {
      throw new Error(`Bad response: ${res.status} on ${res.url}`);
    }
    return res.json();
  };

  fetch(`https://${CANVAS_DOMAIN}/api/v1/users/self`, {
    credentials: 'include'
  })
    .then(safeJson)
    .then(user_data => {
      const STUDENT_ID = user_data.id;

      return fetch(`https://${CANVAS_DOMAIN}/api/v1/courses?per_page=100&enrollment_state=active`, {
        credentials: 'include'
      })
        .then(safeJson)
        .then(courses => ({ user_data, STUDENT_ID, courses }));
    })
    .then(({ user_data, STUDENT_ID, courses }) => {

      const requests = courses.map(course => {
        const COURSE_ID = course.id;

        const submissionsReq = fetch(
          `https://${CANVAS_DOMAIN}/api/v1/courses/${COURSE_ID}/students/submissions?student_ids[]=${STUDENT_ID}&per_page=100`,
          { credentials: 'include' }
        ).then(safeJson);

        const assignmentsReq = fetch(
          `https://${CANVAS_DOMAIN}/api/v1/courses/${COURSE_ID}/assignments?per_page=100`,
          { credentials: 'include' }
        ).then(safeJson);

        return Promise.all([submissionsReq, assignmentsReq])
          .then(([submissions, assignments]) => {
            const assignmentMap = {};
            if (Array.isArray(assignments)) {
              assignments.forEach(a => {
                assignmentMap[a.id] = {
                  title: a.name,
                  points_possible: a.points_possible
                };
              });
            }

            const data = Array.isArray(submissions) ? submissions.map(sub => ({
              assignment_id: sub.assignment_id,
              title: assignmentMap[sub.assignment_id]?.title ?? 'Unknown',
              points_possible: assignmentMap[sub.assignment_id]?.points_possible ?? null,
              score: sub.score,
              submitted_at: sub.submitted_at,
              workflow_state: sub.workflow_state
            })) : [];

            return { COURSE_ID, courseName: course.name ?? `course_${COURSE_ID}`, data };
          })
          .catch(err => {
            console.warn(`[canBet] Skipping course ${COURSE_ID}:`, err.message);
            return { COURSE_ID, courseName: course.name ?? `course_${COURSE_ID}`, data: [] };
          });
      });

      return Promise.all(requests).then(results => ({ user_data, results }));
    })
    .then(({ user_data, results }) => {
      chrome.runtime.sendMessage({
        type: 'CANVAS_ASSIGNMENTS',
        payload: { user_data, courses: results },
        domain: CANVAS_DOMAIN
      });
    })
    .catch(err => console.error('[canBet] fetch failed:', err));
})();