import cadquery as cq
import numpy as np
from PIL import Image
from pathlib import Path
import math
import cv2

# =====================
# PARAMETERS (mm)
# =====================
Z_EPS = 0.01

BASE_DIAMETER = 40
BASE_HEIGHT = 4

DONUT_OUTER_DIAMETER = 40
DONUT_INNER_DIAMETER = 30
DONUT_HEIGHT = 2

TEXT_HEIGHT = 3
IMAGE_HEIGHT = 2
IMAGE_PADDING = 2

FONT_NAME = "Helvetica"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# =====================
# UTILITIES
# =====================

def validate_name(name: str):
    parts = name.split(" ")
    if len(parts) > 2:
        raise ValueError(f"Name '{name}' has more than two words!")
    return parts

def load_binary_image(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGBA")
    alpha = np.array(img.split()[-1])
    binary = alpha > 0
    if not binary.any():
        raise ValueError(f"Image {path} contains no opaque pixels.")
    return binary.astype(np.uint8)

def image_to_solid(binary_img_path, max_size, z_offset, height):
    print("Processing image")

    img = Image.open(binary_img_path).convert("L")
    img_np = np.array(img)

    _, thresh = cv2.threshold(img_np, 1, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        # thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        raise ValueError(f"No contours found in image '{binary_img_path}'")
    

    h,w = img_np.shape
    cx = w / 2
    cy = h / 2
    scale = max_size / max(h,w)

    wp = cq.Workplane("XY").workplane(offset=z_offset+Z_EPS)

    for cnt in contours:

        cnt = cnt.squeeze()
        if len(cnt) < 3:
            continue

        points = [((x-cx)*scale, (cy-y) * scale) for x,y in cnt]

        wp = (
            wp
            .polyline(points)
            .close()
            .extrude(height)
        )

    return wp.rotate((0,0,0),(0,0,1), -90)
    

def curved_text(word, radius, z_offset, angle_center):
    letters = list(word)
    num_letters = len(letters)

    arc_per_letter = 18 #mm
    total_arc = num_letters * arc_per_letter
    if total_arc > 180:
        raise ValueError(f"Word '{word}' too long for rim")
    
    start_angle = angle_center-total_arc/4
    text_objs = []

    for i, letter in enumerate(letters):
        angle =start_angle+ i*arc_per_letter/2 + 2.5
        angle_rad = angle * math.pi / 180
        out_vec = (radius * math.cos(angle_rad),radius * math.sin(angle_rad),0)
        text_w = cq.Workplane("XY").workplane(offset=z_offset).text(letter, fontsize=4,distance=TEXT_HEIGHT, font=FONT_NAME).rotate((0,0,0), (0,0,1), angle-angle_center).translate(out_vec)
        text_objs.append(text_w)

    model = text_objs[0]
    for t in text_objs[1:]:
        model = model.union(t)


    return model 


def arc_length_for_text(word, font_size=4):
    return len(word) * font_size * 0.6

def max_arc_length(radius):
    return math.pi * radius


# =====================
# TOKEN GENERATOR
# =====================

def generate_token(name, image_path):
    print(f"Working on {name}")
    parts = validate_name(name)

    # Base
    model = (
        cq.Workplane("XY")
        .circle(BASE_DIAMETER / 2)
        .extrude(BASE_HEIGHT)
    )
    donut = (
        cq.Workplane("XY")
        .workplane(offset=BASE_HEIGHT)
        .circle(DONUT_OUTER_DIAMETER / 2)
        .circle(DONUT_INNER_DIAMETER / 2)
        .extrude(DONUT_HEIGHT)
    )

    model = model.union(donut)


    # Text
    radius = (DONUT_OUTER_DIAMETER + DONUT_INNER_DIAMETER) / 4
    z_text = BASE_HEIGHT + DONUT_HEIGHT

    model = model.union(curved_text(parts[0][::-1], radius, z_text, 90))
    if len(parts) > 1:
        model = model.union(curved_text(parts[1], radius, z_text, -90))



    # Image
    max_image_size = DONUT_INNER_DIAMETER - 2 * IMAGE_PADDING
    img_solid = image_to_solid(
       binary_img_path=image_path,
       max_size=max_image_size, 
       z_offset=BASE_HEIGHT, 
       height=IMAGE_HEIGHT)

    model = model.union(img_solid)


    # Export
    safe_name = name.replace(" " , "_")
    output_path = OUTPUT_DIR / f"{safe_name}.stl"
    cq.exporters.export(model, str(output_path))

    print(f"Generated: {output_path}")


# =====================
# BATCH ENTRY POINT
# =====================

def generate_all(names, image_paths):
    if len(names) != len(image_paths):
        raise ValueError("Names and images list must be same length.")

    for name, img in zip(names, image_paths):
        generate_token(name, Path(img))


# =====================
# EXAMPLE USAGE
# =====================

if __name__ == "__main__":
    characters = [
        {"name": "Baron", "good": False},
        {"name": "Butler", "good": True},
        {"name": "Chef", "good": True},
        {"name": "Drunk", "good": True},
        {"name": "Empath", "good": True},
        {"name": "Fortune Teller", "good": True},
        {"name": "Imp", "good": False},
        {"name": "Investi gator", "good": True},
        {"name": "Librarian", "good": True},
        {"name": "Mayor", "good": True},
        {"name": "Monk", "good": True},
        {"name": "Poisoner", "good": False},
        {"name": "Raven keeper", "good": True},
        {"name": "Recluse", "good": True},
        {"name": "Saint", "good": True},
        {"name": "Scarlet Woman", "good": False},
        {"name": "Slayer", "good": True},
        {"name": "Spy", "good": False},
        {"name": "Undertaker", "good": True},
        {"name": "Virgin", "good": True},
        {"name": "Washer Woman", "good": True},
    ]

    names = [e.get("name") for e in characters]
    images = [f"./output_png/{e.get("name").lower().replace(" ", "")}_{"g" if e.get("good") else "e"}.png" for e in characters]

    generate_all(names, images)