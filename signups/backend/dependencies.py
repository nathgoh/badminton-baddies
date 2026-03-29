from fastapi import Request

try:
    from .storage.adapter import StorageAdapter
except ImportError:
    from storage.adapter import StorageAdapter


def get_storage(request: Request) -> StorageAdapter:
    return request.app.state.storage
