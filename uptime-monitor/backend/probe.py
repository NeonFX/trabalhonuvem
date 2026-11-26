"""Sondagem HTTP: aceita HTTP(S) públicos e duas rotas internas de demonstração."""
from dataclasses import dataclass
import http.client
import ipaddress
import socket
import ssl
from time import monotonic
from urllib.parse import quote, urlsplit, urlunsplit

DEMO_URLS = {'http://web/demo/online', 'http://web/demo/offline'}
TIMEOUT = 5


@dataclass(frozen=True)
class Result:
    online: bool
    status_code: int | None
    latency_ms: int
    error: str | None = None


def normalize_url(raw):
    raw = raw.strip()
    if not raw or len(raw) > 2048 or any(c.isspace() or ord(c) < 32 for c in raw):
        raise ValueError('Informe uma URL válida, sem espaços.')
    if '://' not in raw:
        raw = 'https://' + raw
    try:
        parts = urlsplit(raw)
        host = parts.hostname
        port = parts.port
        if parts.scheme not in ('http', 'https') or not host or parts.username or parts.password:
            raise ValueError()
        if port not in (None, 80, 443):
            raise ValueError()
        if ':' in host:
            host = '[' + host + ']'
        else:
            host = host.encode('idna').decode('ascii')
        netloc = host + (f':{port}' if port else '')
        normalized = urlunsplit((parts.scheme, netloc, quote(parts.path or '/', safe="/%:@!$&'()*+,;=-._~"), quote(parts.query, safe="/%?:@!$&'()*+,;=-._~"), ''))
        if len(normalized) > 2048:
            raise ValueError()
        return normalized
    except (ValueError, UnicodeError):
        raise ValueError('Use uma URL HTTP ou HTTPS válida, nas portas 80 ou 443.') from None


def public_address(host, port):
    """Resolve o DNS e bloqueia endereços privados, locais e reservados."""
    addresses = [entry[4][0] for entry in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]
    if not addresses or any(not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast for ip in addresses):
        raise ValueError('O endereço não é público.')
    return next((ip for ip in addresses if ipaddress.ip_address(ip).version == 4), addresses[0])


def validate_target(raw):
    url = normalize_url(raw)
    if url not in DEMO_URLS:
        host = urlsplit(url).hostname
        # A resolução efetiva ocorre no worker, com verificação do IP a cada sondagem.
        if '.' not in host and ':' not in host or host.endswith(('.local', '.localhost', '.internal')):
            raise ValueError('Use um domínio público ou os monitores de demonstração.')
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None
        if ip and (not ip.is_global or ip.is_multicast):
            raise ValueError('Endereços privados ou reservados não são permitidos.')
    return url


def check_url(url):
    started = monotonic()
    connection = None
    try:
        url = validate_target(url)
        parts = urlsplit(url)
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        host = parts.hostname
        address = host if url in DEMO_URLS else public_address(host, port)
        if parts.scheme == 'https':
            connection = http.client.HTTPSConnection(host, port, timeout=TIMEOUT, context=ssl.create_default_context())
        else:
            connection = http.client.HTTPConnection(host, port, timeout=TIMEOUT)
        # A conexão usa o IP já validado, enquanto HTTP Host e TLS SNI usam o domínio.
        connection._create_connection = lambda _addr, timeout, source_address=None: socket.create_connection((address, port), timeout, source_address)
        path = parts.path or '/'
        if parts.query:
            path += '?' + parts.query
        connection.request('GET', path, headers={'User-Agent': 'AcademicUptimeMonitor/1.0', 'Connection': 'close'})
        response = connection.getresponse()
        code = response.status
        online = 200 <= code < 400
        return Result(online, code, round((monotonic()-started)*1000), None if online else f'HTTP {code}')
    except (OSError, ValueError, http.client.HTTPException) as exc:
        return Result(False, None, round((monotonic()-started)*1000), str(exc)[:200])
    finally:
        if connection:
            connection.close()
