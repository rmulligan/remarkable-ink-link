"""Syntax highlighting controller for API endpoints."""

from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from pydantic import BaseModel

from inklink.services.augmented_notebook_service import AugmentedNotebookServiceV2
from inklink.services.syntax_highlight_service import SyntaxHighlightCompilerV2
from inklink.di.service_provider import ServiceProvider


class HighlightRequest(BaseModel):
    """Request model for syntax highlighting."""

    code: str
    language: str
    theme: str = "monokai"
    format: str = "html"  # html or hcl


class ThemeListResponse(BaseModel):
    """Response model for theme list."""

    themes: List[Dict[str, any]]


class SettingsResponse(BaseModel):
    """Response model for settings."""

    remarkableToken: Optional[str] = None
    myscriptKey: Optional[str] = None
    myscriptHmac: Optional[str] = None
    uploadFolder: str = "/Syntax Highlighted"
    autoUpload: bool = False


class AuthRequest(BaseModel):
    """Request model for authentication."""

    deviceToken: Optional[str] = None
    apiKey: Optional[str] = None
    hmacKey: Optional[str] = None


class CloudSettingsRequest(BaseModel):
    """Request model for cloud settings."""

    uploadFolder: str
    autoUpload: bool


router = APIRouter(prefix="/syntax", tags=["syntax"])

# Settings storage (in production, use a proper database or config system)
_settings = {
    "remarkableToken": None,
    "myscriptKey": None,
    "myscriptHmac": None,
    "uploadFolder": "/Syntax Highlighted",
    "autoUpload": False,
}

# Theme storage directory
THEMES_DIR = Path("themes")
THEMES_DIR.mkdir(exist_ok=True)


def get_syntax_service(
    service_provider: ServiceProvider = Depends(),
) -> SyntaxHighlightCompilerV2:
    """Get syntax highlighting service instance."""
    return service_provider.get(SyntaxHighlightCompilerV2)


def get_notebook_service(
    service_provider: ServiceProvider = Depends(),
) -> AugmentedNotebookServiceV2:
    """Get augmented notebook service instance."""
    return service_provider.get(AugmentedNotebookServiceV2)


@router.get("/themes", response_model=ThemeListResponse)
async def list_themes(
    syntax_service: SyntaxHighlightCompilerV2 = Depends(get_syntax_service),
) -> ThemeListResponse:
    """List all available themes."""
    themes = []

    # Add built-in themes
    for theme_name in ["monokai", "dark", "light"]:
        themes.append({"name": theme_name, "isBuiltIn": True})

    # Add custom themes from directory
    for theme_file in THEMES_DIR.glob("*.json"):
        themes.append({"name": theme_file.stem, "isBuiltIn": False})

    return ThemeListResponse(themes=themes)


@router.post("/themes")
async def upload_theme(
    name: str = Form(...),
    file: UploadFile = File(...),
    syntax_service: SyntaxHighlightCompilerV2 = Depends(get_syntax_service),
):
    """Upload a custom theme."""
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Theme file must be JSON")

    try:
        content = await file.read()
        # Validate JSON content
        import json

        json.loads(content)  # Validate that it's valid JSON

        # Save theme file
        theme_path = THEMES_DIR / f"{name}.json"
        theme_path.write_bytes(content)

        return {"message": f"Theme '{name}' uploaded successfully"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes/{theme_name}")
async def get_theme(
    theme_name: str,
    syntax_service: SyntaxHighlightCompilerV2 = Depends(get_syntax_service),
):
    """Get details of a specific theme."""
    # Check if it's a built-in theme
    if theme_name in ["monokai", "dark", "light"]:
        return {
            "name": theme_name,
            "isBuiltIn": True,
            "colors": {},  # TODO: Return actual theme colors
        }

    # Check custom themes
    theme_path = THEMES_DIR / f"{theme_name}.json"
    if theme_path.exists():
        import json

        with open(theme_path) as f:
            theme_data = json.load(f)
        return {"name": theme_name, "isBuiltIn": False, "colors": theme_data}

    raise HTTPException(status_code=404, detail="Theme not found")


@router.delete("/themes/{theme_name}")
async def delete_theme(
    theme_name: str,
    syntax_service: SyntaxHighlightCompilerV2 = Depends(get_syntax_service),
):
    """Delete a custom theme."""
    if theme_name in ["monokai", "dark", "light"]:
        raise HTTPException(status_code=400, detail="Cannot delete built-in themes")

    theme_path = THEMES_DIR / f"{theme_name}.json"
    if not theme_path.exists():
        raise HTTPException(status_code=404, detail="Theme not found")

    try:
        theme_path.unlink()
        return {"message": f"Theme '{theme_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/highlight")
async def highlight_code(
    request: HighlightRequest,
    syntax_service: SyntaxHighlightCompilerV2 = Depends(get_syntax_service),
    notebook_service: AugmentedNotebookServiceV2 = Depends(get_notebook_service),
):
    """Highlight code with the specified theme and format."""
    try:
        # Create syntax scanner and parse code
        from inklink.services.syntax_scanner import ScannerFactory

        scanner = ScannerFactory.create_scanner(request.language)
        if not scanner:
            raise HTTPException(
                status_code=400, detail=f"Unsupported language: {request.language}"
            )

        tokens = scanner.scan(request.code)

        # Apply theme and compile to HCL
        hcl_content = syntax_service.compile(tokens, request.theme)

        if request.format == "hcl":
            return {"hcl": hcl_content}

        # Convert to HTML for preview (simplified version)
        html_content = f"""
        <div class="syntax-highlight">
            <pre><code>{request.code}</code></pre>
        </div>
        <style>
            .syntax-highlight {{ background: #272822; color: #f8f8f2; padding: 1em; }}
            .syntax-highlight pre {{ margin: 0; }}
        </style>
        """

        return {"html": html_content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process_file")
async def process_file(
    file_id: str,
    theme: str = "monokai",
    syntax_service: SyntaxHighlightCompilerV2 = Depends(get_syntax_service),
    notebook_service: AugmentedNotebookServiceV2 = Depends(get_notebook_service),
):
    """Process a file for syntax highlighting."""
    try:
        # TODO: Implement file processing logic
        # This would integrate with the existing InkLink pipeline
        return {"response_id": "placeholder", "status": "processing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Settings endpoints (should be in a separate controller in production)
@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current settings."""
    return SettingsResponse(**_settings)


@router.post("/auth/remarkable")
async def save_remarkable_auth(request: AuthRequest):
    """Save reMarkable authentication."""
    if request.deviceToken:
        _settings["remarkableToken"] = request.deviceToken
        return {"message": "reMarkable authentication saved"}
    raise HTTPException(status_code=400, detail="Device token required")


@router.post("/auth/myscript")
async def save_myscript_auth(request: AuthRequest):
    """Save MyScript authentication."""
    if request.apiKey and request.hmacKey:
        _settings["myscriptKey"] = request.apiKey
        _settings["myscriptHmac"] = request.hmacKey
        return {"message": "MyScript authentication saved"}
    raise HTTPException(status_code=400, detail="API key and HMAC key required")


@router.post("/settings/cloud")
async def save_cloud_settings(request: CloudSettingsRequest):
    """Save cloud upload settings."""
    _settings["uploadFolder"] = request.uploadFolder
    _settings["autoUpload"] = request.autoUpload
    return {"message": "Cloud settings saved"}
