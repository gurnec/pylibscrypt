#!/usr/bin/env python

import base64
import ctypes, ctypes.util
import os

from ctypes import c_char_p, c_size_t, c_uint64, c_uint32


_libscrypt_soname = ctypes.util.find_library('scrypt')
if _libscrypt_soname is None:
    raise ImportError('Unable to find libscrypt')

try:
    _libscrypt = ctypes.CDLL(_libscrypt_soname)
except OSError:
    raise ImportError('Unable to load libscrypt: ' + _libscrypt_soname)


try:
    _libscrypt_scrypt = _libscrypt.libscrypt_scrypt
except AttributeError:
    raise ImportError('Incompatible libscrypt: ' + _libscrypt_soname)

_libscrypt_scrypt.argtypes = [
    c_char_p,  # password
    c_size_t,  # password length
    c_char_p,  # salt
    c_size_t,  # salt length
    c_uint64,  # N
    c_uint32,  # r
    c_uint32,  # p
    c_char_p,  # out
    c_size_t,  # out length
]


try:
    _libscrypt_mcf = _libscrypt.libscrypt_mcf
except AttributeError:
    raise ImportError('Incompatible libscrypt: ' + _libscrypt_soname)

_libscrypt_mcf.argtypes = [
    c_uint64,  # N
    c_uint32,  # r
    c_uint32,  # p
    c_char_p,  # salt
    c_char_p,  # hash
    c_char_p,  # out (125+ bytes)
]


try:
    _libscrypt_check = _libscrypt.libscrypt_check
except AttributeError:
    raise ImportError('Incompatible libscrypt: ' + _libscrypt_soname)

_libscrypt_check.argtypes = [
    c_char_p,  # mcf (modified)
    c_char_p,  # hash
]


SCRYPT_MCF_ID = b"$s1"
SCRYPT_MCF_LEN = 125

SCRYPT_N = 1<<14
SCRYPT_r = 8
SCRYPT_p = 1 # Note: Value differs from libscrypt, see below.


def scrypt(password, salt, N=SCRYPT_N, r=SCRYPT_r, p=SCRYPT_p, olen=64):
    """Derives a 64-byte hash using the scrypt key-derivarion function.

    Memory usage is proportional to N*r. Defaults require about 16 MiB.
    Time taken is proportional to N*p. Defaults take <100ms of a recent x86.

    The default values are:
    N -- 2**14 (~16k)
    r -- 8
    p -- 1

    The last one differs from libscrypt defaults, but matches the 'interactive'
    work factor from the original paper. For long term storage where runtime of
    key derivation is not a problem, you could use 16 as in libscrypt or better
    yet increase N if memory is plentiful.
    """
    if not isinstance(password, bytes):
        raise TypeError
    if not isinstance(salt, bytes):
        raise TypeError

    out = ctypes.create_string_buffer(olen)
    ret = _libscrypt_scrypt(password, len(password), salt, len(salt),
                          N, r, p, out, len(out))
    if ret:
        raise ValueError

    return out.raw


def scrypt_mcf(password, salt=None, N=SCRYPT_N, r=SCRYPT_r, p=SCRYPT_p):
    """Derives a Modular Crypt Format hash using the scrypt KDF.

    If no salt is given, 16 random bytes are generated using os.urandom."""
    if salt is None:
        salt = os.urandom(16)
    hash = scrypt(password, salt, N, r, p)

    h64 = base64.b64encode(hash)
    s64 = base64.b64encode(salt)

    out = ctypes.create_string_buffer(SCRYPT_MCF_LEN)
    ret = _libscrypt_mcf(N, r, p, s64, h64, out)
    if not ret:
        raise ValueError

    return out.raw.strip(b'\0')


def scrypt_mcf_check(mcf, password):
    """Returns True if the password matches the given MCF hash"""
    if not isinstance(mcf, bytes):
        raise TypeError
    if not isinstance(password, bytes):
        raise TypeError

    mcfbuf = ctypes.create_string_buffer(mcf)
    ret = _libscrypt_check(mcfbuf, password)
    if ret < 0:
        raise ValueError

    return bool(ret)


