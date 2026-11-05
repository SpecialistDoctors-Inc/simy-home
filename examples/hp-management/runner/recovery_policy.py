"""Conservative recovery decisions without credential or provider payload logs."""
import subprocess
from codex_worker import process_identity
from ledger import require


def retry_policy(value):
    require(isinstance(value,dict),'invalid_recovery_policy')
    result={'enabled':False,'max_retries':3,'base_delay_seconds':30,'stage_timeout_seconds':1800,**value}
    require(set(result)=={'enabled','max_retries','base_delay_seconds','stage_timeout_seconds'},'invalid_recovery_policy')
    require(type(result['enabled']) is bool,'invalid_recovery_policy')
    for field,low,high in [('max_retries',0,5),('base_delay_seconds',1,300),('stage_timeout_seconds',60,7200)]:
        require(type(result[field]) is int and low<=result[field]<=high,'invalid_recovery_policy')
    return result


def error_code(exc):
    value=str(exc)
    # Only fixed machine codes survive. Provider text may contain private data.
    if len(value)<=100 and value.isascii() and value.replace('_','').isalnum():return value
    return type(exc).__name__


def authentication_error(exc):
    seen=set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if getattr(exc,'status',None) in {401,403} or type(exc).__name__ in {'RefreshError','AuthenticationRequired'}:return True
        if str(exc)=='Google credential refresh failed':return True
        exc=exc.__cause__
    return False


def process_finished(record):
    """A read-only observation. This never grants permission to signal a PID."""
    if not isinstance(record,dict) or type(record.get('pid')) is not int or record['pid']<=0 or not record.get('identity'):return False
    try:current=process_identity(record['pid'])
    except subprocess.CalledProcessError:return True
    # A reused PID means the old process is gone, but the new process is owned
    # by somebody else and must not be touched.
    if not current or current!=record['identity']:return True
    try:state=subprocess.check_output(['ps','-p',str(record['pid']),'-o','stat='],text=True).strip()
    except subprocess.CalledProcessError:return True
    return state.startswith('Z')
