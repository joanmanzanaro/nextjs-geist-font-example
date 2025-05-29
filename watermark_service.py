from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple

class WatermarkService:
    def __init__(self, font_path: Optional[str] = None):
        self.font_path = font_path or "arial.ttf"

    def apply_text_watermark(self, image_path: str, output_path: str, watermark_text: str,
                           opacity: float = 0.5, font_size: int = 36,
                           include_reference_code: Optional[str] = None) -> None:
        """
        Apply text watermark to an image.
        
        Args:
            image_path: Path to the source image
            output_path: Path where the watermarked image will be saved
            watermark_text: Text to use as watermark
            opacity: Opacity of the watermark (0-1)
            font_size: Size of the font
            include_reference_code: Optional reference code to append to watermark
        """
        try:
            base_image = Image.open(image_path).convert("RGBA")
            width, height = base_image.size

            # Create watermark image
            watermark = Image.new("RGBA", base_image.size, (0,0,0,0))
            draw = ImageDraw.Draw(watermark)

            try:
                font = ImageFont.truetype(self.font_path, font_size)
            except IOError:
                font = ImageFont.load_default()

            text = watermark_text
            if include_reference_code:
                text += f" | {include_reference_code}"

            # Use getbbox instead of deprecated textsize
            bbox = draw.textbbox((0, 0), text, font=font)
            textwidth = bbox[2] - bbox[0]
            textheight = bbox[3] - bbox[1]

            # Position watermark at bottom right with some padding
            x = width - textwidth - 10
            y = height - textheight - 10

            # Draw text on watermark image
            draw.text((x, y), text, font=font, fill=(255, 255, 255, int(255 * opacity)))

            # Composite watermark with base image
            watermarked = Image.alpha_composite(base_image, watermark)
            watermarked = watermarked.convert("RGB")  # Remove alpha for saving in jpg format

            watermarked.save(output_path, quality=95, optimize=True)
        except Exception as e:
            raise RuntimeError(f"Failed to apply text watermark: {str(e)}")

    def apply_image_watermark(self, image_path: str, output_path: str, watermark_image_path: str,
                            position: Tuple[float, float] = (0.9, 0.9),  # relative position (x,y)
                            scale: float = 0.1,  # relative scale to base image width
                            opacity: float = 0.5) -> None:
        """
        Apply image watermark to an image.
        
        Args:
            image_path: Path to the source image
            output_path: Path where the watermarked image will be saved
            watermark_image_path: Path to the watermark image
            position: Tuple of relative x,y position (0-1)
            scale: Scale of watermark relative to base image width
            opacity: Opacity of the watermark (0-1)
        """
        try:
            base_image = Image.open(image_path).convert("RGBA")
            watermark_image = Image.open(watermark_image_path).convert("RGBA")

            base_width, base_height = base_image.size

            # Resize watermark image based on scale relative to base image width
            new_width = int(base_width * scale)
            aspect_ratio = watermark_image.height / watermark_image.width
            new_height = int(new_width * aspect_ratio)
            
            # Use Resampling.LANCZOS instead of deprecated ANTIALIAS
            watermark_resized = watermark_image.resize(
                (new_width, new_height), 
                Image.Resampling.LANCZOS
            )

            # Adjust watermark opacity
            if opacity < 1:
                alpha = watermark_resized.split()[3]
                alpha = alpha.point(lambda p: int(p * opacity))
                watermark_resized.putalpha(alpha)

            # Calculate position in pixels
            x = int(base_width * position[0]) - new_width
            y = int(base_height * position[1]) - new_height

            # Create a transparent layer the size of the base image
            layer = Image.new("RGBA", base_image.size, (0,0,0,0))
            layer.paste(watermark_resized, (x, y))

            # Composite the watermark with the base image
            watermarked = Image.alpha_composite(base_image, layer)
            watermarked = watermarked.convert("RGB")  # Remove alpha for saving in jpg format

            watermarked.save(output_path, quality=95, optimize=True)
        except Exception as e:
            raise RuntimeError(f"Failed to apply image watermark: {str(e)}")
