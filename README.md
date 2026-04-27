# 🗂 Cinema 4D Object Hierarchy Printer

This Cinema 4D Python script prints the **entire object hierarchy** of your scene to the console. It recursively traverses all objects starting from the first object in the document and displays their names with indentation to reflect parent-child relationships.

---

## ✨ Features
- Recursively traverses the **Object Manager hierarchy**.
- Prints object names with indentation to show structure.
- Provides clear feedback if the scene is empty.
- Simple and lightweight utility for debugging or documentation.

---

## 🚀 Usage
1. Open **Cinema 4D**.
2. Load a scene with objects.
3. Run the script from the **Script Manager**.
4. Check the **Console** (`Shift + F10`) to view the hierarchy output.

---

## 🛠 Example Output
For a scene with a hierarchy like:

```
Null
  Cube
  Sphere
    Cone
```

The console will display:

```
Null
  Cube
  Sphere
    Cone
```

---

## ⚠️ Notes
- If no objects exist in the scene, the script will print:  
  `No objects in scene.`
- This script is read-only and does not modify the scene.
- Useful for quickly inspecting complex hierarchies or debugging rig setups.

---

## 📄 License
Released under the MIT License.  
You are free to use, modify, and distribute this script in your projects.



# 🎥 Advanced OpenPose Sequence Generator UI v4.1

This Cinema 4D Python script provides a user-friendly interface for generating **OpenPose-style skeleton sequences** directly from 3D rigs. It is designed to normalize bone names across different rigging conventions (Mixamo, AccuRig, iClone, Character Creator, etc.) and output clean pose data for AI training, motion analysis, or visualization.

---

## ✨ Key Features
- **Rig Compatibility**: Supports Mixamo, AccuRig, iClone, CC3/CC4, Genesis, and other mocap rigs.
- **Bone Name Normalization**: Automatically cleans prefixes, suffixes, and naming inconsistencies.
- **Auto-Detection**: Maps joints to OpenPose labels with one click.
- **Virtual Face Generator**: Anatomical vector math creates facial landmarks (nose, eyes, ears) even if missing from the rig.
- **Flexible Output**:
  - PNG sequence (lossless, best for AI training)
  - JPG sequence (high quality, smaller size)
  - MP4 video (compressed, quick preview)
- **Customizable Rendering**:
  - Resolution, line thickness, and joint radius
  - Toggle bones and joint markers
- **Undo & Status Feedback**: Safe operations with real-time progress updates.

---

## 🖥️ User Interface
The script opens a **Cinema 4D dialog window** with the following sections:

- **Render Settings**: Choose output folder, format, resolution, and drawing options.
- **Features**: Enable bones, joints, and virtual face generation.
- **Joint Mapping**: Auto-detect rig joints or manually drag-and-drop into link boxes.
- **Action Panel**: Start rendering sequences with progress feedback.

---

## 🚀 Usage
1. Open **Cinema 4D** and load your rig.
2. Select the **root joint or null** in the Object Manager.
3. Launch the script from the **Script Manager**.
4. Use **Auto-Detect** to map joints automatically, or manually assign them.
5. Configure output settings (folder, format, resolution).
6. Click **Generate OpenPose Sequence** to render frames or video.

---

## 🛠 Example Outputs
- **PNG/JPG Sequences**: Frame-by-frame skeleton overlays for AI datasets.
- **MP4 Video**: Continuous skeleton animation preview.
- **Virtual Face Landmarks**: Nose, eyes, and ears generated from anatomical vectors to fix backward-walking artifacts.

---

## ⚠️ Notes
- Ensure the rig’s root joint is selected before running Auto-Detect.
- If joints are not mapped, drag them manually into the link boxes.
- MP4 output may suffer from color compression; use PNG for training data.
- Works best with rigs that follow standard humanoid conventions.

---

# 🦴 Mixamo Joint Name Cleaner for Cinema 4D

This Cinema 4D Python script cleans up Mixamo joint names by removing unwanted numeric suffixes (e.g., `mixamorig1`, `mixamorig2`) and standardizing them back to `mixamorig`. This makes rigs cleaner, easier to read, and more consistent for animation workflows.

---

## ✨ Features
- Recursively traverses the hierarchy starting from a selected root joint (e.g., `Hips`).
- Detects all **Joint objects** in the hierarchy.
- Cleans Mixamo-style names by removing numeric suffixes:
  - `mixamorig1` → `mixamorig`
  - `mixamorig23` → `mixamorig`
- Adds undo support so changes can be reverted.
- Provides console feedback for renamed joints.
- Displays a dialog if no root joint is selected.

---

