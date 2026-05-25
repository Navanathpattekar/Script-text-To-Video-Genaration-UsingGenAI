import os
import time
import subprocess
import requests
from django.shortcuts import render
import pytz
from datetime import datetime
from myproject.settings import MEDIA_ROOT, MEDIA_URL, BASE_DIR
from dotenv import load_dotenv
load_dotenv()

# --------------------------
# 🔑 HUGGING FACE TOKEN HERE
# --------------------------

HF_API_TOKEN  = os.getenv("MY_API_KEY") # <--- PUT YOUR NEW TOKEN HERE
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# NEW Endpoint (old one is deprecated)
# HF_API_URL = "https://router.huggingface.co/hf-inference/models"

HF_API_URL = os.getenv(
    "HF_API_URL",
    "https://api-inference.huggingface.co/models"
)

# context = {}
# now = ""
# save_dir_abs = os.path.join(MEDIA_ROOT, f"script-{now}", "images")
# save_dir = save_dir_abs

# --------------------------
# 1️⃣ Generate SCENES
# --------------------------
def generate_scenes(script):
    api_url = f"{HF_API_URL}/facebook/bart-large-cnn"

    data = {
        "inputs": script,
        "parameters": {
            "max_length": 400,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.95
        }
    }

    try:
        response = requests.post(api_url, headers=HEADERS, json=data)

        print("DEBUG SCENE RESPONSE:", response.text)

        response_data = response.json()

        # If API returns error
        if isinstance(response_data, dict) and response_data.get("error"):
            print("HF ERROR:", response_data["error"])
            return []

        # Extract scenes
        if not isinstance(response_data, list) or "summary_text" not in response_data[0]:
            print("HF RESPONSE INVALID:", response_data)
            return []

        scenes = [
            s.strip()
            for s in response_data[0]["summary_text"].split(".")
            if s.strip()
        ]

        return scenes

    except Exception as e:
        print("ERROR:", e)
        return []


# --------------------------
# 2️⃣ Generate KEY FRAMES
# --------------------------
def generate_images(scenes, template, save_dir_abs, now):
    api_url = f"{HF_API_URL}/black-forest-labs/FLUX.1-schnell"

    generated_images = []
    err_limit = 0
    total_frame_cnt = 0

    # ✅ ensure folder exists (safe on Render)
    os.makedirs(save_dir_abs, exist_ok=True)

    for i, description in enumerate(scenes):

        scene_frame_cnt = 0

        while True:

            # stop conditions
            if err_limit >= 5 or scene_frame_cnt >= len(template):
                err_limit = 0
                break

            prompt = f"{description} {template[scene_frame_cnt]}"

            data = {
                "inputs": prompt,
                "parameters": {
                    "width": 512,
                    "height": 512,
                    "seed": 42,
                    "num_inference_steps": 25,
                    "guidance_scale": 7.5,
                }
            }

            try:
                response = requests.post(
                    api_url,
                    headers=HEADERS,
                    json=data,
                    timeout=60
                )
            except Exception as e:
                print("REQUEST FAILED:", e)
                err_limit += 1
                time.sleep(4)
                continue

            # ❌ API error
            if response.status_code != 200:
                print("IMAGE GEN ERROR:", response.text)
                err_limit += 1
                time.sleep(4)
                continue

            # ❌ ensure image response
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                print("NOT IMAGE RESPONSE:", response.text)
                err_limit += 1
                time.sleep(4)
                continue

            # ✅ save image
            filepath = f"{total_frame_cnt + 1:04d}.jpeg"
            full_path = os.path.join(save_dir_abs, filepath)

            with open(full_path, "wb") as file:
                file.write(response.content)

            filename = f"{total_frame_cnt + 1:04d}.jpeg"
            image_url = os.path.join(
                MEDIA_URL,
                f"script-{now}",
                "images",
                filename
            ).replace("\\", "/")

            generated_images.append(image_url)
            scene_frame_cnt += 1
            total_frame_cnt += 1

            time.sleep(4)

    return generated_images

