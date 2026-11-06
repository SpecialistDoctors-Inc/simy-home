"""AWS secret references and fixed-origin Google identity verification."""
import json
import time
import urllib.parse
import urllib.request
from identity import AuthError


class Secrets:
    def __init__(self, client=None, clock=time.time):
        if client is None:
            import boto3
            client = boto3.client('secretsmanager')
        self.client, self.clock, self.cache = client, clock, {}

    def __call__(self, ref):
        if not ref or not ref.startswith('arn:aws:secretsmanager:'):
            raise AuthError('secret_not_configured')
        value = self.cache.get(ref)
        if not value or value[0] < self.clock() - 300:
            raw = self.client.get_secret_value(SecretId=ref).get('SecretString')
            if not isinstance(raw, str):
                raise AuthError('secret_not_configured')
            value = (self.clock(), raw); self.cache[ref] = value
        return value[1]


class Tokens:
    def __init__(self, private_key, issuer):
        import jwt
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        self.jwt, self.key, self.issuer = jwt, private_key, issuer.rstrip('/')
        self.public = load_pem_private_key(private_key.encode(), password=None).public_key()
        self.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.public))
        import hashlib
        self.kid = hashlib.sha256(json.dumps(self.jwk, sort_keys=True).encode()).hexdigest()[:24]
        self.jwk.update(kid=self.kid, use='sig', alg='RS256')

    def sign(self, claims):
        return self.jwt.encode(claims, self.key, algorithm='RS256', headers={'kid': self.kid})

    def verify(self, value):
        try:
            return self.jwt.decode(value, self.public, algorithms=['RS256'], audience=self.issuer + '/mcp',
                issuer=self.issuer, options={'require': ['exp','iat','sub','iss','aud','jti']})
        except self.jwt.PyJWTError:
            raise AuthError('invalid_access_token') from None


class GoogleExchange:
    def __init__(self, client):
        self.client = client

    def __call__(self, code, redirect, nonce):
        if not isinstance(code, str) or not 1 <= len(code) <= 4096:
            raise AuthError('invalid_google_code')
        import jwt
        payload = urllib.parse.urlencode({'client_id': self.client['client_id'],
            'client_secret': self.client['client_secret'], 'code': code, 'redirect_uri': redirect,
            'grant_type': 'authorization_code'}).encode()
        try:
            request = urllib.request.Request('https://oauth2.googleapis.com/token', data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(65537)
            if len(data) > 65536:
                raise ValueError()
            result = json.loads(data)
            keys = jwt.PyJWKClient('https://www.googleapis.com/oauth2/v3/certs', timeout=10)
            key = keys.get_signing_key_from_jwt(result['id_token'])
            profile = jwt.decode(result['id_token'], key.key, algorithms=['RS256'],
                audience=self.client['client_id'], issuer=['https://accounts.google.com','accounts.google.com'],
                options={'require': ['exp','iat','sub','iss','aud','nonce']})
            if profile.get('nonce') != nonce or profile.get('email_verified') is not True:
                raise ValueError()
            return profile
        except Exception:
            raise AuthError('google_identity_verification_failed') from None
