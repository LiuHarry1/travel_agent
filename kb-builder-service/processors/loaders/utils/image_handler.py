"""Image handling utilities for loaders."""
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import io

from utils.logger import get_logger

logger = get_logger(__name__)

# Optional imports
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class ImageHandler:
    """Handles image extraction, saving, and URL generation."""
    
    def __init__(self, static_dir: Path, base_url: str = ""):
        """
        Args:
            static_dir: Static files root directory
            base_url: Base URL for static files (e.g., http://localhost:8001)
        """
        self.static_dir = Path(static_dir)
        self.images_dir = self.static_dir / "images"
        self.base_url = base_url.rstrip('/') if base_url else ""
        
        # Ensure directory exists
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        if self.base_url:
            logger.info(f"ImageHandler initialized with base_url: '{self.base_url}'")
        else:
            logger.warning("ImageHandler initialized WITHOUT base_url (using relative paths)")
    
    def save_image(
        self, 
        image_data: bytes, 
        file_id: str, 
        image_counter: int, 
        ext: str = ".png"
    ) -> str:
        """
        Save image and return URL.
        
        Args:
            image_data: Image data as bytes
            file_id: File ID for naming
            image_counter: Image counter for unique naming
            ext: Image extension (default: .png)
        
        Returns:
            Image URL (full URL if base_url is set, otherwise relative path)
        """
        img_filename = f"{file_id}_image_{image_counter}{ext}"
        img_path = self.images_dir / img_filename
        
        with open(img_path, 'wb') as f:
            f.write(image_data)
        
        logger.debug(f"Saved image to: {img_path}")
        
        # Generate image URL
        relative_path = f"/static/images/{img_filename}"
        if self.base_url:
            full_url = f"{self.base_url}{relative_path}"
            logger.info(f"Generated image URL with base_url: {full_url}")
            return full_url
        else:
            logger.warning(f"Generated image URL (relative): {relative_path}")
            return relative_path
    
    def detect_image_format(self, image_data: bytes, default_ext: str = ".png") -> str:
        """
        Detect image format from image data.
        
        Args:
            image_data: Image data as bytes
            default_ext: Default extension if detection fails
        
        Returns:
            Image extension (e.g., .png, .jpg)
        """
        if not HAS_PIL:
            return default_ext
        
        try:
            img = Image.open(io.BytesIO(image_data))
            return f".{img.format.lower()}" if img.format else default_ext
        except Exception:
            return default_ext
    
    def download_image(self, url: str, timeout: int = 10) -> Optional[tuple[bytes, str]]:
        """
        Download image from URL.
        
        Args:
            url: Image URL
            timeout: Request timeout in seconds
        
        Returns:
            Tuple of (image_data, extension) or None if download fails
        """
        if not HAS_REQUESTS:
            logger.warning("requests not available, cannot download image")
            return None
        
        try:
            response = requests.get(url, timeout=timeout, stream=True)
            if response.status_code == 200:
                img_data = response.content
                
                # Determine extension from Content-Type or URL
                content_type = response.headers.get('Content-Type', '')
                if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                    img_ext = '.jpg'
                elif 'image/png' in content_type:
                    img_ext = '.png'
                elif 'image/gif' in content_type:
                    img_ext = '.gif'
                else:
                    img_ext = Path(urlparse(url).path).suffix or '.png'
                
                return (img_data, img_ext)
        except Exception as e:
            logger.warning(f"Failed to download image {url}: {e}")
        
        return None
    
    def resolve_image_path(self, src: str, base_path: Path) -> Optional[Path]:
        """
        Resolve image path from relative or absolute path.
        
        Args:
            src: Image source path (relative or absolute)
            base_path: Base path for resolving relative paths
        
        Returns:
            Resolved Path or None if not found
        """
        if src.startswith('http://') or src.startswith('https://'):
            # Network image, return None (should use download_image instead)
            return None
        
        if src.startswith('/'):
            # Absolute path (relative to website root)
            img_path_abs = Path(base_path.parent / src.lstrip('/')).resolve()
        else:
            # Relative path
            img_path_abs = (base_path.parent / src).resolve()
        
        if img_path_abs.exists() and img_path_abs.is_file():
            return img_path_abs
        
        return None
