#!/usr/bin/env python

# Automatically generated file, see inline.py

# Copyright (c) 2014 Richard Moore
# Copyright (c) 2014 Jan Varho
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


# This is a pure-Python implementation of the Scrypt password-based key
# derivation function (PBKDF); see:
# http://en.wikipedia.org/wiki/Scrypt
# http://www.tarsnap.com/scrypt/scrypt.pdf

# It was originally written for a pure-Python Litecoin CPU miner:
# https://github.com/ricmoo/nightminer
# Imported to this project from:
# https://github.com/ricmoo/pyscrypt
# And owes thanks to:
# https://github.com/wg/scrypt


import base64
import hashlib, hmac
import os
import struct


import tests

from consts import *


# Python 3.4+ have PBKDF2 in hashlib, so use it...
if 'pbkdf2_hmac' in dir(hashlib):
    def _pbkdf2(passphrase, salt, count, olen, prf):
        return hashlib.pbkdf2_hmac('sha256', passphrase, salt, count, olen)
else:
    # but fall back to Python implementation in < 3.4
    from pbkdf2 import pbkdf2 as _pbkdf2


def scrypt(password, salt, N=SCRYPT_N, r=SCRYPT_r, p=SCRYPT_p, olen=64):
    """Returns the result of the scrypt password-based key derivation function

    Constraints:
        r * p < (2 ** 30)
        olen <= (((2 ** 32) - 1) * 32
        N must be a power of 2 greater than 1 (eg. 2, 4, 8, 16, 32...)
        N, r, p must be positive
    """

    def array_overwrite(source, s_start, dest, d_start, length):
        dest[d_start:d_start + length] = source[s_start:s_start + length]


    def blockxor(source, s_start, dest, d_start, length):
        for i in xrange(length):
            dest[d_start + i] ^= source[s_start + i]


    def integerify(B, r):
        '''"A bijection from ({0, 1} ** k) to {0, ..., (2 ** k) - 1"'''

        Bi = (2 * r - 1) * 16
        return B[Bi]


    def salsa20_8(B, x, src, s_start, dest, d_start):
        '''Salsa20/8 http://en.wikipedia.org/wiki/Salsa20'''

        # Merged blockxor for speed
        for i in xrange(16):
            x[i] = B[i] = B[i] ^ src[s_start + i]

        # This is the actual Salsa 20/8: four identical double rounds
        for i in xrange(4):
            a = (x[0]+x[12]) & 0xffffffff
            b = (x[5]+x[1]) & 0xffffffff
            x[4] ^= (a << 7) | (a >> 25)
            x[9] ^= (b << 7) | (b >> 25)
            a = (x[10]+x[6]) & 0xffffffff
            b = (x[15]+x[11]) & 0xffffffff
            x[14] ^= (a << 7) | (a >> 25)
            x[3] ^= (b << 7) | (b >> 25)
            a = (x[4]+x[0]) & 0xffffffff
            b = (x[9]+x[5]) & 0xffffffff
            x[8] ^= (a << 9) | (a >> 23)
            x[13] ^= (b << 9) | (b >> 23)
            a = (x[14]+x[10]) & 0xffffffff
            b = (x[3]+x[15]) & 0xffffffff
            x[2] ^= (a << 9) | (a >> 23)
            x[7] ^= (b << 9) | (b >> 23)
            a = (x[8]+x[4]) & 0xffffffff
            b = (x[13]+x[9]) & 0xffffffff
            x[12] ^= (a << 13) | (a >> 19)
            x[1] ^= (b << 13) | (b >> 19)
            a = (x[2]+x[14]) & 0xffffffff
            b = (x[7]+x[3]) & 0xffffffff
            x[6] ^= (a << 13) | (a >> 19)
            x[11] ^= (b << 13) | (b >> 19)
            a = (x[12]+x[8]) & 0xffffffff
            b = (x[1]+x[13]) & 0xffffffff
            x[0] ^= (a << 18) | (a >> 14)
            x[5] ^= (b << 18) | (b >> 14)
            a = (x[6]+x[2]) & 0xffffffff
            b = (x[11]+x[7]) & 0xffffffff
            x[10] ^= (a << 18) | (a >> 14)
            x[15] ^= (b << 18) | (b >> 14)
            a = (x[0]+x[3]) & 0xffffffff
            b = (x[5]+x[4]) & 0xffffffff
            x[1] ^= (a << 7) | (a >> 25)
            x[6] ^= (b << 7) | (b >> 25)
            a = (x[10]+x[9]) & 0xffffffff
            b = (x[15]+x[14]) & 0xffffffff
            x[11] ^= (a << 7) | (a >> 25)
            x[12] ^= (b << 7) | (b >> 25)
            a = (x[1]+x[0]) & 0xffffffff
            b = (x[6]+x[5]) & 0xffffffff
            x[2] ^= (a << 9) | (a >> 23)
            x[7] ^= (b << 9) | (b >> 23)
            a = (x[11]+x[10]) & 0xffffffff
            b = (x[12]+x[15]) & 0xffffffff
            x[8] ^= (a << 9) | (a >> 23)
            x[13] ^= (b << 9) | (b >> 23)
            a = (x[2]+x[1]) & 0xffffffff
            b = (x[7]+x[6]) & 0xffffffff
            x[3] ^= (a << 13) | (a >> 19)
            x[4] ^= (b << 13) | (b >> 19)
            a = (x[8]+x[11]) & 0xffffffff
            b = (x[13]+x[12]) & 0xffffffff
            x[9] ^= (a << 13) | (a >> 19)
            x[14] ^= (b << 13) | (b >> 19)
            a = (x[3]+x[2]) & 0xffffffff
            b = (x[4]+x[7]) & 0xffffffff
            x[0] ^= (a << 18) | (a >> 14)
            x[5] ^= (b << 18) | (b >> 14)
            a = (x[9]+x[8]) & 0xffffffff
            b = (x[14]+x[13]) & 0xffffffff
            x[10] ^= (a << 18) | (a >> 14)
            x[15] ^= (b << 18) | (b >> 14)

        # While we are handling the data, write it to the correct dest.
        # The latter half is still part of salsa20
        for i in xrange(16):
            dest[d_start + i] = B[i] = (x[i] + B[i]) & 0xffffffff


    def blockmix_salsa8(BY, Bi, Yi, r):
        '''Blockmix; Used by SMix'''

        start = Bi + (2 * r - 1) * 16
        X = BY[start:start+16]                             # BlockMix - 1
        tmp = [0]*16

        for i in xrange(2 * r):                            # BlockMix - 2
            #blockxor(BY, i * 16, X, 0, 16)                # BlockMix - 3(inner)
            salsa20_8(X, tmp, BY, i * 16, BY, Yi + i*16)   # BlockMix - 3(outer)
            #array_overwrite(X, 0, BY, Yi + (i * 16), 16)  # BlockMix - 4

        for i in xrange(r):                                # BlockMix - 6
            array_overwrite(BY, Yi + (i * 2) * 16, BY, Bi + (i * 16), 16)

        for i in xrange(r):
            array_overwrite(BY, Yi + (i*2 + 1) * 16, BY, Bi + (i + r) * 16, 16)


    def smix(B, Bi, r, N, V, X):
        '''SMix; a specific case of ROMix based on Salsa20/8'''

        array_overwrite(B, Bi, X, 0, 32 * r)               # ROMix - 1

        for i in xrange(N):                                # ROMix - 2
            array_overwrite(X, 0, V, i * (32 * r), 32 * r) # ROMix - 3
            blockmix_salsa8(X, 0, 32 * r, r)               # ROMix - 4

        for i in xrange(N):                                # ROMix - 6
            j = integerify(X, r) & (N - 1)                 # ROMix - 7
            blockxor(V, j * (32 * r), X, 0, 32 * r)        # ROMix - 8(inner)
            blockmix_salsa8(X, 0, 32 * r, r)               # ROMix - 9(outer)

        array_overwrite(X, 0, B, Bi, 32 * r)               # ROMix - 10


    if not isinstance(salt, bytes):
        raise TypeError('scrypt salt must be a byte string')
    if N < 2 or (N & (N - 1)):
        raise ValueError('scrypt N must be a power of 2 greater than 1')
    if r <= 0:
        raise ValueError('scrypt r must be positive')
    if p <= 0:
        raise ValueError('scrypt p must be positive')

    prf = lambda k, m: hmac.new(key=k, msg=m, digestmod=hashlib.sha256).digest()
    B  = _pbkdf2(password, salt, 1, p * 128 * r, prf)

    # Everything is lists of 32-bit uints for all but pbkdf2
    B  = list(struct.unpack('<%dI' % (len(B) // 4), B))
    XY = [0] * (64 * r)
    V  = [0] * (32 * r * N)

    for i in xrange(p):
        smix(B, i * 32 * r, r, N, V, XY)

    B = struct.pack('<%dI' % len(B), *B)
    return _pbkdf2(password, B, 1, olen, prf)


# deBruijn table for getting ilog2 for powers of two quickly
_scrypt_dbs = [
    0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8,
    31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9
]

def scrypt_mcf(password, salt=None, N=SCRYPT_N, r=SCRYPT_r, p=SCRYPT_p):
    """Derives a Modular Crypt Format hash using the scrypt KDF

    If no salt is given, 16 random bytes are generated using os.urandom."""
    if salt is None:
        salt = os.urandom(16)

    if r > 255:
        raise ValueError('scrypt_mcf r out of range [1,255]')
    if p > 255:
        raise ValueError('scrypt_mcf p out of range [1,255]')

    hash = scrypt(password, salt, N, r, p)

    h64 = base64.b64encode(hash)
    s64 = base64.b64encode(salt)

    t = _scrypt_dbs[((N * 0x077CB531) & 0xffffffff) >> 27]
    params = p + (r << 8) + (t << 16)

    return (
        SCRYPT_MCF_ID +
        ('$%06x' % params).encode() +
        b'$' + s64 +
        b'$' + h64
    )


def scrypt_mcf_check(mcf, password):
    """Returns True if the password matches the given MCF hash"""
    if not isinstance(mcf, bytes):
        raise TypeError
    if not isinstance(password, bytes):
        raise TypeError

    s = mcf.split(b'$')
    if not (mcf.startswith(SCRYPT_MCF_ID) and len(s) == 5):
        raise ValueError('Unrecognized MCF hash')

    params, s64, h64 = s[2:]
    params = base64.b16decode(params, True)
    salt = base64.b64decode(s64)
    hash = base64.b64decode(h64)

    if len(params) != 3:
        raise ValueError('Unrecognized MCF parameters')
    t, r, p = struct.unpack('3B', params)
    N = 2 ** t

    h = scrypt(password, salt, N=N, r=r, p=p)

    return hash == h


if __name__ == "__main__":
    print('Testing scrypt...')
    tests.run_tests(scrypt, scrypt_mcf, scrypt_mcf_check)
