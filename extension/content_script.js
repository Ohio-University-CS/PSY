(function () {
  const CANVAS_DOMAIN = window.location.hostname;

  fetch(`https://${CANVAS_DOMAIN}/api/v1/users/self`, {
    credentials: 'include'
  })
    .then(res => res.json())
    .then(user_data => {
      const STUDENT_ID = user_data.id;

      return fetch(`https://${CANVAS_DOMAIN}/api/v1/courses?per_page=100&enrollment_state=active`, {
        credentials: 'include'
      })
        .then(res => res.json())
        .then(courses => ({ user_data, STUDENT_ID, courses }));
    })
    .then(({ user_data, STUDENT_ID, courses }) => {

      const requests = courses.map(course => {
        const COURSE_ID = course.id;

        const submissionsReq = fetch(
          `https://${CANVAS_DOMAIN}/api/v1/courses/${COURSE_ID}/students/submissions?student_ids[]=${STUDENT_ID}&per_page=100`,
          { credentials: 'include' }
        ).then(res => res.json());

        const assignmentsReq = fetch(
          `https://${CANVAS_DOMAIN}/api/v1/courses/${COURSE_ID}/assignments?per_page=100`,
          { credentials: 'include' }
        ).then(res => res.json());

        return Promise.all([submissionsReq, assignmentsReq])
          .then(([submissions, assignments]) => {
            // Build lookup map: assignment_id -> { title, points_possible }
            const assignmentMap = {};
            if (Array.isArray(assignments)) {
              assignments.forEach(a => {
                assignmentMap[a.id] = {
                  title: a.name,
                  points_possible: a.points_possible
                };
              });
            }

            // Join submissions with assignment metadata
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
          .catch(() => ({ COURSE_ID, courseName: course.name ?? `course_${COURSE_ID}`, data: [] }));
      });

      return Promise.all(requests).then(results => ({ user_data, results }));
    })
    .then(({ user_data, results }) => {
      browser.runtime.sendMessage({
        type: 'CANVAS_ASSIGNMENTS',
        payload: { user_data, courses: results },
        domain: CANVAS_DOMAIN
      });
    })
    .catch(err => console.error('[canBet] fetch failed:', err));
})();