import base64
import hashlib

from Crypto import Random
from Crypto.Cipher import AES


def gen_token(length):
    import random
    import string
    return ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(32))


class AESCipher(object):

    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]

    def encrypt(self, raw):
        raw = self._pad(raw).encode('utf-8')
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw)).decode('utf-8')

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)


class AESCipherADA(object):

    def __init__(self, key):
        self.bs = AES.block_size
        self.key = bytes(key, encoding="utf-8")

    def encrypt(self, string):
        string_bytes = string.encode("utf-8")
        string_bytes = self._pad(string_bytes)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(string_bytes))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode("utf-8")

    def _pad(self, data):
        length = self.bs - (len(data) % self.bs)
        data += bytes([length]) * length
        return data

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]
