import c4d
from c4d import gui
from c4d import utils
from c4d import documents

def current(obj,doc,settings):
        utils.SendModelingCommand(command = c4d.MCOMMAND_CURRENTSTATETOOBJECT,
            list = [obj],
            mode=c4d.MODELINGCOMMANDMODE_ALL,
            bc=settings,
            doc = c4d.documents.GetActiveDocument())
        doc.SetActiveObject(obj)
        c4d.CallCommand(100004768, 100004768) # Select Children
        c4d.CallCommand(16768, 16768) # Connect Objects + Delete
def CurrentStateToObject(obj,doc,settings) :
    doc = c4d.documents.GetActiveDocument()
    doc.SetActiveObject(obj)
    current(obj,doc,settings)
    
def main():
    doc = c4d.documents.GetActiveDocument()
    selected = doc.GetActiveObjects(0)
    settings = c4d.BaseContainer()
    if len(selected) > 0:
        c4d.StopAllThreads()
        doc.StartUndo()
        for obj in selected:
            CurrentStateToObject(obj,doc,settings)

        doc.EndUndo()

if __name__=='__main__':
    main()