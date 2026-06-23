# Script-to-Video Generation Using GenAI

A Django-based AI-powered application that converts a text script into a video automatically using Generative AI. The application generates scenes from a script, creates AI-generated images for each scene, interpolates intermediate frames, and combines them into a final video using FFmpeg.

## Features

* Convert text scripts into visual scenes
* Generate scene descriptions using AI
* Create AI-generated images from scene prompts
* Generate intermediate frames using RIFE Frame Interpolation
* Create smooth videos using FFmpeg
* Simple web-based interface built with Django
* Automated end-to-end text-to-video workflow

## Tech Stack

### Backend

* Python
* Django

### AI & ML

* Hugging Face Inference API
* Pollinations AI Image Generation
* RIFE (Real-Time Intermediate Flow Estimation)

### Video Processing

* FFmpeg
* OpenCV

### Frontend

* HTML
* CSS
* JavaScript

## Project Workflow

1. User enters a script.
2. AI generates scene descriptions.
3. Images are generated for each scene.
4. RIFE generates intermediate frames.
5. FFmpeg combines frames into a video.
6. Final video is displayed to the user.

## Installation

### Clone Repository

```bash
git clone https://github.com/Navanathpattekar/Script-text-To-Video-Genaration-UsingGenAI.git
cd Script-text-To-Video-Genaration-UsingGenAI
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Apply Migrations

```bash
python manage.py migrate
```

### Run Server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Project Structure

```text
myproject/
│
├── myapp/
│   ├── views.py
│   ├── urls.py
│   └── templates/
│
├── media/
├── static/
├── staticfiles/
├── manage.py
└── requirements.txt
```

## Future Enhancements

* Voice-over generation
* Background music integration
* Multiple video styles
* Custom image generation models
* Cloud deployment support
* User authentication and project history

## Author

Navanath Pattekar

GitHub:
https://github.com/Navanathpattekar

## License

This project is developed for educational and learning purposes.