if __name__ == "__main__":
    print('Testing scrypt...')

    test_vectors = (
        (b'password', b'NaCl', 1024, 8, 16,
         b'fdbabe1c9d3472007856e7190d01e9fe7c6ad7cbc8237830e77376634b373162'
         b'2eaf30d92e22a3886ff109279d9830dac727afb94a83ee6d8360cbdfa2cc0640',
         b'$s1$0a0810$TmFDbA==$/bq+HJ00cgB4VucZDQHp/nxq18vII3gw53N2Y0s3MWIu'
         b'rzDZLiKjiG/xCSedmDDaxyevuUqD7m2DYMvfoswGQA=='),
        (b'pleaseletmein', b'SodiumChloride', 16384, 8, 1,
         b'7023bdcb3afd7348461c06cd81fd38ebfda8fbba904f8e3ea9b543f6545da1f2'
         b'd5432955613f0fcf62d49705242a9af9e61e85dc0d651e40dfcf017b45575887',
         b'$s1$0e0801$U29kaXVtQ2hsb3JpZGU=$cCO9yzr9c0hGHAbNgf046/2o+7qQT44+'
         b'qbVD9lRdofLVQylVYT8Pz2LUlwUkKpr55h6F3A1lHkDfzwF7RVdYhw=='),
    )
    i = fails = 0
    for pw, s, n, r, p, h, m in test_vectors:
        i += 1
        h2 = scrypt(pw, s, n, r, p)
        if h2 != base64.b16decode(h, True):
            print("Test %d.1 failed!" % i)
            print("  scrypt('%s', '%s', %d, %d, %d)" % (pw, s, n, r, p))
            print("  Expected: %s" % h)
            print("  Got:      %s" % base64.b16encode(h2))
            fails += 1
        m2 = scrypt_mcf(pw, s, N=n, p=p, r=r)
        if m != m2:
            print("Test %d.1.5 failed!" % i)
            print("  scrypt_mcf('%s', '%s', %d, %d, %d)" % (pw, s, n, r, p))
            print("  Expected: %s" % m)
            print("  Got:      %s" % m2)
            print("  scrypt_mcf_check failed!")
            fails += 1
        if not (scrypt_mcf_check(m, pw) and scrypt_mcf_check(m2, pw)):
            print("Test %d.2 failed!" % i)
            print("  scrypt_mcf('%s', '%s', %d, %d, %d)" % (pw, s, n, r, p))
            print("  Expected: %s" % m)
            print("  Got:      %s" % m2)
            print("  scrypt_mcf_check failed!")
            fails += 1
        if scrypt_mcf_check(m, b'X' + pw) or scrypt_mcf_check(m2, b'X' + pw):
            print("Test %d.3 failed!" % i)
            print("  scrypt_mcf_check succeeded with wrong password!")
            fails += 1

    i += 1
    try:
        scrypt(u'password', b'salt')
    except TypeError:
        pass
    else:
        print("Test %d failed!" % i)
        print("  Unicode password accepted")
        fails += 1

    i += 1
    try:
        scrypt(b'password', u'salt')
    except TypeError:
        pass
    else:
        print("Test %d failed!" % i)
        print("  Unicode salt accepted")
        fails += 1

    i += 1
    try:
        scrypt(b'password', b'salt', N=-1)
    except ValueError:
        pass
    else:
        print("Test %d failed!" % i)
        print("  Invalid N value accepted")
        fails += 1

    i += 1
    if scrypt_mcf(b'password', b'salt') != scrypt_mcf(b'password', b'salt'):
        print("Test %d.1 failed!" % i)
        print("  Inconsistent MCF!")
        fails += 1
    if scrypt_mcf(b'password') == scrypt_mcf(b'password'):
        print("Test %d.2 failed!" % i)
        print("  Random salts match!")
        fails += 1

    i += 1
    try:
        mcf = scrypt_mcf(b'password', b's'*100)
    except ValueError:
        pass
    else:
        if len(mcf) < 150:
            print("Test %d failed!" % i)
            print("  Long salt truncated by scrypt_mcf")
            fails += 1

    i += 1
    try:
        scrypt_mcf_check(42, b'password')
    except TypeError:
        pass
    else:
        print("Test %d failed!" % i)
        print("  Non-string MCF accepted")
        fails += 1

    i += 1
    try:
        scrypt_mcf_check(b'mcf', 42)
    except TypeError:
        pass
    else:
        print("Test %d failed!" % i)
        print("  Non-string password accepted")
        fails += 1

    i += 1
    try:
        scrypt_mcf_check(b'mcf', b'password')
    except ValueError:
        pass
    else:
        print("Test %d failed!" % i)
        print("  Invalid MCF not reported")
        fails += 1

    if fails:
        print("%d tests failed!" % fails)
    else:
        print("All tests successful!")

