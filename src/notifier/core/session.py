from pathlib import Path
from typing import Dict, Any, Union
from notifier.core.events import SessionInfo, Provider


def extract_session(
    raw: Dict[str, Any],
    provider: Union[Provider, str] = Provider.CLAUDE_CODE,
) -> SessionInfo:
    """Extract session identity from a hook payload.

    Per D-05: Session identity = (session_id, cwd) composite key.
    Per D-03: Provider-aware session identity.
    Per D-04: Project display name = leaf directory from cwd.
    """
    session_id = raw.get("session_id", "unknown")
    cwd = raw.get("cwd", "")

    # Normalize provider string to Provider enum
    if isinstance(provider, str):
        try:
            provider = Provider(provider)
        except ValueError:
            provider = Provider.CLAUDE_CODE

    return SessionInfo(
        session_id=session_id,
        cwd=cwd,
        project_name=project_name(cwd),
        provider=provider,
    )


def project_name(cwd: str) -> str:
    """Derive a stable project display name from the working directory.

    Per D-04: leaf directory name. E.g., D:/code/my-project -> my-project.
    Empty or missing cwd -> "unknown".
    """
    if not cwd:
        return "unknown"
    parts = Path(cwd).parts
    return parts[-1] if parts else "unknown"
