"""4x AI upscale (Real-ESRGAN x4plus-anime, bundled with realesrgan-ncnn-py, run on CPU).

    python3 tools/ep/upscale.py in.png out.png

Not needed to render: the upscaled images are kept in series/ep01/x4 and
characters_x16. To run it: pip install realesrgan-ncnn-py, and
apt-get install libomp5 libvulkan1 mesa-vulkan-drivers (its CPU path still loads Vulkan).
"""
import sys, cv2
from realesrgan_ncnn_py import Realesrgan

if __name__ == '__main__':
    r = Realesrgan(gpuid=-1, model=3, tilesize=256)
    img = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR)
    cv2.imwrite(sys.argv[2], r.process_cv2(img))
    print(sys.argv[2], flush=True)
