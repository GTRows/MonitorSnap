from PIL import Image

# Create .ico file from PNG images
sizes = [16, 32, 48, 64, 128, 256]
images = []

for size in sizes:
    try:
        img = Image.open(f"icon_{size}.png")
        images.append(img)
    except:
        print(f"Could not load icon_{size}.png")

if images:
    images[0].save("app.ico", format="ICO", sizes=[(img.width, img.height) for img in images], append_images=images[1:])
    print("Created app.ico successfully!")
else:
    print("No images found!")
