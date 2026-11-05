"""Distinguish a failed read/preflight from an uncertain provider write.

Providers are called serially under the controller's exclusive lock. An absent
remote receipt alone never proves that an admitted write was not attempted.
"""
from functools import wraps


class AuthenticationRequired(RuntimeError):
    """A provider credential or authorization failure safe to persist.

    The exception deliberately carries only a fixed provider code and the
    HTTP status when it is 401 or 403.  Provider response text can contain an
    account identifier, token diagnostics, or a user-entered value and must
    remain only on the exception chain, never in durable recovery state.
    """

    def __init__(self, provider: str, code: str, status: int | None = None):
        allowed = {
            'google': {'google_auth_refresh_required', 'google_http_401', 'google_http_403'},
            # Codex login status is local preflight, so there is no trusted
            # HTTP status to retain.  Do not serialize CLI output.
            'codex': {'codex_auth_required'},
        }
        if provider not in allowed or code not in allowed[provider]:
            raise ValueError('invalid authentication error')
        if (provider == 'google' and status not in {None, 401, 403}) or (provider == 'codex' and status is not None):
            raise ValueError('invalid authentication status')
        super().__init__(code)
        self.provider = provider
        self.code = code
        self.status = status


def safe_provider_code(error):
    """Return only controller-safe authentication fields, or ``None``.

    Recovery code calls this instead of serializing an exception or a provider
    response.  ``EffectNotStarted`` wrapping does not hide a cause: callers
    can walk ``__cause__`` before calling this helper.
    """

    if not isinstance(error, AuthenticationRequired):
        return None
    return {'provider': error.provider, 'code': error.code, 'status': error.status}


class EffectNotStarted(RuntimeError):
    """The current invocation failed before attempting any mutating HTTP call."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def note_write_attempt(provider):
    tracker = getattr(provider, '_effect_write_tracker', None)
    if tracker is not None:
        tracker['attempted'] = True


def classify_effect(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        previous = getattr(self, '_effect_write_tracker', None)
        tracker = previous if previous is not None else {'attempted': False}
        self._effect_write_tracker = tracker
        try:
            return method(self, *args, **kwargs)
        except Exception as error:
            if not tracker['attempted']:
                raise EffectNotStarted(method.__name__ + '_preflight_failed') from error
            raise
        finally:
            self._effect_write_tracker = previous
    return wrapped
