# Cinema 4D Scripts

A collection of Python scripts for Cinema 4D, run from the **Script Manager**. They cover rig cleanup, hierarchy inspection, batch geometry conversion, and generating OpenPose skeleton sequences from 3D character rigs.

## Contents

| Script | What it does |
|---|---|
| [OpenPose Sequence Generator](#-advanced-openpose-sequence-generator-ui) | Renders OpenPose-style skeleton sequences from a rig, with a full dialog UI |
| [Mixamo Joint Name Cleaner](#-mixamo-joint-name-cleaner-for-cinema-4d) | Strips numeric suffixes from `mixamorig` joint names |
| [Batch Current State to Object](#-batch-current-state-to-object) | Converts selected generators to editable geometry and connects the result |
| [Object Hierarchy Printer](#-cinema-4d-object-hierarchy-printer) | Prints the scene hierarchy to the console |

**Requirements:** Cinema 4D with Python support. Scripts are written against the Python 3.11 API used by 2023 and later releases.

**Installing:** copy a `.py` file into your user scripts folder, then run it from *Extensions > Script Manager*. On Windows that folder is under
`%APPDATA%\Maxon\<installation>\library\scripts` — the installation folder name carries a hash, so find it via *Script Manager > User Scripts Folder* rather than typing the path.

---

# 🎥 Advanced OpenPose Sequence Generator UI

> **Note:** the script file is currently at **v4.5**; the notes below were written for v4.1. The v4.5 header documents the newer changes — added `RShoulder→REar` and `LShoulder→LEar` limb pairs, and a correction so that the rig's `Head` joint anchors the virtual face generator rather than being plotted as COCO keypoint 0 (Nose).

This Cinema 4D Python script provides a user-friendly interface for generating **OpenPose-style skeleton sequences** directly from 3D rigs. It is designed to normalize bone names across different rigging conventions (Mixamo, AccuRig, iClone, Character Creator, etc.) and output clean pose data for AI training, motion analysis, or visualization.

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

## 🖥️ User Interface
The script opens a **Cinema 4D dialog window** with the following sections:

- **Render Settings**: Choose output folder, format, resolution, and drawing options.
- **Features**: Enable bones, joints, and virtual face generation.
- **Joint Mapping**: Auto-detect rig joints or manually drag-and-drop into link boxes.
- **Action Panel**: Start rendering sequences with progress feedback.

## 🚀 Usage
1. Open **Cinema 4D** and load your rig.
2. Select the **root joint or null** in the Object Manager.
3. Launch the script from the **Script Manager**.
4. Use **Auto-Detect** to map joints automatically, or manually assign them.
5. Configure output settings (folder, format, resolution).
6. Click **Generate OpenPose Sequence** to render frames or video.

## 🛠 Example Outputs
- **PNG/JPG Sequences**: Frame-by-frame skeleton overlays for AI datasets.
- **MP4 Video**: Continuous skeleton animation preview.
- **Virtual Face Landmarks**: Nose, eyes, and ears generated from anatomical vectors to fix backward-walking artifacts.

## ⚠️ Notes
- Ensure the rig's root joint is selected before running Auto-Detect.
- If joints are not mapped, drag them manually into the link boxes.
- MP4 output may suffer from color compression; use PNG for training data.
- Works best with rigs that follow standard humanoid conventions.

---

# 🦴 Mixamo Joint Name Cleaner for Cinema 4D

This Cinema 4D Python script cleans up Mixamo joint names by removing unwanted numeric suffixes (e.g., `mixamorig1`, `mixamorig2`) and standardizing them back to `mixamorig`. This makes rigs cleaner, easier to read, and more consistent for animation workflows.

## ✨ Features
- Recursively traverses the hierarchy starting from a selected root joint (e.g., `Hips`).
- Detects all **Joint objects** in the hierarchy.
- Cleans Mixamo-style names by removing numeric suffixes:
  - `mixamorig1` → `mixamorig`
  - `mixamorig23` → `mixamorig`
- Adds undo support so changes can be reverted.
- Provides console feedback for renamed joints.
- Displays a dialog if no root joint is selected.

## 🚀 Usage
1. Select the root joint of the rig (typically `Hips`) in the Object Manager.
2. Run the script from the **Script Manager**.
3. Renamed joints are listed in the Console (`Shift + F10`).

---

# 🧩 Batch Current State to Object

Converts every **selected** object to editable geometry in one pass, then collapses each result into a single mesh.

## ✨ Features
- Runs *Current State to Object* on each selected object in turn.
- Follows each conversion with *Select Children* and *Connect Objects + Delete*, so a generator that produced a hierarchy comes back as one clean mesh.
- Wraps the whole batch in a single undo step.
- Calls `StopAllThreads()` first, so it is safe to run on a scene that is still evaluating.

## 🚀 Usage
1. Select one or more generators, cloners, or parametric objects.
2. Run the script from the **Script Manager**.
3. Each selection is replaced by a single editable mesh.

## ⚠️ Notes
- This **modifies the scene**. The whole batch undoes as one step.
- Nothing happens if no objects are selected.

---

# 🗂 Cinema 4D Object Hierarchy Printer

This Cinema 4D Python script prints the **entire object hierarchy** of your scene to the console. It recursively traverses all objects starting from the first object in the document and displays their names with indentation to reflect parent-child relationships.

## ✨ Features
- Recursively traverses the **Object Manager hierarchy**.
- Prints object names with indentation to show structure.
- Provides clear feedback if the scene is empty.
- Simple and lightweight utility for debugging or documentation.

## 🚀 Usage
1. Open **Cinema 4D**.
2. Load a scene with objects.
3. Run the script from the **Script Manager**.
4. Check the **Console** (`Shift + F10`) to view the hierarchy output.

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

## ⚠️ Notes
- If no objects exist in the scene, the script will print:
  `No objects in scene.`
- This script is read-only and does not modify the scene.
- Useful for quickly inspecting complex hierarchies or debugging rig setups.

---

## Related

- [Cinema-4D-Python-Effectors](https://github.com/grasycho/Cinema-4D-Python-Effectors) — MoGraph Python Effector scripts
- [Cinema-4D-Projects](https://github.com/grasycho/Cinema-4D-Projects) — project files and scene setups
- [c4dpl-container-object](https://github.com/grasycho/c4dpl-container-object) — Container Object plugin (C++)

## 📄 License

Released under the MIT License. You are free to use, modify, and distribute these scripts in your projects.
