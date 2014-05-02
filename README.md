Scrypt for Python
==

There are a lot of different scrypt modules for Python, but none of them have
everything that I'd like, so here's One More[1].

Features
--
* Uses system libscrypt[2] as the first choice.
* If that isn't available, tries the scrypt Python module[3].
* Offers a pure Python scrypt implementation for when there's no C scrypt.
* Not unusably slow, even in pure Python... at least with pypy[4].
  (Around one fifth the C speed, anyway.)

Requirements
--
* Python 2.7 or 3.4 or so. Pypy 2.2 also works. Older versions may or may not.
* If you want speed: libscrypt 1.8+ (older may work) or py-scrypt 0.6+

Usage
--

    from pylibscrypt import *
    # Print a raw scrypt hash in hex
    print(scrypt('Hello World', 'salt').encode('hex'))
    # Generate an MCF hash with random salt
    mcf = scrypt_mcf('Hello World')
    # Test it
    print(scrypt_mcf_check(mcf, 'Hello World'))
    print(scrypt_mcf_check(mcf, 'HelloPyWorld'))

Testing
--
tests.py tests both implementations with some quick tests. Running either
implementation directly will also compare to scrypt test vectors from the paper
but this is slow for the Python version unless you have pypy.

run_coverage.sh uses coverage.py[5] to report test coverage.

TODO
--
* Embed C implementation for when there's no system library?

[1]:https://xkcd.com/927/
[2]:https://github.com/technion/libscrypt
[3]:https://bitbucket.org/mhallin/py-scrypt/src
[4]:http://pypy.org/
[5]:http://nedbatchelder.com/code/coverage/

