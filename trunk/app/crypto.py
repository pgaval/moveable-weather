# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Cryptographic operations."""

__author__ = 'Ka-Ping Yee <kpy@google.com>'

import hashlib
import hmac
import pickle
import time


def sha256_hmac(key, bytes):
    """Computes a hexadecimal HMAC using the SHA256 digest algorithm."""
    return hmac.new(key, bytes, digestmod=hashlib.sha256).hexdigest()


def sign(key, data, lifetime=None):
    """Produces a signature for the given data.  If 'lifetime' is specified,
    the signature expires in 'lifetime' seconds; otherwise it never expires."""
    expiry = lifetime and int(time.time() + lifetime) or 0
    bytes = pickle.dumps((data, expiry))
    return sha256_hmac(key, bytes) + '.' + str(expiry)


def verify(key, data, signature):
    """Checks that a signature matches the given data and hasn't expired."""
    try:
        mac, expiry = signature.split('.', 1)
        expiry = int(expiry)
    except ValueError:
        return False
    if expiry == 0 or time.time() < expiry:
        bytes = pickle.dumps((data, expiry))
        return sha256_hmac(key, bytes) == mac
