"""
Usage:
    python manage.py sync_canvas --user <username>
    python manage.py sync_canvas          # syncs ALL users with a canvas_user_id

Requires CANVAS_DOMAIN and CANVAS_TOKEN in .env (or Django settings).
On a successful sync the command awards Bits based on on-time submissions.
"""

import requests
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from canbet_app.models import CanBetUser, CanvasSubmission


# ── Bits awarded per on-time submission ────────────────────────────────────────
BITS_PER_SUBMISSION = 50


class Command(BaseCommand):
    help = 'Sync Canvas submission data and award Bits for on-time work.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Sync a single user by Django username.',
        )

    def handle(self, *args, **options):
        domain  = settings.CANVAS_DOMAIN
        token   = settings.CANVAS_TOKEN

        if not token:
            raise CommandError(
                'CANVAS_TOKEN is not set. Add it to your .env file.'
            )

        headers = {'Authorization': f'Bearer {token}'}

        # ── Select which users to sync ─────────────────────────────────────────
        if options['user']:
            users = CanBetUser.objects.filter(username=options['user'])
            if not users.exists():
                raise CommandError(f"User '{options['user']}' not found.")
        else:
            users = CanBetUser.objects.exclude(canvas_user_id=None).exclude(canvas_user_id='')

        for user in users:
            self.stdout.write(f'Syncing {user.username}…')
            self._sync_user(user, domain, token, headers)

        self.stdout.write(self.style.SUCCESS('Canvas sync complete.'))

    # ── Per-user sync ──────────────────────────────────────────────────────────
    def _sync_user(self, user, domain, token, headers):
        student_id = user.canvas_user_id

        # 1. Fetch courses
        resp = requests.get(
            f'{domain}/api/v1/courses?per_page=100&enrollment_state=active',
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            self.stderr.write(f'  Could not fetch courses for {user.username}: {resp.status_code}')
            return

        courses = resp.json()
        if isinstance(courses, dict) and 'errors' in courses:
            self.stderr.write(f'  Canvas error: {courses["errors"]}')
            return

        bits_earned = 0

        for course in courses:
            course_id   = str(course.get('id', ''))
            course_name = course.get('name', course_id)

            # 2. Fetch submissions for this student in this course
            url  = (f'{domain}/api/v1/courses/{course_id}/students/submissions'
                    f'?student_ids[]={student_id}&per_page=100')
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue

            submissions = resp.json()
            if not isinstance(submissions, list):
                continue

            for sub in submissions:
                assignment_id = str(sub.get('assignment_id', ''))
                submitted_at_raw = sub.get('submitted_at')
                submitted_at = parse_datetime(submitted_at_raw) if submitted_at_raw else None
                score        = sub.get('score')

                obj, created = CanvasSubmission.objects.update_or_create(
                    user=user,
                    course_id=course_id,
                    assignment_id=assignment_id,
                    defaults={
                        'course_name': course_name,
                        'submitted_at': submitted_at,
                        'score':        score,
                        'fetched_at':   timezone.now(),
                    }
                )

                # Award Bits only on newly-discovered on-time submissions
                if created and submitted_at:
                    bits_earned += BITS_PER_SUBMISSION

        if bits_earned:
            user.bit_balance += bits_earned
            user.save(update_fields=['bit_balance'])
            self.stdout.write(
                f'  → Awarded {bits_earned} Bits to {user.username} '
                f'(new balance: {user.bit_balance})'
            )
        else:
            self.stdout.write(f'  → No new submissions found for {user.username}.')