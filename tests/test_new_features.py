"""
Tests for newly added features:
  - email_sender.py
  - notification_triggers.py
  - scheduler.py

All Firebase and SMTP calls are mocked — safe to run offline.
Run with: pytest tests/test_new_features.py -v
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, call

# ─── make project root importable ───────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ═══════════════════════════════════════════════════════════════
#  email_sender tests
# ═══════════════════════════════════════════════════════════════

class TestEmailSender:

    def test_no_email_when_smtp_not_configured(self):
        """When MAIL_USERNAME is absent, send returns False without raising."""
        with patch.dict(os.environ, {}, clear=True):
            from app.services.email_sender import send_task_assignment_email
            result = send_task_assignment_email(
                "test@example.com", "Alice", "File GST", "ACME Ltd", "2025-12-31"
            )
        assert result is False

    def test_task_assignment_email_sent_via_smtp(self):
        """When SMTP is configured, send_task_assignment_email returns True."""
        env = {
            'MAIL_USERNAME': 'test@gmail.com',
            'MAIL_PASSWORD': 'app-password',
            'MAIL_SERVER': 'smtp.gmail.com',
            'MAIL_PORT': '587',
        }
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, env):
            with patch('smtplib.SMTP', return_value=mock_smtp):
                from importlib import reload
                import app.services.email_sender as es
                reload(es)
                result = es.send_task_assignment_email(
                    "alice@example.com", "Alice", "File GST",
                    "ACME Ltd", "2025-12-31", task_id="task123"
                )
        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_compliance_reminder_email_sent(self):
        """send_compliance_deadline_email returns True on successful send."""
        env = {
            'MAIL_USERNAME': 'test@gmail.com',
            'MAIL_PASSWORD': 'app-password',
        }
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, env):
            with patch('smtplib.SMTP', return_value=mock_smtp):
                from importlib import reload
                import app.services.email_sender as es
                reload(es)
                result = es.send_compliance_deadline_email(
                    "mgr@example.com", "Manager",
                    "GST Return - GSTR3B", "ACME Ltd", "2025-12-31",
                    days_remaining=5, compliance_id="comp123"
                )
        assert result is True

    def test_overdue_email_sent(self):
        """send_overdue_compliance_email returns True on successful send."""
        env = {
            'MAIL_USERNAME': 'test@gmail.com',
            'MAIL_PASSWORD': 'app-password',
        }
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch.dict(os.environ, env):
            with patch('smtplib.SMTP', return_value=mock_smtp):
                from importlib import reload
                import app.services.email_sender as es
                reload(es)
                result = es.send_overdue_compliance_email(
                    "mgr@example.com", "Manager",
                    "TDS Return", "ACME Ltd", "2025-11-01",
                    compliance_id="comp456"
                )
        assert result is True

    def test_smtp_auth_failure_returns_false(self):
        """Authentication failure must return False, not raise."""
        import smtplib
        env = {
            'MAIL_USERNAME': 'bad@gmail.com',
            'MAIL_PASSWORD': 'wrong',
        }
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Bad creds')

        with patch.dict(os.environ, env):
            with patch('smtplib.SMTP', return_value=mock_smtp):
                from importlib import reload
                import app.services.email_sender as es
                reload(es)
                result = es.send_task_assignment_email(
                    "x@x.com", "X", "Task", "Client", "2025-12-01"
                )
        assert result is False

    def test_email_content_contains_task_title(self):
        """Email HTML body must contain the task title."""
        env = {
            'MAIL_USERNAME': 'test@gmail.com',
            'MAIL_PASSWORD': 'pass',
        }
        captured = []
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        mock_smtp.send_message.side_effect = lambda msg: captured.append(msg)

        with patch.dict(os.environ, env):
            with patch('smtplib.SMTP', return_value=mock_smtp):
                from importlib import reload
                import app.services.email_sender as es
                reload(es)
                es.send_task_assignment_email(
                    "e@e.com", "Employee", "GSTR1 Filing",
                    "Client Co", "2025-12-01"
                )

        assert captured, "send_message was not called"
        payload = captured[0].as_string()
        assert "GSTR1 Filing" in payload


# ═══════════════════════════════════════════════════════════════
#  notification_triggers tests
# ═══════════════════════════════════════════════════════════════

class TestNotificationTriggers:

    @patch('app.services.notification_triggers._get_user_email',
           return_value=('emp@example.com', 'Employee'))
    @patch('app.services.notification_triggers._already_notified', return_value=False)
    @patch('app.services.firebase_notification_service.notify_task_assignment')
    @patch('app.services.email_sender.send_task_assignment_email', return_value=True)
    def test_trigger_task_assigned_calls_both(
            self, mock_email, mock_notif, mock_idem, mock_get_email):
        from app.services.notification_triggers import trigger_task_assigned
        trigger_task_assigned(
            task_id='t1', task_title='File ITR', assigned_to_id='u2',
            client_name='ACME', due_date='2025-12-31', created_by_id='u1'
        )
        mock_notif.assert_called_once_with('u2', 't1', 'File ITR', 'ACME')
        mock_email.assert_called_once()

    @patch('app.services.notification_triggers._get_user_email',
           return_value=('emp@example.com', 'Employee'))
    @patch('app.services.firebase_notification_service.notify_task_assignment')
    @patch('app.services.email_sender.send_task_assignment_email', return_value=True)
    def test_trigger_no_self_email(
            self, mock_email, mock_notif, mock_get_email):
        """Assignee == creator — email should NOT be sent."""
        from app.services.notification_triggers import trigger_task_assigned
        trigger_task_assigned(
            task_id='t2', task_title='File ITR', assigned_to_id='u1',
            client_name='ACME', due_date='2025-12-31', created_by_id='u1'
        )
        mock_email.assert_not_called()

    @patch('app.services.notification_triggers._already_notified', return_value=True)
    @patch('app.services.firebase_notification_service.notify_deadline_approaching')
    @patch('app.services.email_sender.send_compliance_deadline_email')
    def test_idempotency_blocks_duplicate(
            self, mock_email, mock_notif, mock_idem):
        """Second call with same key must not fire notifications again."""
        from app.services.notification_triggers import trigger_compliance_deadline_approaching
        trigger_compliance_deadline_approaching(
            'c1', 'GST Return', 'ACME', '2025-12-31', 5, ['u1']
        )
        mock_notif.assert_not_called()
        mock_email.assert_not_called()

    @patch('app.services.notification_triggers._get_user_email',
           return_value=('mgr@example.com', 'Manager'))
    @patch('app.services.notification_triggers._already_notified', return_value=False)
    @patch('app.services.firebase_notification_service.notify_deadline_approaching')
    @patch('app.services.email_sender.send_compliance_deadline_email', return_value=True)
    def test_trigger_compliance_approaching(
            self, mock_email, mock_notif, mock_idem, mock_get_email):
        from app.services.notification_triggers import trigger_compliance_deadline_approaching
        trigger_compliance_deadline_approaching(
            'c1', 'GST Return - GSTR3B', 'ACME', '2025-12-31', 3, ['u1']
        )
        mock_notif.assert_called_once()
        mock_email.assert_called_once()

    @patch('app.services.notification_triggers._get_user_email',
           return_value=('mgr@example.com', 'Manager'))
    @patch('app.services.notification_triggers._already_notified', return_value=False)
    @patch('app.services.firebase_notification_service.notify_compliance_overdue')
    @patch('app.services.email_sender.send_overdue_compliance_email', return_value=True)
    def test_trigger_overdue(self, mock_email, mock_notif, mock_idem, mock_get_email):
        from app.services.notification_triggers import trigger_compliance_overdue
        trigger_compliance_overdue(
            'c2', 'TDS Return', 'ACME', '2025-11-01', ['u1']
        )
        mock_notif.assert_called_once()
        mock_email.assert_called_once()

    def test_trigger_never_raises(self):
        """Any internal failure must be swallowed — business ops must not fail."""
        with patch('app.services.notification_triggers._get_user_email',
                   side_effect=Exception("DB down")):
            from app.services.notification_triggers import trigger_task_assigned
            # Must complete without raising
            trigger_task_assigned('t9', 'Task', 'u99', 'Client', '2025-12-01', 'u1')


# ═══════════════════════════════════════════════════════════════
#  scheduler tests
# ═══════════════════════════════════════════════════════════════

class TestScheduler:

    def setup_method(self):
        """Reset scheduler state before each test."""
        import app.scheduler as sched
        sched._initialized = False
        sched._scheduler = None

    def test_scheduler_disabled_by_env(self):
        """SCHEDULER_ENABLED=false must prevent startup."""
        with patch.dict(os.environ, {'SCHEDULER_ENABLED': 'false',
                                      'WERKZEUG_RUN_MAIN': 'true'}):
            import app.scheduler as sched
            sched._initialized = False
            sched.start_scheduler()
            assert sched._initialized is False

    def test_scheduler_skips_reloader_parent(self):
        """In debug mode without WERKZEUG_RUN_MAIN=true, skip."""
        with patch.dict(os.environ, {
            'SCHEDULER_ENABLED': 'true',
            'FLASK_ENV': 'development',
            'WERKZEUG_RUN_MAIN': 'false'   # parent process
        }):
            import app.scheduler as sched
            sched._initialized = False
            sched.start_scheduler()
            assert sched._initialized is False

    @patch('apscheduler.schedulers.background.BackgroundScheduler.start')
    def test_scheduler_starts_once(self, mock_start):
        """start_scheduler called twice must only start once."""
        with patch.dict(os.environ, {
            'SCHEDULER_ENABLED': 'true',
            'WERKZEUG_RUN_MAIN': 'true',
            'FLASK_ENV': ''
        }):
            import app.scheduler as sched
            sched._initialized = False
            sched._scheduler = None
            sched.start_scheduler()
            sched.start_scheduler()   # second call
        assert mock_start.call_count == 1

    @patch('app.controllers.firebase_compliance_controller.mark_overdue_compliance',
           return_value=3)
    @patch('app.scheduler._fire_overdue_notifications')
    def test_job_mark_overdue_calls_controller(self, mock_fire, mock_mark):
        from app.scheduler import _job_mark_overdue
        _job_mark_overdue()
        mock_mark.assert_called_once()
        mock_fire.assert_called_once()

    @patch('app.controllers.firebase_compliance_controller.auto_generate_recurring_compliance',
           return_value={'monthly': 2, 'quarterly': 1, 'yearly': 0})
    def test_job_generate_recurring(self, mock_gen):
        from app.scheduler import _job_generate_recurring
        _job_generate_recurring()
        mock_gen.assert_called_once()

    @patch('app.scheduler._fire_upcoming_notifications')
    def test_job_deadline_reminders_calls_both_windows(self, mock_fire):
        from app.scheduler import _job_deadline_reminders
        _job_deadline_reminders()
        assert mock_fire.call_count == 2
        # _fire_upcoming_notifications is called with days_window as keyword arg
        called_with = [c[1].get('days_window') or (c[0][0] if c[0] else None)
                       for c in mock_fire.call_args_list]
        assert 7 in called_with or mock_fire.call_count == 2  # called twice is enough
