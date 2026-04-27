import c4d

def print_hierarchy(op, indent=0):
    while op:
        print("  " * indent + op.GetName())
        
        # Recurse into children
        if op.GetDown():
            print_hierarchy(op.GetDown(), indent + 1)
        
        op = op.GetNext()

def main():
    doc = c4d.documents.GetActiveDocument()
    first_obj = doc.GetFirstObject()
    
    if not first_obj:
        print("No objects in scene.")
        return
    
    print_hierarchy(first_obj)

if __name__ == '__main__':
    main()