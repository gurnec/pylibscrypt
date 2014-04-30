
# First, try loading libscrypt
_done = False
try:
    from pylibscrypt import *
except ImportError:
    pass
else:
    _done = True

# If that didn't work, get the inlined Python version
if not _done:
    try:
        from pypyscrypt_inline import *
    except ImportError:
        pass
    else:
        _done = True

# Finally the non-inlined
if not _done:
    from pypyscrypt import *
