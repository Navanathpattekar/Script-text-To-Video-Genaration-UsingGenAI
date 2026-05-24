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

HF_API_URL = os.getenv("HF_API_URL")

context = {}
now = ""
save_dir = ""
save_dir_abs = ""


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
        scenes = [
            scene.strip()
            for scene in response_data[0]["summary_text"].split(".")
            if scene.strip()
        ]

        return scenes

    except Exception as e:
        print("ERROR:", e)
        return []


# --------------------------
# 2️⃣ Generate KEY FRAMES
# --------------------------
def generate_images(scenes, template, save_dir):
    api_url = f"{HF_API_URL}/black-forest-labs/FLUX.1-schnell"

    generated_images = []
    err_limit = 0
    total_frame_cnt = 0
    scene_frame_cnt = 0

    for i, description in enumerate(scenes):

        while True:
            if err_limit == 5 or scene_frame_cnt == 3:
                err_limit = 0
                scene_frame_cnt = 0
                break

            data = {
                "inputs": description + " " + template[scene_frame_cnt],
                "parameters": {
                    "width": 512,
                    "height": 512,
                    "seed": 42,
                    "num_inference_steps": 25,
                    "guidance_scale": 7.5,
                }
            }

            response = requests.post(api_url, headers=HEADERS, json=data)

            if response.status_code == 200:
                filepath = f"{total_frame_cnt + 1:04d}.jpeg"

                with open(filepath, "wb") as file:
                    file.write(response.content)

                img = os.path.join(save_dir, filepath).replace("\\", "/")
                generated_images.append(img)

                scene_frame_cnt += 1
                total_frame_cnt += 1
                time.sleep(4)

            else:
                print("IMAGE GEN ERROR:", response.text)
                time.sleep(4)
                err_limit += 1

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

        context["scenes"] = scenes
        return render(request, "scenes.html", context)

    return render(request, "home.html", context)


# --------------------------
# KEY FRAME GENERATION PAGE
# --------------------------
def key_frames(request):
    if request.method == "POST":
        global context, save_dir, save_dir_abs, now

        timezone = pytz.timezone("Asia/Kolkata")
        now = datetime.now(timezone).strftime("%d-%m--%H-%M")

        save_dir = os.path.join(MEDIA_URL, f"script-{now}", "images").replace("\\", "/")
        save_dir_abs = os.path.join(MEDIA_ROOT, f"script-{now}", "images").replace("\\", "/")

        os.makedirs(save_dir_abs, exist_ok=True)
        os.chdir(save_dir_abs)

        angles = [
            "front view realistic",
            "45 degree left front view realistic",
            "90 degree left side view realistic",
            ""
        ]

        scenes = context.get("scenes")

        if not scenes:
            context["error"] = "Scenes not found. Please generate script again."
            return render(request, "home.html", context)

        images = generate_images(scenes, angles, save_dir)

        if not images:
            context["error"] = "Key frames not generated"
            return render(request, "home.html", context)

        context["keyframes"] = images
        return render(request, "keyframes.html", context)

    return render(request, "home.html", context)


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
        global context, save_dir, save_dir_abs, now

        if not create_video(save_dir_abs):
            context["error"] = "Video generation error"
            return render(request, "home.html", context)

        video_path = os.path.join(os.path.dirname(save_dir), f"{now}.mp4").replace("\\", "/")
        context["video_url"] = video_path

        return render(request, "video.html", context)

    return render(request, "home.html", context)






