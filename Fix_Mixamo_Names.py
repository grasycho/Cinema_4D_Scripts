import c4d
import re

def clean_joint_names(op, doc):
    """
    Recursively iterates through the hierarchy, finds Joint objects, 
    and removes numeric suffixes from Mixamo naming conventions.
    """
    while op:
        # Check if the object is a joint
        if op.GetType() == c4d.Ojoint:
            old_name = op.GetName()
            
            # Replace 'mixamorig' followed by any numbers with just 'mixamorig'
            new_name = re.sub(r'mixamorig\d+', 'mixamorig', old_name)
            
            # If the name changed, update it and add an undo state
            if new_name != old_name:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, op)
                op.SetName(new_name)
                print(f"Renamed: {old_name} -> {new_name}")
        
        # Recursively process child objects
        clean_joint_names(op.GetDown(), doc)
        
        # Move to the next sibling
        op = op.GetNext()

def main():
    doc = c4d.documents.GetActiveDocument()
    
    # Get the currently selected object
    selected = doc.GetActiveObject()
    
    if not selected:
        c4d.gui.MessageDialog("Please select the root joint (e.g., Hips) before running the script.")
        return

    # Start the undo block
    doc.StartUndo()
    
    # Execute the cleaning function starting from the selected object
    clean_joint_names(selected, doc)
    
    # End the undo block and refresh the UI
    doc.EndUndo()
    c4d.EventAdd()
    
    print("Mixamo joint name cleaning complete.")

if __name__ == '__main__':
    main()