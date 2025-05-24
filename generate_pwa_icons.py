import os

from PIL import Image


def create_pwa_icons():
    # Create icons directory if it doesn't exist
    os.makedirs("static/icons", exist_ok=True)

    # Open the base image
    with Image.open("generated-icon.png") as img:
        # Generate 192x192 icon
        icon_192 = img.resize((192, 192), Image.Resampling.LANCZOS)
        icon_192.save("static/icons/icon-192x192.png", "PNG")

        # Generate 512x512 icon
        icon_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
        icon_512.save("static/icons/icon-512x512.png", "PNG")

        print("PWA icons generated successfully!")


if __name__ == "__main__":
    create_pwa_icons()
