(() => {
  const CANVAS_DOMAIN = window.location.hostname;
  const IS_CANBET =
    CANVAS_DOMAIN === 'canbet.live' || CANVAS_DOMAIN === 'www.canbet.live';
  const IS_CANVAS =
    CANVAS_DOMAIN.endsWith('.instructure.com') &&
    !CANVAS_DOMAIN.includes('.login.instructure.com');

  function fetchCanvasJson(url, errorLabel) {
    return fetch(url, { credentials: 'include' })
      .then((res) => {
        const contentType = res.headers.get('content-type') || '';
        if (!res.ok) {
          throw new Error(`${errorLabel}: ${res.status}`);
        }
        if (!contentType.includes('application/json')) {
          throw new Error(`${errorLabel}: expected JSON`);
        }
        return res.json();
      });
  }

  if (IS_CANBET) {
    window.addEventListener('message', (event) => {
      if (event.source !== window) return;
      if (!event.data || event.data.type !== 'CANBET_TOKEN' || !event.data.token) return;

      chrome.runtime.sendMessage({
        type: 'CANBET_TOKEN',
        token: event.data.token,
      });
    });

    return;
  }

  if (!IS_CANVAS) return;

  fetchCanvasJson(
    `https://${CANVAS_DOMAIN}/api/v1/users/self`,
    'Failed to fetch user'
  )
    .then((user_data) => {
      const STUDENT_ID = user_data.id;

      return fetchCanvasJson(
        `https://${CANVAS_DOMAIN}/api/v1/courses?per_page=100&enrollment_state=active`,
        'Failed to fetch courses'
      )
        .then((courses) => ({ user_data, STUDENT_ID, courses }));
    })
    .then(({ user_data, STUDENT_ID, courses }) => {
      const requests = courses.map((course) => {
        const COURSE_ID = course.id;

        const submissionsReq = fetchCanvasJson(
          `https://${CANVAS_DOMAIN}/api/v1/courses/${COURSE_ID}/students/submissions?student_ids[]=${STUDENT_ID}&per_page=100`,
          `Failed submissions fetch for course ${COURSE_ID}`
        );

        const assignmentsReq = fetchCanvasJson(
          `https://${CANVAS_DOMAIN}/api/v1/courses/${COURSE_ID}/assignments?per_page=100`,
          `Failed assignments fetch for course ${COURSE_ID}`
        );

        return Promise.all([submissionsReq, assignmentsReq])
          .then(([submissions, assignments]) => {
            const assignmentMap = {};

            if (Array.isArray(assignments)) {
              assignments.forEach((a) => {
                assignmentMap[a.id] = {
                  title: a.name,
                  points_possible: a.points_possible,
                };
              });
            }

            const data = Array.isArray(submissions)
              ? submissions.map((sub) => ({
                  assignment_id: sub.assignment_id,
                  title: assignmentMap[sub.assignment_id]?.title ?? 'Unknown',
                  points_possible: assignmentMap[sub.assignment_id]?.points_possible ?? null,
                  score: sub.score,
                  submitted_at: sub.submitted_at,
                  workflow_state: sub.workflow_state,
                }))
              : [];

            return {
              COURSE_ID,
              courseName: course.name ?? `course_${COURSE_ID}`,
              data,
            };
          })
          .catch((err) => {
            console.error('[canBet] Course fetch failed:', err);
            return {
              COURSE_ID,
              courseName: course.name ?? `course_${COURSE_ID}`,
              data: [],
            };
          });
      });

      return Promise.all(requests).then((results) => ({ user_data, results }));
    })
    .then(({ user_data, results }) => {
      chrome.runtime.sendMessage({
        type: 'CANVAS_ASSIGNMENTS',
        payload: { user_data, courses: results },
        domain: CANVAS_DOMAIN,
      });
    })
    .catch((err) => {
      console.error('[canBet] fetch failed:', err);
    });
})();
