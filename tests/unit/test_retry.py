from app.recovery.retry_handler import should_retry

def test_transient_retry():
    assert should_retry("TRANSIENT",1)
    assert not should_retry("TRANSIENT",2)

def test_non_transient_no_retry():
    assert not should_retry("DUPLICATE",1)
