# Cinema 4D Python Script
# Advanced OpenPose Sequence Generator UI v4.1
# Fix: Replaced arbitrary joint axes with Anatomical Vector Math for Virtual Face

import c4d
from c4d import gui, bitmaps, storage
import math
import os
import re

# -----------------------------
# CONSTANTS & MAPPINGS
# -----------------------------
DIALOG_ID = 1059998 

ID_GRP_MAIN = 1000
ID_GRP_SETTINGS = 1001
ID_GRP_LINKS = 1002
ID_GRP_ACTION = 1003

ID_IN_FOLDER = 2000
ID_BTN_FOLDER = 2001
ID_IN_WIDTH = 2002
ID_IN_HEIGHT = 2003
ID_IN_THICKNESS = 2004
ID_IN_RADIUS = 2005
ID_CHK_BONES = 2006
ID_CHK_POINTS = 2007
ID_COMBO_FORMAT = 2008  
ID_CHK_VIRTUAL_FACE = 2009 

ID_BTN_AUTODETECT = 3000
ID_LINK_BASE = 4000 

ID_BTN_RENDER = 5000
ID_TXT_STATUS = 5001

COCO_LABELS = {
    0: "0: Nose / Head Base", 1: "1: Neck",
    2: "2: Right Shoulder",   3: "3: Right ForeArm",  4: "4: Right Hand",
    5: "5: Left Shoulder",    6: "6: Left ForeArm",   7: "7: Left Hand",
    8: "8: Right UpLeg",      9: "9: Right Leg",      10: "10: Right Foot",
    11: "11: Left UpLeg",     12: "12: Left Leg",     13: "13: Left Foot",
    14: "14: Right Eye",      15: "15: Left Eye",
    16: "16: Right Ear",      17: "17: Left Ear"
}

COLORS = {
    0: (255, 0, 0),    1: (255, 85, 0),   2: (255, 170, 0),  3: (255, 255, 0),
    4: (170, 255, 0),  5: (85, 255, 0),   6: (0, 255, 0),    7: (0, 255, 85),
    8: (0, 255, 170),  9: (0, 255, 255),  10: (0, 170, 255), 11: (0, 85, 255),
    12: (0, 0, 255),   13: (85, 0, 255),  14: (170, 0, 255), 15: (255, 0, 255),
    16: (255, 0, 170), 17: (255, 0, 85)
}

OPENPOSE_PAIRS = [
    (1, 2, 2), (2, 3, 3), (3, 4, 4),       
    (1, 5, 5), (5, 6, 6), (6, 7, 7),       
    (1, 8, 8), (8, 9, 9), (9, 10, 10),     
    (1, 11, 11), (11, 12, 12), (12, 13, 13), 
    (1, 0, 0),                             
    (0, 14, 14), (14, 16, 16),             
    (0, 15, 15), (15, 17, 17)              
]

PREFIX_RE = re.compile(r'^(?:mixamorig\d*[:\s]?|mocaprig_|DEF-|ORG-|MCH-|VIS-|c_|b_|jnt_|j_|Bip001\s*|Bip01\s*|CC_Base_|Genesis\d+_|mixamo:|iClone\w*_|RL_Bone)', re.IGNORECASE)
ACCURIG_RE = re.compile(r'^accrig_', re.IGNORECASE)
SIDE_SUFFIX_RE = re.compile(r'[._\s-](L|R|left|right)$', re.IGNORECASE)

MIXAMO_TO_OPENPOSE = {
    "Head": 0, "Neck": 1,
    "RightArm": 2, "RightForeArm": 3, "RightHand": 4,
    "LeftArm": 5, "LeftForeArm": 6, "LeftHand": 7,
    "RightUpLeg": 8, "RightLeg": 9, "RightFoot": 10,
    "LeftUpLeg": 11, "LeftLeg": 12, "LeftFoot": 13,
    "RightEye": 14, "LeftEye": 15, "RightEar": 16, "LeftEar": 17
}

