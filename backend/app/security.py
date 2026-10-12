"""Local API safeguards; these do not replace authentication for public hosting."""
import asyncio
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit

from starlette.responses import JSONResponse


class SecurityMiddleware:
    MAX_BODY_BYTES = 32768
    MUTATING_PATHS = {'/api/insights', '/api/reviews/translations'}

    def __init__(self, app, *, origins, hosts):
        self.app = app
        self.origins = set(origins)
        self.hosts = set(hosts)
        self.calls = defaultdict(deque)
        self.lock = Lock()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = {key.decode('latin1').lower(): value.decode('latin1') for key, value in scope['headers']}
        async def reject(status, detail):
            return await JSONResponse({'detail': detail}, status_code=status)(scope, receive, send)
        # Next's fixed upstream Host must not conceal a browser's untrusted Host.
        forwarded = headers.get('x-forwarded-host')
        if forwarded:
            try:
                hostname = urlsplit('http://' + forwarded).hostname
            except ValueError:
                hostname = None
            if hostname not in self.hosts:
                return await reject(400, 'Invalid forwarded host')
        if scope['method'] == 'POST' and scope['path'] in self.MUTATING_PATHS:
            origin = headers.get('origin')
            if origin and origin not in self.origins:
                return await reject(403, 'Origin is not allowed')
            if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                return await reject(415, 'Expected application/json')
            try:
                length = int(headers.get('content-length', '0'))
            except ValueError:
                return await reject(400, 'Invalid content length')
            if length < 0 or length > self.MAX_BODY_BYTES:
                return await reject(413, 'Request body is too large')
            chunks=[];size=0
            try:
                while True:
                    message = await asyncio.wait_for(receive(), timeout=10)
                    if message['type'] == 'http.disconnect':
                        return
                    body=message.get('body', b'');size+=len(body)
                    if size>self.MAX_BODY_BYTES:
                        return await reject(413, 'Request body is too large')
                    chunks.append(body)
                    if not message.get('more_body', False):break
            except TimeoutError:
                return await reject(408, 'Request body timed out')
            # Ignore client-controlled forwarding IP headers. One server process,
            # bounded per-minute quota; a shared limiter is needed for scaling.
            client=(scope.get('client') or ('unknown',))[0]
            now=monotonic()
            with self.lock:
                if client not in self.calls and len(self.calls)>=1024:
                    for key in list(self.calls):
                        if not self.calls[key] or self.calls[key][-1]<=now-60:del self.calls[key]
                if client not in self.calls and len(self.calls)>=1024:
                    limited=True
                else:
                    queue=self.calls[client]
                    while queue and queue[0] <= now-60:queue.popleft()
                    limited=len(queue)>=30
                    if not limited:queue.append(now)
            if limited:
                return await reject(429, 'Too many requests; try again later')
            body=b''.join(chunks);del chunks
            delivered=False
            original_receive=receive
            async def replay():
                nonlocal delivered
                if delivered:return await original_receive()
                delivered=True
                return {'type':'http.request','body':body,'more_body':False}
            receive=replay
        async def secured_send(message):
            if message['type']=='http.response.start':
                response_headers=list(message.get('headers',[]))
                response_headers.extend([(b'x-content-type-options',b'nosniff'),(b'x-frame-options',b'DENY'),
                                         (b'referrer-policy',b'no-referrer'),(b'cache-control',b'no-store')])
                message={**message,'headers':response_headers}
            await send(message)
        return await self.app(scope, receive, secured_send)