# --------------------------
# 3️⃣ Interpolate Frames
# --------------------------
def interpolated_images(save_dir):
    os.chdir(os.path.dirname(save_dir))

    cmd = [
        "python",
        os.path.join(BASE_DIR, "ECCV2022-RIFE", "inference_video.py").replace("\\", "/"),
        "--exp=4",
        f"--img={save_dir}",
        "--model",
        os.path.join(BASE_DIR, "ECCV2022-RIFE", "train_log").replace("\\", "/")
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return False

    return True


# --------------------------
# 4️⃣ Create Final Video using FFmpeg (NO OpenCV)
# --------------------------
def create_video(image_folder):
    try:
        if not os.path.isdir(image_folder):
            print("Invalid folder:", image_folder)
            return False

        # FFmpeg command expects numbers like 0001.jpeg, 0002.jpeg, etc.
        output_video_path = os.path.join(
            os.path.dirname(image_folder),
            f"{now}.mp4"
        ).replace("\\", "/")

        # IMPORTANT: Run inside the folder containing images
        cmd = [
            "ffmpeg",
            "-framerate", "3",
            "-i", "%04d.jpeg",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_video_path,
            "-y"
        ]

        print("Running FFmpeg:", cmd)

        subprocess.run(cmd, cwd=image_folder, check=True)

        print("Video created:", output_video_path)
        return True

    except Exception as e:
        print("FFMPEG ERROR:", e)
        return False


# --------------------------
# HOME PAGE — Enter Script
# --------------------------
def home(request):
    global context
    context = {}

    if request.method == "POST":
        script = request.POST.get("script", "").strip()

        if not script:
            context["error"] = "Script is required."
            return render(request, "home.html", context)

        elif len(script) < 30:
            context["error"] = "Script is too short."
            return render(request, "home.html", context)

        scenes = generate_scenes(script)

        if not scenes:
            context["error"] = "Error in generating scenes"
            return render(request, "home.html", context)

        request.session["scenes"] = scenes
        return render(request, "scenes.html", context)

    return render(request, "home.html", context)


# --------------------------
# KEY FRAME GENERATION PAGE
# --------------------------
def key_frames(request):
    if request.method == "POST":

        global context, save_dir, save_dir_abs, now

        from pytz import timezone as pytz_timezone

        ist = pytz_timezone("Asia/Kolkata")
        now = datetime.now(ist).strftime("%d-%m--%H-%M")

        save_dir_abs = os.path.join(
            MEDIA_ROOT,
            f"script-{now}",
            "images"
        ).replace("\\", "/")

        os.makedirs(save_dir_abs, exist_ok=True)

        angles = [
            "front view realistic",
            "45 degree left front view realistic",
            "90 degree left side view realistic",
            ""
        ]

        scenes = request.session.get("scenes")

        if not scenes:
            return render(request, "home.html", {"error": "Scenes not found"})

        images = generate_images(scenes, angles, save_dir_abs, now)

        if not images:
            return render(request, "home.html", {"error": "Key frames not generated"})

        request.session["save_dir_abs"] = save_dir_abs
        request.session["now"] = now

        return render(request, "keyframes.html", {"keyframes": images})

    return render(request, "home.html")

# --------------------------
# INTERPOLATED FRAMES PAGE
# --------------------------
def interpolated_frames(request):
    if request.method == "POST":
        global context, save_dir_abs

        if not interpolated_images(save_dir_abs):
            context["error"] = "Error in interpolated frames"
            return render(request, "home.html", context)

        context["interpolated"] = True
        return render(request, "interpolated.html", context)

    return render(request, "home.html", context)


# --------------------------
# FINAL VIDEO PAGE
# --------------------------
def video(request):
    if request.method == "POST":

        save_dir_abs = request.session.get("save_dir_abs")
        now = request.session.get("now")

        if not save_dir_abs or not now:
            return render(request, "home.html", {"error": "Session expired"})

        if not create_video(save_dir_abs):
            return render(request, "home.html", {"error": "Video generation error"})

        video_url = os.path.join(
            MEDIA_URL,
            f"script-{now}",
            f"{now}.mp4"
        ).replace("\\", "/")

        return render(request, "video.html", {"video_url": video_url})

    return render(request, "home.html")



