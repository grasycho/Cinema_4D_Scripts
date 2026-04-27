
AI Overview
OpenPose Scripts
— Advanced script mapping rig joints to COCO-18 keypoints with anatomical virtual face generation features.1
— Python script designed for Cinema 4D to generate OpenPose image sequences from character rig joints.2
Folders
— Directory containing tools and scripts for generating OpenPose data from Cinema 4D projects.3
OpenPose_Sequence_Generator_From_Selected_Joints_v2.py
# Cinema 4D Python Script
# Advanced OpenPose Sequence Generator UI v4.5
# Spec audit fixes vs v4.4:
#   - OPENPOSE_PAIRS: Added missing RShoulder->REar (2,16) and LShoulder->LEar (5,17) limb pairs.
#   - MIXAMO_TO_OPENPOSE: "Head" no longer maps to index 0 (Nose). Head joint is now the
#     anchor for the Virtual Face generator only. Index 0 is exclusively Nose/Virtual Nose.
#   - COCO_LABELS[0] corrected to "0: Nose" (was misleadingly "Nose / Head Base").
#   - Virtual Face: "head" joint from rig drives face geometry but is NOT plotted as joint 0.
#     Joint 0 (Nose) is always synthesised by the Virtual Face generator from the head anchor.
#   - Added HEAD_ANCHOR_IDX = 18 as a virtual 19th slot for the rig's head root joint,
#     separate from all 18 COCO keypoints.
#   - COLORS updated: pairs (2,16) and (5,17) now use correct color indices.

import c4d
from c4d import gui, bitmaps, storage
import math
import os
import re
import subprocess
import sys

# -----------------------------
# CONSTANTS & MAPPINGS
# -----------------------------
DIALOG_ID = 1059998

ID_GRP_MAIN         = 1000
ID_GRP_SETTINGS     = 1001
ID_GRP_LINKS        = 1002
ID_GRP_ACTION       = 1003

ID_IN_FOLDER        = 2000
ID_BTN_FOLDER       = 2001
ID_IN_WIDTH         = 2002
ID_IN_HEIGHT        = 2003
ID_IN_THICKNESS     = 2004
ID_IN_RADIUS        = 2005
ID_CHK_BONES        = 2006
ID_CHK_POINTS       = 2007
ID_COMBO_FORMAT     = 2008
ID_CHK_VIRTUAL_FACE = 2009

ID_BTN_AUTODETECT   = 3000
ID_LINK_BASE        = 4000   # slots 4000–4017 = COCO joints 0–17
                              # slot  4018      = Head anchor (virtual face root)

ID_BTN_RENDER       = 5000
ID_TXT_STATUS       = 5001

# Slot index used internally for the rig's head-root joint (NOT a COCO keypoint)
HEAD_ANCHOR_IDX = 18

# Official OpenPose COCO-18 keypoint labels (poseParameters.cpp)
COCO_LABELS = {
    0:  "0: Nose",            1:  "1: Neck",
    2:  "2: RShoulder",       3:  "3: RElbow",        4:  "4: RWrist",
    5:  "5: LShoulder",       6:  "6: LElbow",         7:  "7: LWrist",
    8:  "8: RHip",            9:  "9: RKnee",          10: "10: RAnkle",
    11: "11: LHip",           12: "12: LKnee",          13: "13: LAnkle",
    14: "14: REye",           15: "15: LEye",
    16: "16: REar",           17: "17: LEar",
    # Slot 18 is the rig's Head anchor — used only for Virtual Face math, never drawn as a keypoint
    HEAD_ANCHOR_IDX: "18: Head Anchor (Virtual Face Root)"
}

# OpenPose standard rainbow gradient colors per keypoint index
COLORS = {
    0:  (255,   0,   0),  1:  (255,  85,   0),  2:  (255, 170,   0),  3:  (255, 255,   0),
    4:  (170, 255,   0),  5:  ( 85, 255,   0),  6:  (  0, 255,   0),  7:  (  0, 255,  85),
    8:  (  0, 255, 170),  9:  (  0, 255, 255),  10: (  0, 170, 255),  11: (  0,  85, 255),
    12: (  0,   0, 255),  13: ( 85,   0, 255),  14: (170,   0, 255),  15: (255,   0, 255),
    16: (255,   0, 170),  17: (255,   0,  85)
}

