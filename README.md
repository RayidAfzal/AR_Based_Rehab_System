# AR Neuro-Motor Rehabilitation System

A real-time gesture-based rehabilitation platform designed to improve neuro-motor coordination using interactive therapy games powered by computer vision.

The system uses hand tracking and motion analysis to create engaging rehabilitation exercises through multiple interactive modules.

---

## Features

- Real-time hand tracking using MediaPipe
- Multiple rehabilitation game modules
- Gesture-controlled interaction
- Motor performance analytics
- Patient session tracking
- Graphical progress reports
- Kiosk-mode deployment support
- Automatic application startup support

---

## Therapy Modules

- ### Fruit Ninja 🍉 
Gesture-controlled slicing game for improving hand movement precision and reaction time.

- ### Finger Tap 👌🏻
Finger tapping coordination and response training module.

- ### Balloon Rehab 🎈


- ### Laser Slice 🪚


---

## 📂 Project Structure

```text
AR-NeuroRehab-System/
│
├── Images/
├── sounds/
│
├── game_balloon_rehab.py
├── game_finger_tap.py
├── game_fruit_ninja.py
├── game_laser_slice.py
├── Rehab.py
├── utils.py
│
├── patient_data.csv
├── patients.json
├── rehab_progress.csv
│
├── requirements.txt
├── README.md
```

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/RayidAfzal/AR_Based_Rehab_System.git
```

Move into the project directory:

```bash
cd AR_Based_Rehab_System
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Project

Run the main application:

```bash
python Rehab.py
```

---

## 🖥 Creating the Executable

Use the following command to generate the standalone executable:

```bash
pyinstaller --onefile --windowed --version-file file_version_info.txt --add-data "PATH_TO_MEDIAPIPE_FOLDER;mediapipe" --add-data "Images;Images" --add-data "sounds;sounds" --add-data "utils.py;." Rehab.py

Replace `PATH_TO_MEDIAPIPE_FOLDER` with your local MediaPipe installation path.

Example (Windows):

C:\Users\YourName\AppData\Local\Programs\Python\Python310\Lib\site-packages\mediapipe
```

The executable will be generated inside the `dist/` folder.

---

## 📊 Analytics Features

The system tracks:
- Score
- Accuracy
- Response Time
- Motor Index
- Session Progress

Reports can also be exported as PNG graphs.

---

## 👨‍💻 Team

- Rayid — Fruit Ninja module + System Integration
- Karthik — Finger Tap module
- Abhishek — Balloon Interaction module
- Elias — Laser Slice module

Guide:
Dr. Pradeep C

---

## 📌 Notes

- Ensure webcam permissions are enabled.
- Best experienced in fullscreen mode.
- Designed for rehabilitation demo and research purposes.

---

## 📜 License

MIT License
