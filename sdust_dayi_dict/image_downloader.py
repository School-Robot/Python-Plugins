# image_downloader.py

import os
import uuid
import httpx
import random
from urllib.parse import urlparse

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

def download_image(url, save_dir):
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type:
                raise ValueError(f"Downloaded content is not an image: {content_type}")

            file_extension = os.path.splitext(urlparse(url).path)[1]
            if not file_extension:
                if 'jpeg' in content_type or 'jpg' in content_type:
                    file_extension = '.jpg'
                elif 'png' in content_type:
                    file_extension = '.png'
                elif 'gif' in content_type:
                    file_extension = '.gif'
                else:
                    file_extension = '.jpg'  # Default to .jpg if unable to determine

            # filename = f"{uuid.uuid4()}{file_extension}"
            # local_path = os.path.join(save_dir, filename)
            local_path = save_dir
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            return local_path
    except httpx.HTTPError as e:
        raise(f"HTTP error occurred while downloading image: {e}")
    except Exception as e:
        raise(f"An error occurred while downloading image: {e}")
    
    return None