# Official COCO-18 limb pairs from poseParameters.cpp POSE_COCO_PAIRS:
# {1,2, 1,5, 2,3, 3,4, 5,6, 6,7, 1,8, 8,9, 9,10, 1,11, 11,12, 12,13,
#  1,0, 0,14, 14,16, 0,15, 15,17, 2,16, 5,17}  — 19 pairs total
# Tuple format: (joint_a, joint_b, color_index)
OPENPOSE_PAIRS = [
    # Torso + arms
    (1,  2,  2),  (2,  3,  3),  (3,  4,  4),   # Neck→RShoulder→RElbow→RWrist
    (1,  5,  5),  (5,  6,  6),  (6,  7,  7),   # Neck→LShoulder→LElbow→LWrist
    # Legs
    (1,  8,  8),  (8,  9,  9),  (9, 10, 10),   # Neck→RHip→RKnee→RAnkle
    (1, 11, 11),  (11,12, 12),  (12,13, 13),   # Neck→LHip→LKnee→LAnkle
    # Nose
    (1,  0,  0),                                # Neck→Nose
    # Right face
    (0, 14, 14),  (14,16, 16),                  # Nose→REye→REar
    # Left face
    (0, 15, 15),  (15,17, 17),                  # Nose→LEye→LEar
    # FIX: Missing shoulder-to-ear connections (officially part of COCO pairs)
    (2, 16, 16),                                # RShoulder→REar
    (5, 17, 17),                                # LShoulder→LEar
]

PREFIX_RE      = re.compile(
    r'^(?:mixamorig\d*[:\s]?|mocaprig_|DEF-|ORG-|MCH-|VIS-|c_|b_|jnt_|j_'
    r'|Bip001\s*|Bip01\s*|CC_Base_|Genesis\d+_|mixamo:|iClone\w*_|RL_Bone)',
    re.IGNORECASE)
ACCURIG_RE     = re.compile(r'^accrig_', re.IGNORECASE)
SIDE_SUFFIX_RE = re.compile(r'[._\s-](L|R|left|right)$', re.IGNORECASE)

# FIX: "Head" no longer maps to keypoint 0 (Nose). The rig's head-root joint
# is mapped to HEAD_ANCHOR_IDX (18) and used only as the origin for virtual-face
# geometry. The actual Nose position (index 0) is always synthesised.
MIXAMO_TO_OPENPOSE = {
    "Head":      HEAD_ANCHOR_IDX,   # Head ROOT → virtual-face anchor only, NOT drawn as joint 0
    "Neck":      1,
    "RightArm":  2,  "RightForeArm": 3,  "RightHand": 4,
    "LeftArm":   5,  "LeftForeArm":  6,  "LeftHand":  7,
    "RightUpLeg":8,  "RightLeg":     9,  "RightFoot": 10,
    "LeftUpLeg": 11, "LeftLeg":      12, "LeftFoot":  13,
    "RightEye":  14, "LeftEye":      15,
    "RightEar":  16, "LeftEar":      17,
}

