from django import template
import os
from urllib.parse import urlparse

register = template.Library()

@register.filter
def last_part(value, delimiter='/'):
    """
    URL veya dosya yolundan son parçayı (dosya adını) döndürür.
    
    Örnek:
    {{ "http://example.com/path/to/file.jpg"|last_part:"/" }} -> "file.jpg"
    {{ "/var/www/html/index.html"|last_part:"/" }} -> "index.html"
    """
    if not value:
        return ""
    
    # URL ise, path kısmını al
    parsed_url = urlparse(value)
    if parsed_url.netloc:
        path = parsed_url.path
    else:
        path = value
    
    # Son parçayı döndür
    parts = path.split(delimiter)
    return parts[-1] if parts else "" 