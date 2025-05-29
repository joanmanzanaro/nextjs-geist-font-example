import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin

class SocialMediaService:
    """Service for handling social media interactions, primarily Instagram."""
    
    API_VERSION = "v15.0"
    BASE_URL = "https://graph.facebook.com"
    
    def __init__(self, access_token: str, instagram_account_id: str):
        """
        Initialize the social media service.
        
        Args:
            access_token: Instagram/Facebook API access token
            instagram_account_id: Instagram business account ID
        """
        self.access_token = access_token
        self.instagram_account_id = instagram_account_id
        self.graph_api_url = urljoin(self.BASE_URL, self.API_VERSION)

    def _make_request(self, endpoint: str, params: Dict[str, Any], method: str = "POST") -> Optional[Dict[str, Any]]:
        """
        Make a request to the Instagram Graph API.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            method: HTTP method (default: POST)
            
        Returns:
            Response data if successful, None otherwise
        """
        try:
            url = f"{self.graph_api_url}/{endpoint}"
            params["access_token"] = self.access_token
            
            response = requests.request(method, url, params=params)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {str(e)}")
            if hasattr(response, 'text'):
                print(f"Response: {response.text}")
            return None

    def create_media_container(self, image_url: str, caption: str) -> Optional[str]:
        """
        Create a media container for Instagram posting.
        
        Args:
            image_url: URL of the image to post
            caption: Caption for the post
            
        Returns:
            Creation ID if successful, None otherwise
        """
        endpoint = f"{self.instagram_account_id}/media"
        params = {
            "image_url": image_url,
            "caption": caption
        }
        
        response = self._make_request(endpoint, params)
        return response.get("id") if response else None

    def publish_media(self, creation_id: str) -> bool:
        """
        Publish media using a creation ID.
        
        Args:
            creation_id: ID returned from create_media_container
            
        Returns:
            True if successful, False otherwise
        """
        endpoint = f"{self.instagram_account_id}/media_publish"
        params = {
            "creation_id": creation_id
        }
        
        response = self._make_request(endpoint, params)
        return bool(response)

    def share_image(self, image_url: str, caption: str) -> bool:
        """
        Share an image on Instagram.
        
        Args:
            image_url: URL of the image to share
            caption: Caption for the post
            
        Returns:
            True if successful, False otherwise
        """
        creation_id = self.create_media_container(image_url, caption)
        if not creation_id:
            return False
        return self.publish_media(creation_id)

    def verify_credentials(self) -> bool:
        """
        Verify that the provided credentials are valid.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        if not self.access_token or not self.instagram_account_id:
            return False
            
        endpoint = f"{self.instagram_account_id}"
        params = {}
        
        response = self._make_request(endpoint, params, method="GET")
        return bool(response)
