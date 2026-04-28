#!/usr/bin/env python3
"""
Convert a PNG image to favicon formats
Usage: python create_favicon.py <input_image.png>
"""

import sys
from pathlib import Path

def create_favicon(image_path):
    """Convert image to favicon formats"""
    try:
        from PIL import Image
    except ImportError:
        print("Installing Pillow...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image
    
    input_file = Path(image_path)
    output_dir = Path(__file__).parent / "frontend" / "public"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Open the image
    img = Image.open(input_file)
    
    # Convert RGBA to RGB if needed (for favicon)
    if img.mode == 'RGBA':
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
        img = rgb_img
    
    # Create favicon sizes
    sizes = [
        (16, "favicon-16.png"),
        (32, "favicon-32.png"),
        (64, "favicon-64.png"),
        (128, "favicon-128.png"),
        (180, "favicon-180.png"),  # Apple touch icon
        (256, "favicon-256.png"),
    ]
    
    for size, filename in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        output_path = output_dir / filename
        resized.save(output_path)
        print(f"✓ Created {output_path}")
    
    # Also create ICO format
    img.save(output_dir / "favicon.ico")
    print(f"✓ Created {output_dir / 'favicon.ico'}")
    
    print("\n✅ Favicon files created successfully!")
    print(f"📁 Location: {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_favicon.py <input_image.png>")
        sys.exit(1)
    
    create_favicon(sys.argv[1])
