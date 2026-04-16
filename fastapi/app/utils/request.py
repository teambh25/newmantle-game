from fastapi import Request


def get_client_ip(request: Request) -> str:
    # Nginx sets X-Real-IP to $remote_addr; fall back to direct client if header is missing.
    return request.headers.get("X-Real-IP") or (
        request.client.host if request.client else "unknown"
    )