def normalize_bone_name(raw_name):
    name = raw_name.strip()
    exact_maps = {
        "CC_Base_Hip": "Hips", "CC_Base_L_Upperarm": "LeftArm", "CC_Base_L_Forearm": "LeftForeArm", 
        "CC_Base_L_Hand": "LeftHand", "CC_Base_R_Upperarm": "RightArm", "CC_Base_R_Forearm": "RightForeArm", 
        "CC_Base_R_Hand": "RightHand", "CC_Base_L_Thigh": "LeftUpLeg", "CC_Base_L_Calf": "LeftLeg", 
        "CC_Base_L_Foot": "LeftFoot", "CC_Base_R_Thigh": "RightUpLeg", "CC_Base_R_Calf": "RightLeg", 
        "CC_Base_R_Foot": "RightFoot", "CC_Base_Head": "Head", "CC_Base_NeckTwist01": "Neck",
        "hip": "Hips", "pelvis": "Hips", "head": "Head", "neckLower": "Neck",
        "lShldrBend": "LeftArm", "lForearmBend": "LeftForeArm", "lHand": "LeftHand",
        "rShldrBend": "RightArm", "rForearmBend": "RightForeArm", "rHand": "RightHand",
        "lThighBend": "LeftUpLeg", "lShin": "LeftLeg", "lFoot": "LeftFoot",
        "rThighBend": "RightUpLeg", "rShin": "RightLeg", "rFoot": "RightFoot",
        "LeftEye": "LeftEye", "RightEye": "RightEye", "LeftEar": "LeftEar", "RightEar": "RightEar"
    }
    if name in exact_maps: return exact_maps[name]
    name = ACCURIG_RE.sub("", name)
    name = PREFIX_RE.sub("", name).strip()
    if name in exact_maps: return exact_maps[name]
    m = SIDE_SUFFIX_RE.search(name)
    if m:
        side = m.group(1).lower()
        base = name[:m.start()]
        name = ("Left" if side in ("l", "left") else "Right") + base
    key = name.lower().replace("_","").replace(" ","").replace(".","").replace("-","")
    segment_map = {
        "lupperarm": "LeftArm", "llowerarm": "LeftForeArm", "lforearm": "LeftForeArm", "lhand": "LeftHand",
        "rupperarm": "RightArm", "rlowerarm": "RightForeArm", "rforearm": "RightForeArm", "rhand": "RightHand",
        "lthigh": "LeftUpLeg", "lupleg": "LeftUpLeg", "lleg": "LeftLeg", "lcalf": "LeftLeg", "lfoot": "LeftFoot",
        "rthigh": "RightUpLeg", "rupleg": "RightUpLeg", "rleg": "RightLeg", "rcalf": "RightLeg", "rfoot": "RightFoot"
    }
    if key in segment_map: return segment_map[key]
    return name

def get_all_objects(op):
    while op:
        yield op
        for child in get_all_objects(op.GetDown()):
            yield child
        op = op.GetNext()

