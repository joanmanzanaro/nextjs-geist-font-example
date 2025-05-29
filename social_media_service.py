import requests
from typing import Optional

class SocialMediaService:
    def __init__(self, access_token: str, instagram_account_id: str):
        self.access_token = access_token
        self.instagram_account_id = instagram_account_id
        self.graph_api_url = "https://graph.facebook.com/v15.0"

    def create_media_container(self, image_url: str, caption: str) -> Optional[str]:
        url = f"{self.graph_api_url}/{self.instagram_account_id}/media"
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token
        }
        response = requests.post(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("id")
        else:
            print(f"Error creating media container: {response.text}")
            return None

    def publish_media(self, creation_id: str) -> bool:
        url = f"{self.graph_api_url}/{self.instagram_account_id}/media_publish"
        params = {
            "creation_id": creation_id,
            "access_token": self.access_token
        }
        response = requests.post(url, params=params)
        if response.status_code == 200:
            return True
        else:
            print(f"Error publishing media: {response.text}")
            return False

    def share_image(self, image_url: str, caption: str) -> bool:
        creation_id = self.create_media_container(image_url, caption)
        if not creation_id:
            return False
        return self.publish_media(creation_id)