# -----------------------------
# HELPERS
# -----------------------------
def normalize_bone_name(raw_name):
    name = raw_name.strip()
    exact_maps = {
        "CC_Base_Hip": "Hips",              "CC_Base_L_Upperarm": "LeftArm",
        "CC_Base_L_Forearm": "LeftForeArm", "CC_Base_L_Hand": "LeftHand",
        "CC_Base_R_Upperarm": "RightArm",   "CC_Base_R_Forearm": "RightForeArm",
        "CC_Base_R_Hand": "RightHand",      "CC_Base_L_Thigh": "LeftUpLeg",
        "CC_Base_L_Calf": "LeftLeg",        "CC_Base_L_Foot": "LeftFoot",
        "CC_Base_R_Thigh": "RightUpLeg",    "CC_Base_R_Calf": "RightLeg",
        "CC_Base_R_Foot": "RightFoot",      "CC_Base_Head": "Head",
        "CC_Base_NeckTwist01": "Neck",      "hip": "Hips",
        "pelvis": "Hips",                   "head": "Head",
        "neckLower": "Neck",                "lShldrBend": "LeftArm",
        "lForearmBend": "LeftForeArm",      "lHand": "LeftHand",
        "rShldrBend": "RightArm",           "rForearmBend": "RightForeArm",
        "rHand": "RightHand",               "lThighBend": "LeftUpLeg",
        "lShin": "LeftLeg",                 "lFoot": "LeftFoot",
        "rThighBend": "RightUpLeg",         "rShin": "RightLeg",
        "rFoot": "RightFoot",               "LeftEye": "LeftEye",
        "RightEye": "RightEye",             "LeftEar": "LeftEar",
        "RightEar": "RightEar"
    }
    if name in exact_maps:
        return exact_maps[name]
    name = ACCURIG_RE.sub("", name)
    name = PREFIX_RE.sub("", name).strip()
    if name in exact_maps:
        return exact_maps[name]
    m = SIDE_SUFFIX_RE.search(name)
    if m:
        side = m.group(1).lower()
        base = name[:m.start()]
        name = ("Left" if side in ("l", "left") else "Right") + base
    key = name.lower().replace("_","").replace(" ","").replace(".","").replace("-","")
    segment_map = {
        "lupperarm": "LeftArm",     "llowerarm": "LeftForeArm",
        "lforearm":  "LeftForeArm", "lhand":     "LeftHand",
        "rupperarm": "RightArm",    "rlowerarm":  "RightForeArm",
        "rforearm":  "RightForeArm","rhand":      "RightHand",
        "lthigh":    "LeftUpLeg",   "lupleg":     "LeftUpLeg",
        "lleg":      "LeftLeg",     "lcalf":      "LeftLeg",
        "lfoot":     "LeftFoot",    "rthigh":     "RightUpLeg",
        "rupleg":    "RightUpLeg",  "rleg":        "RightLeg",
        "rcalf":     "RightLeg",    "rfoot":       "RightFoot"
    }
    return segment_map.get(key, name)


def iter_hierarchy(root):
    """Iterative depth-first traversal — avoids recursion limit on deep rigs."""
    stack = [root]
    while stack:
        op = stack.pop()
        if op is None:
            continue
        yield op
        sibling = op.GetNext()
        if sibling:
            stack.append(sibling)
        child = op.GetDown()
        if child:
            stack.append(child)


def get_viewport_rect(bd):
    try:
        frame = bd.GetFrame()
        if isinstance(frame, dict):
            return frame["cl"], frame["cr"], frame["ct"], frame["cb"]
        return frame.cl, frame.cr, frame.ct, frame.cb
    except Exception:
        pass
    try:
        return 0, bd.GetWidth() - 1, 0, bd.GetHeight() - 1
    except Exception:
        return 0, 1023, 0, 1023


def fill_ellipse_safe(clip, x1, y1, x2, y2):
    if x2 <= x1 or y2 <= y1:
        clip.SetPixel(max(x1, 0), max(y1, 0))
        return
    clip.FillEllipse(x1, y1, x2, y2)


def draw_thick_line(clip, ax, ay, bx, by, half_r):
    dist  = math.hypot(bx - ax, by - ay)
    steps = max(int(dist), 1)
    for st in range(steps + 1):
        t  = st / float(steps)
        cx = int(ax + (bx - ax) * t)
        cy = int(ay + (by - ay) * t)
        fill_ellipse_safe(clip, cx - half_r, cy - half_r, cx + half_r, cy + half_r)