# -----------------------------
# UI DIALOG CLASS
# -----------------------------
class OpenPoseDialog(gui.GeDialog):
    
    def __init__(self):
        self.link_boxes = {}

    def CreateLayout(self):
        self.SetTitle("Advanced OpenPose Generator (v4.1)")
        
        self.GroupBegin(ID_GRP_SETTINGS, c4d.BFH_SCALEFIT, 2, 0, "Render Settings")
        self.GroupBorderSpace(10, 10, 10, 10)
        self.GroupBorder(c4d.BORDER_GROUP_IN)
        
        self.AddStaticText(0, c4d.BFH_LEFT, name="Output Folder:")
        self.GroupBegin(0, c4d.BFH_SCALEFIT, 2, 0)
        self.AddEditText(ID_IN_FOLDER, c4d.BFH_SCALEFIT, 200, 0)
        self.AddButton(ID_BTN_FOLDER, c4d.BFH_LEFT, 30, 0, "...")
        self.GroupEnd()

        self.AddStaticText(0, c4d.BFH_LEFT, name="Output Format:")
        self.AddComboBox(ID_COMBO_FORMAT, c4d.BFH_LEFT, 240, 0)
        self.AddChild(ID_COMBO_FORMAT, 0, "PNG Sequence (Lossless - Best for AI)")
        self.AddChild(ID_COMBO_FORMAT, 1, "JPG Sequence (High Quality)")
        self.AddChild(ID_COMBO_FORMAT, 2, "MP4 Video (Warning: Color compression)")
        
        self.AddStaticText(0, c4d.BFH_LEFT, name="Resolution (W x H):")
        self.GroupBegin(0, c4d.BFH_LEFT, 3, 0)
        self.AddEditNumberArrows(ID_IN_WIDTH, c4d.BFH_LEFT, 70, 0)
        self.AddStaticText(0, c4d.BFH_LEFT, name=" x ")
        self.AddEditNumberArrows(ID_IN_HEIGHT, c4d.BFH_LEFT, 70, 0)
        self.GroupEnd()
        
        self.AddStaticText(0, c4d.BFH_LEFT, name="Line Thickness / Radius:")
        self.GroupBegin(0, c4d.BFH_LEFT, 3, 0)
        self.AddEditNumberArrows(ID_IN_THICKNESS, c4d.BFH_LEFT, 70, 0)
        self.AddStaticText(0, c4d.BFH_LEFT, name=" / ")
        self.AddEditNumberArrows(ID_IN_RADIUS, c4d.BFH_LEFT, 70, 0)
        self.GroupEnd()
        
        self.AddStaticText(0, c4d.BFH_LEFT, name="Features:")
        self.GroupBegin(0, c4d.BFH_LEFT, 1, 0)
        self.GroupBegin(0, c4d.BFH_LEFT, 2, 0)
        self.AddCheckbox(ID_CHK_BONES, c4d.BFH_LEFT, 0, 0, "Bones")
        self.AddCheckbox(ID_CHK_POINTS, c4d.BFH_LEFT, 0, 0, "Joints")
        self.GroupEnd()
        self.AddCheckbox(ID_CHK_VIRTUAL_FACE, c4d.BFH_LEFT, 0, 0, "Auto-Generate Virtual Face (Fix Backwards Walking)")
        self.GroupEnd()
        
        self.GroupEnd()
        
        self.AddSeparatorH(c4d.BFH_SCALEFIT)
        
        self.GroupBegin(ID_GRP_LINKS, c4d.BFH_SCALEFIT, 1, 0, "Joint Mapping")
        self.GroupBorderSpace(10, 10, 10, 10)
        
        self.AddButton(ID_BTN_AUTODETECT, c4d.BFH_SCALEFIT, 0, 20, "⚡ Auto-Detect from Selected Rig Root")
        self.AddStaticText(0, c4d.BFH_CENTER, name="(Drag & Drop overrides into the boxes below if needed)")
        
        self.GroupBegin(0, c4d.BFH_SCALEFIT, 4, 0)
        bc = c4d.BaseContainer()
        bc.SetInt32(c4d.DESC_ACCEPT, c4d.Obase) 
        
        for i in range(9):
            self.AddStaticText(0, c4d.BFH_LEFT, name=COCO_LABELS[i])
            self.link_boxes[i] = self.AddCustomGui(ID_LINK_BASE + i, c4d.CUSTOMGUI_LINKBOX, "", c4d.BFH_SCALEFIT, 150, 0, bc)
            
            idx_right = i + 9
            self.AddStaticText(0, c4d.BFH_LEFT, name=COCO_LABELS[idx_right])
            self.link_boxes[idx_right] = self.AddCustomGui(ID_LINK_BASE + idx_right, c4d.CUSTOMGUI_LINKBOX, "", c4d.BFH_SCALEFIT, 150, 0, bc)
        self.GroupEnd()
        self.GroupEnd() 
        
        self.AddSeparatorH(c4d.BFH_SCALEFIT)
        
        self.GroupBegin(ID_GRP_ACTION, c4d.BFH_SCALEFIT, 1, 0)
        self.GroupBorderSpace(10, 10, 10, 10)
        self.AddButton(ID_BTN_RENDER, c4d.BFH_SCALEFIT, 0, 30, " GENERATE OPENPOSE SEQUENCE")
        self.AddStaticText(ID_TXT_STATUS, c4d.BFH_CENTER, name="Ready.")
        self.GroupEnd()
        
        return True

    def InitValues(self):
        self.SetString(ID_IN_FOLDER, "C:/openpose_output")
        self.SetInt32(ID_COMBO_FORMAT, 0) 
        self.SetInt32(ID_IN_WIDTH, 1024)
        self.SetInt32(ID_IN_HEIGHT, 1024)
        self.SetInt32(ID_IN_THICKNESS, 10)
        self.SetInt32(ID_IN_RADIUS, 6)
        self.SetBool(ID_CHK_BONES, True)
        self.SetBool(ID_CHK_POINTS, True)
        self.SetBool(ID_CHK_VIRTUAL_FACE, True)
        return True

    def Command(self, id, msg):
        if id == ID_BTN_FOLDER:
            path = storage.LoadDialog(title="Select Output Folder", flags=c4d.FILESELECT_DIRECTORY)
            if path:
                self.SetString(ID_IN_FOLDER, path)
        elif id == ID_BTN_AUTODETECT:
            self.DoAutoDetect()
        elif id == ID_BTN_RENDER:
            self.DoRender()
        return True

    def DoAutoDetect(self):
        doc = c4d.documents.GetActiveDocument()
        root = doc.GetActiveObject()
        if not root:
            gui.MessageDialog("Please select the root Null or Joint of your rig in the Object Manager first.")
            return
            
        for i in range(18):
            self.link_boxes[i].SetLink(None)
            
        count = 0
        for obj in get_all_objects(root):
            raw_name = obj.GetName()
            canonical_name = normalize_bone_name(raw_name)
            
            if canonical_name in MIXAMO_TO_OPENPOSE:
                idx = MIXAMO_TO_OPENPOSE[canonical_name]
                self.link_boxes[idx].SetLink(obj)
                count += 1
                
        self.SetString(ID_TXT_STATUS, f"Auto-detected and mapped {count} joints.")

    def DoRender(self):
        doc = c4d.documents.GetActiveDocument()
        bd = doc.GetActiveBaseDraw()
        
        folder = self.GetString(ID_IN_FOLDER)
        out_fmt = self.GetInt32(ID_COMBO_FORMAT)
        img_w = self.GetInt32(ID_IN_WIDTH)
        img_h = self.GetInt32(ID_IN_HEIGHT)
        thick = self.GetInt32(ID_IN_THICKNESS)
        radius = self.GetInt32(ID_IN_RADIUS)
        draw_bones = self.GetBool(ID_CHK_BONES)
        draw_points = self.GetBool(ID_CHK_POINTS)
        use_virtual_face = self.GetBool(ID_CHK_VIRTUAL_FACE)

        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except Exception as e:
                gui.MessageDialog(f"Could not create folder: {e}")
                return

        active_joints = {}
        for i in range(18):
            obj = self.link_boxes[i].GetLink(doc, 0)
            if obj:
                active_joints[i] = obj
                
        if not active_joints:
            gui.MessageDialog("No joints mapped! Please use Auto-Detect or drag joints into the boxes.")
            return

        start = doc.GetMinTime().GetFrame(doc.GetFps())
        end = doc.GetMaxTime().GetFrame(doc.GetFps())
        total_frames = end - start + 1
        fps = doc.GetFps()

        self.SetString(ID_TXT_STATUS, "Initializing Render...")
        c4d.gui.StatusSetBar(0)
        
        frame_dict = bd.GetFrame()
        cl, cr = frame_dict["cl"], frame_dict["cr"]
        ct, cb = frame_dict["ct"], frame_dict["cb"]
        vp_w = float(cr - cl + 1)
        vp_h = float(cb - ct + 1)

        is_video = (out_fmt == 2)
        movie_saver = None
        if is_video:
            movie_saver = bitmaps.MovieSaver()
            mp4_path = os.path.join(folder, "openpose_sequence.mp4")
            mp4_id = getattr(c4d, 'FORMAT_MP4', 1025520) 
            
            init_clip = bitmaps.GeClipMap()
            init_clip.Init(img_w, img_h, 32)
            dummy_bmp = init_clip.GetBitmap()
            
            if not movie_saver.Open(mp4_path, dummy_bmp, fps, mp4_id, c4d.BaseContainer(), c4d.SAVEBIT_NONE):
                gui.MessageDialog("Failed to initialize MP4 Video Saver.")
                return

        for i, f in enumerate(range(start, end + 1)):
            self.SetString(ID_TXT_STATUS, f"Rendering Frame {f} ({i+1}/{total_frames})...")
            c4d.gui.StatusSetBar(int((i / total_frames) * 100))
            
            doc.SetTime(c4d.BaseTime(f, fps))
            doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)

            points = {}
            for idx, joint in active_joints.items():
                screen = bd.WS(joint.GetMg().off)
                if vp_w > 0 and vp_h > 0:
                    nx = ((screen.x - cl) / vp_w) * img_w
                    ny = ((screen.y - ct) / vp_h) * img_h
                    points[idx] = (int(nx), int(ny))

            # --- ANATOMICAL VIRTUAL FACE GENERATOR ---
            if use_virtual_face and all(j in active_joints for j in [0, 1, 2, 5]):
                head_pos = active_joints[0].GetMg().off
                neck_pos = active_joints[1].GetMg().off
                r_shoulder_pos = active_joints[2].GetMg().off
                l_shoulder_pos = active_joints[5].GetMg().off
                
                head_scale = (head_pos - neck_pos).GetLength() * 1.5

                # 1. UP vector (Neck to Head)
                up = (head_pos - neck_pos).GetNormalized()
                
                # 2. RIGHT vector (Left Shoulder to Right Shoulder)
                # Note: Mixamo 2=Right, 5=Left. Vector from 5 to 2 points to Character's Right.
                right = (r_shoulder_pos - l_shoulder_pos).GetNormalized()
                
                # 3. FORWARD vector (Cross product)
                # Right(X) x Up(Y) = -Z (Backwards). Up(Y) x Right(X) = Z (Forward).
                forward = up.Cross(right).GetNormalized()

                # Calculate spatial offsets purely based on anatomy, ignoring joint rotation
                nose_3d = head_pos + (up * (head_scale * 0.3)) + (forward * (head_scale * 0.45))
                r_eye_3d = head_pos + (up * (head_scale * 0.55)) + (forward * (head_scale * 0.4)) + (right * (head_scale * 0.2))
                l_eye_3d = head_pos + (up * (head_scale * 0.55)) + (forward * (head_scale * 0.4)) - (right * (head_scale * 0.2))
                r_ear_3d = head_pos + (up * (head_scale * 0.45)) - (forward * (head_scale * 0.1)) + (right * (head_scale * 0.4))
                l_ear_3d = head_pos + (up * (head_scale * 0.45)) - (forward * (head_scale * 0.1)) - (right * (head_scale * 0.4))

                def proj(p3d):
                    s = bd.WS(p3d)
                    return (int(((s.x - cl) / vp_w) * img_w), int(((s.y - ct) / vp_h) * img_h))

                if vp_w > 0 and vp_h > 0:
                    points[0] = proj(nose_3d) 
                    if 14 not in active_joints: points[14] = proj(r_eye_3d)
                    if 15 not in active_joints: points[15] = proj(l_eye_3d)
                    if 16 not in active_joints: points[16] = proj(r_ear_3d)
                    if 17 not in active_joints: points[17] = proj(l_ear_3d)

            # Auto-Neck Generator (if 1 is missing, but 2 and 5 exist)
            if 1 not in points and 2 in points and 5 in points:
                points[1] = ((points[2][0] + points[5][0]) // 2, (points[2][1] + points[5][1]) // 2)

            clip = bitmaps.GeClipMap()
            clip.Init(img_w, img_h, 32)
            clip.BeginDraw()
            clip.SetColor(0, 0, 0, 255)
            clip.FillRect(0, 0, img_w, img_h)

            if draw_bones:
                for a, b, color_idx in OPENPOSE_PAIRS:
                    if a in points and b in points:
                        col = COLORS.get(color_idx, (255, 255, 255))
                        clip.SetColor(col[0], col[1], col[2], 255)
                        dist = math.hypot(points[b][0] - points[a][0], points[b][1] - points[a][1])
                        if dist > 0:
                            steps = int(dist)
                            rad = thick // 2
                            for st in range(steps + 1):
                                t = st / float(steps)
                                cx = int(points[a][0] + (points[b][0] - points[a][0]) * t)
                                cy = int(points[a][1] + (points[b][1] - points[a][1]) * t)
                                clip.FillEllipse(cx - rad, cy - rad, cx + rad, cy + rad)

            if draw_points:
                for idx, p in points.items():
                    col = COLORS.get(idx, (255, 255, 255))
                    clip.SetColor(col[0], col[1], col[2], 255)
                    clip.FillEllipse(p[0] - radius, p[1] - radius, p[0] + radius, p[1] + radius)

            clip.EndDraw()
            bmp = clip.GetBitmap()

            if is_video:
                movie_saver.Write(bmp)
            else:
                ext = "png" if out_fmt == 0 else "jpg"
                fmt_id = c4d.FILTER_PNG if out_fmt == 0 else c4d.FILTER_JPG
                filename = os.path.join(folder, f"openpose_{f:04d}.{ext}")
                bmp.Save(filename, fmt_id)

        if is_video:
            movie_saver.Close()
            msg = f"Successfully generated MP4 video to:\n{mp4_path}"
        else:
            msg = f"Successfully generated {total_frames} frames to:\n{folder}"

        self.SetString(ID_TXT_STATUS, "Done!")
        c4d.gui.StatusClear()
        gui.MessageDialog(msg)

# -----------------------------
# EXECUTION
# -----------------------------
if __name__ == "__main__":
    global dlg
    dlg = OpenPoseDialog()
    dlg.Open(dlgtype=c4d.DLG_TYPE_ASYNC, defaultw=400, defaulth=500)