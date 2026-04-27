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

## 📜 Script Overview

```python
import c4d
import re

def clean_joint_names(op, doc):
    """
    Recursively iterates through the hierarchy, finds Joint objects, 
    and removes numeric suffixes from Mixamo naming conventions.
    """
    while op:
        if op.GetType() == c4d.Ojoint:
            old_name = op.GetName()
            new_name = re.sub(r'mixamorig\d+', 'mixamorig', old_name)

            if new_name != old_name:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, op)
                op.SetName(new_name)
                print(f"Renamed: {old_name} -> {new_name}")

        clean_joint_names(op.GetDown(), doc)
        op = op.GetNext()

def main():
    doc = c4d.documents.GetActiveDocument()
    selected = doc.GetActiveObject()

    if not selected:
        c4d.gui.MessageDialog("Please select the root joint (e.g., Hips) before running the script.")
        return

    doc.StartUndo()
    clean_joint_names(selected, doc)
    doc.EndUndo()
    c4d.EventAdd()

    print("Mixamo joint name cleaning complete.")

if __name__ == '__main__':
    main()
