from pathlib import Path
from PIL import Image
import numpy as np

INPUT_DIR = Path("input_webp")
OUTPUT_DIR = Path("output_png")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALPHA_THRESHOLD = 10
WHITE_THRESHOLD = 190

PADDING_PX = 0

def convert_image(webp_path: Path, output_path: Path):
    img = Image.open(webp_path).convert("RGBA")
    arr = np.array(img)

    r,g,b,a = arr.T

    # foreground mask
    not_transparent = a > ALPHA_THRESHOLD
    not_white = ~((r > WHITE_THRESHOLD) &
                  (g > WHITE_THRESHOLD) &
                  (b > WHITE_THRESHOLD))

    mask = not_transparent & not_white

    binary = np.zeros(arr.shape, dtype=np.uint8)
    # full transparent
    binary[..., 3] = 0
    # white foreground
    binary[mask] = [255,255,255,255]

    # crop to content
    ys, xs = np.where(mask)
    min_x, max_x = xs.min(), xs.max()
    min_y, max_y = ys.min(), ys.max()

    binary = binary[min_y:max_y+1,min_x:max_x+1]
    
    if PADDING_PX > 0:
        # add padding
        h,w,_ = binary.shape
        padded = np.zeros(
            (h+2 * PADDING_PX, w+2 * PADDING_PX, 4),
            dtype=np.uint8
        )
        padded[PADDING_PX:PADDING_PX+h, PADDING_PX:PADDING_PX+w] = binary
    else:
        padded = binary

    # make square
    h,w,_ = padded.shape
    size = max(h,w)

    square = np.zeros((size, size, 4), dtype=np.uint8)
    y_off = (size -h) //2
    x_off = (size -w) //2
    square[y_off:y_off+h, x_off:x_off+w] = padded

    Image.fromarray(square, mode="RGBA").save(output_path)


def process_folder(input_dir: Path, output_dir: Path):
    for webp_file in input_dir.rglob("*.webp"):
        relative = webp_file.relative_to(input_dir)
        out_path = (output_dir / relative).with_suffix(".png")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        convert_image(webp_file, out_path)
        print(f"Converted: {webp_file} -> {out_path}")


if __name__ == "__main__":
    process_folder(INPUT_DIR, OUTPUT_DIR)
