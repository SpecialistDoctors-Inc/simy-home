"""Distinguish a failed read/preflight from an uncertain provider write.

Providers are called serially under the controller's exclusive lock. An absent
remote receipt alone never proves that an admitted write was not attempted.
"""
from functools import wraps


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