# -----------------------------
# UI DIALOG CLASS
# -----------------------------
class OpenPoseDialog(gui.GeDialog):

    def __init__(self):
        self.link_boxes = {}

    def CreateLayout(self):
        self.SetTitle("Advanced OpenPose Generator (v4.5)")

        # ---- Settings Group ----
        self.GroupBegin(ID_GRP_SETTINGS, c4d.BFH_SCALEFIT, 2, 0, "Render Settings")
        self.GroupBorder(c4d.BORDER_GROUP_IN)
        self.GroupBorderSpace(10, 10, 10, 10)

        self.AddStaticText(0, c4d.BFH_LEFT, name="Output Folder:")
        self.GroupBegin(0, c4d.BFH_SCALEFIT, 2, 0)
        self.AddEditText(ID_IN_FOLDER, c4d.BFH_SCALEFIT, 200, 0)
        self.AddButton(ID_BTN_FOLDER, c4d.BFH_LEFT, 30, 0, "...")
        self.GroupEnd()

        self.AddStaticText(0, c4d.BFH_LEFT, name="Output Format:")
        self.AddComboBox(ID_COMBO_FORMAT, c4d.BFH_LEFT, 260, 0)
        self.AddChild(ID_COMBO_FORMAT, 0, "PNG Sequence (Lossless - Best for AI)")
        self.AddChild(ID_COMBO_FORMAT, 1, "JPG Sequence (High Quality)")
        self.AddChild(ID_COMBO_FORMAT, 2, "MP4 Video (Direct via FFmpeg)")

        self.AddStaticText(0, c4d.BFH_LEFT, name="Resolution (W x H):")
        self.GroupBegin(0, c4d.BFH_LEFT, 3, 0)
        self.AddEditNumberArrows(ID_IN_WIDTH,  c4d.BFH_LEFT, 70, 0)
        self.AddStaticText(0, c4d.BFH_LEFT, name=" x ")
        self.AddEditNumberArrows(ID_IN_HEIGHT, c4d.BFH_LEFT, 70, 0)
        self.GroupEnd()

        self.AddStaticText(0, c4d.BFH_LEFT, name="Line Thickness / Radius:")
        self.GroupBegin(0, c4d.BFH_LEFT, 3, 0)
        self.AddEditNumberArrows(ID_IN_THICKNESS, c4d.BFH_LEFT, 70, 0)
        self.AddStaticText(0, c4d.BFH_LEFT, name=" / ")
        self.AddEditNumberArrows(ID_IN_RADIUS,    c4d.BFH_LEFT, 70, 0)
        self.GroupEnd()

        self.AddStaticText(0, c4d.BFH_LEFT, name="Features:")
        self.GroupBegin(0, c4d.BFH_LEFT, 1, 0)
        self.GroupBegin(0, c4d.BFH_LEFT, 2, 0)
        self.AddCheckbox(ID_CHK_BONES,  c4d.BFH_LEFT, 0, 0, "Bones")
        self.AddCheckbox(ID_CHK_POINTS, c4d.BFH_LEFT, 0, 0, "Joints")
        self.GroupEnd()
        self.AddCheckbox(ID_CHK_VIRTUAL_FACE, c4d.BFH_LEFT, 0, 0,
                         "Auto-Generate Virtual Face (requires Head Anchor)")
        self.GroupEnd()
        self.GroupEnd()  # ID_GRP_SETTINGS

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # ---- Joint Mapping Group ----
        self.GroupBegin(ID_GRP_LINKS, c4d.BFH_SCALEFIT, 1, 0, "Joint Mapping")
        self.GroupBorderSpace(10, 10, 10, 10)

        self.AddButton(ID_BTN_AUTODETECT, c4d.BFH_SCALEFIT, 0, 20,
                       "Auto-Detect from Selected Rig Root")
        self.AddStaticText(0, c4d.BFH_CENTER,
                           name="(Drag & Drop overrides into the boxes below if needed)")

        bc = c4d.BaseContainer()
        bc.SetInt32(c4d.DESC_ACCEPT, c4d.Obase)

        # 10 rows of 2 columns (indices 0-9 left, 10-18 right, giving 19 slots total)
        self.GroupBegin(0, c4d.BFH_SCALEFIT, 4, 0)
        for i in range(10):
            self.AddStaticText(0, c4d.BFH_LEFT, name=COCO_LABELS.get(i, ""))
            self.link_boxes[i] = self.AddCustomGui(
                ID_LINK_BASE + i, c4d.CUSTOMGUI_LINKBOX, "",
                c4d.BFH_SCALEFIT, 150, 0, bc)
            idx_right = i + 10
            if idx_right <= HEAD_ANCHOR_IDX:
                self.AddStaticText(0, c4d.BFH_LEFT, name=COCO_LABELS.get(idx_right, ""))
                self.link_boxes[idx_right] = self.AddCustomGui(
                    ID_LINK_BASE + idx_right, c4d.CUSTOMGUI_LINKBOX, "",
                    c4d.BFH_SCALEFIT, 150, 0, bc)
            else:
                self.AddStaticText(0, c4d.BFH_LEFT, name="")
                self.AddStaticText(0, c4d.BFH_LEFT, name="")
        self.GroupEnd()
        self.GroupEnd()  # ID_GRP_LINKS

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # ---- Action Group ----
        self.GroupBegin(ID_GRP_ACTION, c4d.BFH_SCALEFIT, 1, 0)
        self.GroupBorderSpace(10, 10, 10, 10)
        self.AddButton(ID_BTN_RENDER, c4d.BFH_SCALEFIT, 0, 30,
                       "GENERATE OPENPOSE SEQUENCE")
        self.AddStaticText(ID_TXT_STATUS, c4d.BFH_CENTER, name="Ready.")
        self.GroupEnd()

        return True

    def InitValues(self):
        self.SetString(ID_IN_FOLDER,      "C:/openpose_output")
        self.SetInt32(ID_COMBO_FORMAT,    0)
        self.SetInt32(ID_IN_WIDTH,        1024)
        self.SetInt32(ID_IN_HEIGHT,       1024)
        self.SetInt32(ID_IN_THICKNESS,    10)
        self.SetInt32(ID_IN_RADIUS,       6)
        self.SetBool(ID_CHK_BONES,        True)
        self.SetBool(ID_CHK_POINTS,       True)
        self.SetBool(ID_CHK_VIRTUAL_FACE, True)
        return True

    def Command(self, id, msg):
        if id == ID_BTN_FOLDER:
            path = storage.LoadDialog(
                title="Select Output Folder",
                flags=c4d.FILESELECT_DIRECTORY)
            if path:
                self.SetString(ID_IN_FOLDER, path)
        elif id == ID_BTN_AUTODETECT:
            self.DoAutoDetect()
        elif id == ID_BTN_RENDER:
            self.DoRender()
        return True

    def _set_status(self, text):
        self.SetString(ID_TXT_STATUS, text)

    # ------------------------------------------------------------------
    def DoAutoDetect(self):
        doc  = c4d.documents.GetActiveDocument()
        root = doc.GetActiveObject()
        if not root:
            gui.MessageDialog(
                "Please select the root Null or Joint of your rig "
                "in the Object Manager first.")
            return

        for i in range(HEAD_ANCHOR_IDX + 1):
            if i in self.link_boxes:
                self.link_boxes[i].SetLink(None)

        count = 0
        for obj in iter_hierarchy(root):
            canonical = normalize_bone_name(obj.GetName())
            if canonical in MIXAMO_TO_OPENPOSE:
                idx = MIXAMO_TO_OPENPOSE[canonical]
                if idx in self.link_boxes:
                    self.link_boxes[idx].SetLink(obj)
                    count += 1

        self._set_status(f"Auto-detected and mapped {count} joints.")

    # ------------------------------------------------------------------
    def DoRender(self):
        doc = c4d.documents.GetActiveDocument()
        bd  = doc.GetActiveBaseDraw()

        if bd is None:
            gui.MessageDialog(
                "No active viewport found. Please click inside a viewport first.")
            return

        folder           = self.GetString(ID_IN_FOLDER)
        out_fmt          = self.GetInt32(ID_COMBO_FORMAT)
        img_w            = self.GetInt32(ID_IN_WIDTH)
        img_h            = self.GetInt32(ID_IN_HEIGHT)
        thick            = max(self.GetInt32(ID_IN_THICKNESS), 1)
        radius           = max(self.GetInt32(ID_IN_RADIUS), 1)
        draw_bones       = self.GetBool(ID_CHK_BONES)
        draw_points      = self.GetBool(ID_CHK_POINTS)
        use_virtual_face = self.GetBool(ID_CHK_VIRTUAL_FACE)

        direct_mp4 = (out_fmt == 2)
        if direct_mp4:
            out_fmt = 0

        if not folder:
            gui.MessageDialog("Please specify an output folder.")
            return
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except Exception as e:
                gui.MessageDialog(f"Could not create output folder:\n{e}")
                return

        # Collect all mapped joints (0–17 are COCO keypoints; 18 is head anchor)
        active_joints = {}
        for i in range(HEAD_ANCHOR_IDX + 1):
            if i not in self.link_boxes:
                continue
            obj = self.link_boxes[i].GetLink(doc, c4d.Obase)
            if obj:
                active_joints[i] = obj

        # Exclude the head anchor from the "no joints mapped" check
        coco_joints = {k: v for k, v in active_joints.items() if k < HEAD_ANCHOR_IDX}
        if not coco_joints:
            gui.MessageDialog(
                "No COCO joints mapped!\n"
                "Please use Auto-Detect or drag joints into the boxes.")
            return

        start        = doc.GetMinTime().GetFrame(doc.GetFps())
        end          = doc.GetMaxTime().GetFrame(doc.GetFps())
        total_frames = max(end - start + 1, 1)
        fps          = doc.GetFps()

        cl, cr, ct, cb = get_viewport_rect(bd)
        vp_w = float(max(cr - cl + 1, 1))
        vp_h = float(max(cb - ct + 1, 1))

        self._set_status("Initializing render...")
        c4d.gui.StatusSetBar(0)

        build_flags = getattr(c4d, "BUILDFLAGS_0", getattr(c4d, "BUILDFLAGS_NONE", 0))
        half_thick  = max(thick // 2, 1)
        fmt_id      = c4d.FILTER_PNG if out_fmt == 0 else c4d.FILTER_JPG
        ext         = "png"           if out_fmt == 0 else "jpg"

        def world_to_screen(p3d):
            s = bd.WS(p3d)
            return (int(((s.x - cl) / vp_w) * img_w),
                    int(((s.y - ct) / vp_h) * img_h))

        # ---- Frame loop ----
        for i, f in enumerate(range(start, end + 1)):
            self._set_status(f"Rendering frame {f}  ({i + 1}/{total_frames})")
            c4d.gui.StatusSetBar(int((i / total_frames) * 100))

            doc.SetTime(c4d.BaseTime(f, fps))
            doc.ExecutePasses(None, True, True, True, build_flags)

            # Project COCO keypoints (indices 0–17 only; head anchor 18 is math-only)
            points = {}
            for idx, joint in active_joints.items():
                if idx < HEAD_ANCHOR_IDX:   # only draw real COCO keypoints
                    points[idx] = world_to_screen(joint.GetMg().off)

            # ---- Anatomical Virtual Face Generator ----
            # Requires: HEAD_ANCHOR_IDX(18)=head root, 1=Neck, 2=RShoulder, 5=LShoulder
            if use_virtual_face and all(j in active_joints for j in [HEAD_ANCHOR_IDX, 1, 2, 5]):
                head_pos       = active_joints[HEAD_ANCHOR_IDX].GetMg().off
                neck_pos       = active_joints[1].GetMg().off
                r_shoulder_pos = active_joints[2].GetMg().off
                l_shoulder_pos = active_joints[5].GetMg().off

                neck_to_head = head_pos - neck_pos
                head_scale   = neck_to_head.GetLength() * 1.5

                up_len = neck_to_head.GetLength()
                up     = neck_to_head / up_len if up_len > 1e-6 else c4d.Vector(0, 1, 0)

                sh_vec = r_shoulder_pos - l_shoulder_pos
                sh_len = sh_vec.GetLength()
                right  = sh_vec / sh_len if sh_len > 1e-6 else c4d.Vector(1, 0, 0)

                forward = up.Cross(right)
                fwd_len = forward.GetLength()
                forward = forward / fwd_len if fwd_len > 1e-6 else c4d.Vector(0, 0, 1)

                # Synthesise all five face keypoints from head anchor geometry
                nose_3d  = head_pos + up * (head_scale * 0.30) + forward * (head_scale * 0.45)
                r_eye_3d = head_pos + up * (head_scale * 0.55) + forward * (head_scale * 0.40) + right * (head_scale * 0.20)
                l_eye_3d = head_pos + up * (head_scale * 0.55) + forward * (head_scale * 0.40) - right * (head_scale * 0.20)
                r_ear_3d = head_pos + up * (head_scale * 0.45) - forward * (head_scale * 0.10) + right * (head_scale * 0.40)
                l_ear_3d = head_pos + up * (head_scale * 0.45) - forward * (head_scale * 0.10) - right * (head_scale * 0.40)

                # Joint 0 (Nose) is always synthesised — never taken from the head-root joint
                points[0]  = world_to_screen(nose_3d)
                # Eyes/ears: synthesise only if not already provided by real rig joints
                if 14 not in active_joints: points[14] = world_to_screen(r_eye_3d)
                if 15 not in active_joints: points[15] = world_to_screen(l_eye_3d)
                if 16 not in active_joints: points[16] = world_to_screen(r_ear_3d)
                if 17 not in active_joints: points[17] = world_to_screen(l_ear_3d)

            # Auto-Neck: synthesise midpoint if neck joint is absent
            if 1 not in points and 2 in points and 5 in points:
                points[1] = (
                    (points[2][0] + points[5][0]) // 2,
                    (points[2][1] + points[5][1]) // 2
                )

            # ---- Draw frame ----
            clip = bitmaps.GeClipMap()
            clip.Init(img_w, img_h, 32)
            clip.BeginDraw()
            clip.SetColor(0, 0, 0, 255)
            clip.FillRect(0, 0, img_w - 1, img_h - 1)

            if draw_bones:
                for a, b, color_idx in OPENPOSE_PAIRS:
                    if a in points and b in points:
                        col = COLORS.get(color_idx, (255, 255, 255))
                        clip.SetColor(col[0], col[1], col[2], 255)
                        draw_thick_line(clip,
                                        points[a][0], points[a][1],
                                        points[b][0], points[b][1],
                                        half_thick)

            if draw_points:
                for idx, p in points.items():
                    col = COLORS.get(idx, (255, 255, 255))
                    clip.SetColor(col[0], col[1], col[2], 255)
                    fill_ellipse_safe(clip,
                                      p[0] - radius, p[1] - radius,
                                      p[0] + radius, p[1] + radius)

            clip.EndDraw()
            bmp   = clip.GetBitmap()
            fname = os.path.join(folder, f"openpose_{f:04d}.{ext}")
            bmp.Save(fname, fmt_id)

        # ---- Finalise & Direct MP4 Muxing ----
        c4d.gui.StatusClear()

        if direct_mp4:
            self._set_status("Muxing MP4 with FFmpeg...")
            mp4_path    = os.path.join(folder, "openpose_sequence.mp4")
            png_pattern = os.path.join(folder, "openpose_%04d.png")

            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(int(fps)),
                "-start_number", str(start),
                "-i", png_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                mp4_path
            ]
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

            try:
                result = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
                if result.returncode == 0:
                    for f_idx in range(start, end + 1):
                        tmp = os.path.join(folder, f"openpose_{f_idx:04d}.png")
                        if os.path.exists(tmp):
                            os.remove(tmp)
                    msg = f"Successfully generated MP4 video:\n{mp4_path}"
                else:
                    err = result.stderr.decode("utf-8", errors="ignore")
                    msg = (f"FFmpeg error. PNG frames kept in:\n{folder}\n\n"
                           f"FFmpeg output:\n{err[:400]}")
            except FileNotFoundError:
                msg = (f"FFmpeg not found on PATH.\n"
                       f"PNG frames kept in:\n{folder}\n\n"
                       f"Install FFmpeg and add it to your system PATH, then restart C4D.")
            except Exception as e:
                msg = f"Unexpected FFmpeg error:\n{e}\n\nPNG frames kept."
        else:
            msg = f"Successfully generated {total_frames} frames to:\n{folder}"

        self._set_status("Done!")
        gui.MessageDialog(msg)


# -----------------------------
# EXECUTION
# -----------------------------
if __name__ == "__main__":
    dlg = OpenPoseDialog()
    dlg.Open(dlgtype=c4d.DLG_TYPE_ASYNC,
             pluginid=DIALOG_ID,
             defaultw=480,
             defaulth=560)
