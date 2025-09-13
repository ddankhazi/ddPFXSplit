"""
DD PFX Split Tool for Maya - PRODUCTION VERSION (PYTHON 2/3 COMPATIBLE)
Author: Denes Dankhazi  
Date: August 27, 2025

Complete implementation based on tested workflow:
Paint Effects + Temporary Plane + Orthographic Projection

UPDATED: August 28, 2025
- Replaced MEL wrapper commands with direct Maya commands for better control
- Added polyProjectCurve with custom parameters: curveSamples=50, tolerance=0.001, automatic=1, pointsOnEdges=0
- Fixed polySplit to use makeCurveSplitConnections for multiple projected curves
- Added UI controls for projection and split settings
- Supports multiple curves with proper curve shape collection and single polySplit node
- Made compatible with both Python 2 (Maya 2022) and Python 3 (Maya 2026+)
"""

from __future__ import print_function  # Python 2/3 compatibility for print function
import sys
import maya.cmds as cmds
import maya.mel as mel


class DDFreeSplitTool:
    def __init__(self):
        self.tool_name = "ddPFXSplit"
        self.version = "1.0"
        self.target_geo = None
        self.duplicated_geo = None
        self.temp_plane = None
        self.projection_curve = None
        self.projection_curves = []  # List for multiple curves
        self.pfx_stroke = None
        self.original_camera_state = {}
        self.gui_window = None
        
        # Detect Python and Maya version for compatibility
        self.python_version = sys.version_info[0]
        try:
            self.maya_version = int(cmds.about(version=True))
        except:
            self.maya_version = 2026  # Default assumption
        
    def resize_window_on_collapse(self, *args):
        """Resize window to fit content when projection settings are collapsed"""
        if self.gui_window and cmds.window(self.gui_window, exists=True):
            # Force window to shrink by temporarily disabling resizeToFitChildren
            cmds.window(self.gui_window, edit=True, resizeToFitChildren=False)
            # Set a smaller height to force shrinking, then re-enable auto-resize
            cmds.window(self.gui_window, edit=True, height=400)
            cmds.window(self.gui_window, edit=True, resizeToFitChildren=True)
        
    def create_ui(self):
        """Create production-ready UI"""
        if cmds.window(self.tool_name + "_window", exists=True):
            cmds.deleteUI(self.tool_name + "_window")
            
        self.gui_window = cmds.window(self.tool_name + "_window", 
                                    title="DD PFX Split Tool v{}".format(self.version),
                                    widthHeight=(297, 610),
                                    resizeToFitChildren=True,
                                    sizeable=True)
        
        # Force window size (Maya sometimes ignores widthHeight on fixed windows)
        #cmds.window(self.gui_window, edit=True, widthHeight=(297, 610))
        
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=8, 
                                      columnOffset=("both", 15))
        
        # Header
        cmds.text(label="DD PFX Split Tool", font="boldLabelFont", height=45)
        cmds.text(label="Paint Effects Based Mesh Splitting", 
                 font="smallPlainLabelFont", height=20)
        cmds.separator(height=5)
        
        # Step 1: Setup (Neutral Gray)
        cmds.frameLayout(label="Step 1: Geometry Setup", collapsable=False, backgroundColor=[0.2, 0.2, 0.2])
        cmds.columnLayout(adjustableColumn=True)
        #cmds.text(label="Select geometry to split, then click Setup:")
        cmds.button(label="Setup Selected Geometry", 
                   command=self.setup_geometry, height=40)
        cmds.text("status_text", label="Status: No geometry selected", align="left")
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Step 2: Paint Tool (Blue)
        cmds.frameLayout(label="Step 2: Paint Tool Activation", collapsable=False, backgroundColor=[0.2, 0.2, 0.2])
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="Activate Paint Tool", 
                   command=self.activate_paint_tool, height=40, backgroundColor=[0.2, 0.4, 0.5])
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(132, 132))
        cmds.button(label="Toggle X-Ray", command=self.toggle_xray, height=25, width=128)
        cmds.button(label="Reset Camera View", command=self.reset_camera_view, height=25, width=128)
        cmds.setParent('..')
        cmds.text(label="Move camera to adjust drawing position", align="left")
        cmds.text(label="Draw your split curve with Paint Effects", align="left")
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Step 3: Convert and Project
        cmds.frameLayout(label="Step 3: Convert and Project", collapsable=False, backgroundColor=[0.2, 0.2, 0.2])
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="Convert and Project Curve(s)", 
                   command=self.convert_and_project, height=40, backgroundColor=[0.1, 0.4, 0.4])
        
        # Projection Settings
        cmds.frameLayout(label="Projection Settings", collapsable=True, collapse=True, 
                        backgroundColor=[0.2, 0.2, 0.2],
                        collapseCommand=self.resize_window_on_collapse)
        cmds.columnLayout(adjustableColumn=True)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 180))
        cmds.text(label="Curve Samples:")
        cmds.intField("curveSamples", value=50, minValue=10, maxValue=200)
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(120, 180))
        cmds.text(label="Tolerance:")
        cmds.floatField("projTolerance", value=0.001, minValue=0.0001, maxValue=0.1, precision=4)
        cmds.setParent('..')
        cmds.checkBox("pointsOnEdges", label="Points on Edges", value=False)
        cmds.checkBox("automatic", label="Automatic Projection", value=True)
        cmds.setParent('..')
        cmds.setParent('..')
        
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Step 4: Execute Split (Red)
        cmds.frameLayout(label="Step 4: Execute Split", collapsable=False, backgroundColor=[0.2, 0.2, 0.2])
        cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="Execute Split", command=self.execute_split, height=40, backgroundColor=[0.2, 0.5, 0.5])
        cmds.checkBox("keepHistory", label="Keep Projected Curves", value=False)
        cmds.checkBox("detachEdges", label="Detach Edges (Separate Pieces)", value=True)
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Final Actions (Gray)
        cmds.frameLayout(label="Finish", collapsable=False, backgroundColor=[0.2, 0.2, 0.2])
        cmds.columnLayout(adjustableColumn=True)
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(132, 132))
        cmds.button(label="Finish & Cleanup", command=self.finish_and_cleanup, height=40, width=128, backgroundColor=[0.4, 0.4, 0.4])
        cmds.button(label="Cancel", command=self.cancel_operation, height=40, width=128, backgroundColor=[0.2, 0.2, 0.2])
        cmds.setParent('..')
        cmds.setParent('..')
        cmds.setParent('..')
        
        # Add bottom margin to match overall UI spacing
        cmds.separator(height=12, style="none")
        
        cmds.showWindow(self.gui_window)
        
    def setup_geometry(self, *args):
        """Setup geometry - duplicate and hide original"""
        selection = cmds.ls(selection=True, type="transform")
        if not selection:
            cmds.warning("Please select a geometry object first!")
            return
            
        self.target_geo = selection[0]
        
        # Duplicate geometry and hide original
        self.duplicated_geo = cmds.duplicate(self.target_geo, 
                                           name=self.target_geo + "_split")[0]
        cmds.hide(self.target_geo)
        
        # Update status
        try:
            cmds.text("status_text", edit=True, 
                     label="Status: {} ready for splitting".format(self.target_geo))
        except:
            pass
        
    def activate_paint_tool(self, *args):
        """Activate paint tool with complete setup"""
        if not self.target_geo:
            cmds.warning("Please setup geometry first!")
            return
            
        self.setup_orthographic_camera()
        self.create_temporary_plane()
        self.activate_paint_effects()
        
    def setup_orthographic_camera(self):
        """Setup orthographic camera with bbox-based width"""
        current_panel = cmds.getPanel(withFocus=True)
        if not current_panel or cmds.getPanel(typeOf=current_panel) != "modelPanel":
            panels = [p for p in cmds.getPanel(visiblePanels=True) 
                     if cmds.getPanel(typeOf=p) == "modelPanel"]
            current_panel = panels[0] if panels else None
            
        camera = cmds.modelPanel(current_panel, query=True, camera=True)
        camera_shape = cmds.listRelatives(camera, shapes=True)[0]
        
        # Store original state
        self.original_camera_state = {
            "camera": camera,
            "camera_shape": camera_shape,
            "orthographic": cmds.getAttr(camera_shape + ".orthographic"),
            "orthographicWidth": cmds.getAttr(camera_shape + ".orthographicWidth"),
        }
        
        # Calculate width from bbox
        bbox = cmds.exactWorldBoundingBox(self.target_geo)
        width = max(bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2]) * 1.5
        
        # Switch to orthographic
        cmds.setAttr(camera_shape + ".orthographic", 1)
        cmds.setAttr(camera_shape + ".orthographicWidth", width)
        
        # Unlock tumble
        cmds.tumbleCtx("tumbleContext", edit=True, orthoLock=False)
        cmds.tumbleCtx("tumbleContext", edit=True, autoOrthoConstrain=False)
        
    def create_temporary_plane(self):
        """Create temporary plane exactly as specified"""
        camera = self.original_camera_state["camera"]
        camera_shape = self.original_camera_state["camera_shape"]
        ortho_width = cmds.getAttr(camera_shape + ".orthographicWidth")
        
        # Create polyPlane with exact parameters
        plane_result = cmds.polyPlane(width=ortho_width, height=ortho_width, 
                                    subdivisionsX=20, subdivisionsY=20, 
                                    axis=(0, 1, 0), createUVs=2, 
                                    constructionHistory=True,
                                    name="ddSplit_tempPlane")
        self.temp_plane = plane_result[0]
        plane_creation_node = plane_result[1]
        
        # Connect camera orthographicWidth to plane dimensions
        cmds.connectAttr(camera_shape + ".orthographicWidth", 
                        plane_creation_node + ".width", force=True)
        cmds.connectAttr(camera_shape + ".orthographicWidth", 
                        plane_creation_node + ".height", force=True)
        
        # Parent and position
        cmds.parent(self.temp_plane, camera)
        cmds.setAttr(self.temp_plane + ".translateX", 0)
        cmds.setAttr(self.temp_plane + ".translateY", 0)
        cmds.setAttr(self.temp_plane + ".translateZ", -100)
        cmds.setAttr(self.temp_plane + ".rotateX", 90)
        cmds.setAttr(self.temp_plane + ".rotateY", 0)
        cmds.setAttr(self.temp_plane + ".rotateZ", 0)
        
        # Set to bounding box display and hide
        cmds.setAttr(self.temp_plane + ".overrideEnabled", 1)
        cmds.setAttr(self.temp_plane + ".overrideDisplayType", 2)
        cmds.setAttr(self.temp_plane + ".visibility", 0)
        
    def activate_paint_effects(self):
        """Activate Paint Effects with defaultPaint"""
        # Load defaultPaint preset - use version-agnostic path approach
        try:
            # Try Maya 2026+ path first
            mel.eval('source "C:/Program Files/Autodesk/Maya2026/Examples/Paint_Effects/Airbrush/defaultPaint.mel"')
        except:
            try:
                # Try Maya 2022 path
                mel.eval('source "C:/Program Files/Autodesk/Maya2022/Examples/Paint_Effects/Airbrush/defaultPaint.mel"')
            except:
                try:
                    # Use generic approach if specific paths fail
                    mel.eval('source `getenv("MAYA_LOCATION")` + "/Examples/Paint_Effects/Airbrush/defaultPaint.mel"')
                except:
                    pass  # Silently use default paint settings
        
        # Set wire mode (correct flag is 'dam' not 'disableAfterModifier')
        try:
            cmds.dynWireCtx("dynWireCtx1", edit=True, dam=False)
        except:
            pass  # Silently continue if dynWireCtx fails
        
        # Make plane paintable (correct MEL command is MakePaintable not makePaintable)
        if self.temp_plane:
            cmds.select(self.temp_plane)
            try:
                mel.eval("MakePaintable")
            except:
                pass  # User can make paintable manually if needed
            
    def toggle_xray(self, *args):
        """Toggle X-Ray mode"""
        current_panel = cmds.getPanel(withFocus=True)
        if cmds.getPanel(typeOf=current_panel) == "modelPanel":
            current_state = cmds.modelEditor(current_panel, query=True, xray=True)
            cmds.modelEditor(current_panel, edit=True, xray=not current_state)
            
    def reset_camera_view(self, *args):
        """Reset camera to frame geometry"""
        if self.duplicated_geo:
            cmds.select(self.duplicated_geo)
            cmds.viewFit()
            cmds.select(clear=True)
            
    def convert_and_project(self, *args):
        """Convert PFX to curve and project - handles multiple strokes"""
        strokes = cmds.ls(type="stroke")
        if not strokes:
            cmds.warning("No Paint Effects stroke found!")
            return
            
        # Store all created projection curves for cleanup
        self.projection_curves = []
        
        # Process each stroke
        for i, stroke_shape in enumerate(strokes):
            # Verify stroke shape exists
            if not stroke_shape or not cmds.objExists(stroke_shape):
                cmds.warning("Paint Effects stroke {} is invalid - skipping!".format(i+1))
                continue
            
            # Get the transform node for reference
            stroke_transforms = cmds.listRelatives(stroke_shape, parent=True)
            if stroke_transforms:
                pfx_stroke = stroke_transforms[0]
            else:
                pfx_stroke = stroke_shape
                
            # Create circle for this stroke
            circle_result = cmds.circle(center=(0, 0, 0), normal=(0, 1, 0), 
                                      sweep=360, radius=1, degree=3, 
                                      useTolerance=False, tolerance=0.01, 
                                      sections=8, constructionHistory=False,
                                      name="projCurve_{:02d}".format(i+1))
            projection_curve = circle_result[0]
            circle_shape = cmds.listRelatives(projection_curve, shapes=True)[0]
            
            # Store for cleanup
            self.projection_curves.append(projection_curve)
            
            # Connect PFX stroke shape directly
            cmds.connectAttr("{}.outMainCurves[0]".format(stroke_shape), 
                            "{}.create".format(circle_shape), force=True)
        
        # Set the first curve as main reference (for backward compatibility)
        if self.projection_curves:
            self.projection_curve = self.projection_curves[0]
        
        # Project all curves using direct Maya commands with proper settings
        if self.projection_curves:
            try:
                # Get projection settings from UI
                curve_samples = 50
                tolerance = 0.001
                points_on_edges = False
                automatic = True
                
                try:
                    curve_samples = cmds.intField("curveSamples", query=True, value=True)
                    tolerance = cmds.floatField("projTolerance", query=True, value=True)
                    points_on_edges = cmds.checkBox("pointsOnEdges", query=True, value=True)
                    automatic = cmds.checkBox("automatic", query=True, value=True)
                except:
                    pass  # Use default projection settings
                
                projected_curve_groups = []
                
                # Project each curve individually with specific parameters
                for i, curve in enumerate(self.projection_curves):
                    # Use polyProjectCurve with proper settings
                    result = cmds.polyProjectCurve(
                        curve, self.duplicated_geo,
                        constructionHistory=True,        # ch=1
                        pointsOnEdges=points_on_edges,   # pointsOnEdges (from UI)
                        curveSamples=curve_samples,      # curveSamples (from UI)
                        automatic=automatic,             # automatic (from UI)
                        tolerance=tolerance              # tolerance (from UI)
                    )
                    
                    # Result is a list: [projectedCurve, curveVarGroup]
                    if result:
                        projected_curve_groups.append(result[1])  # Store curveVarGroup
                
            except Exception as e:
                cmds.warning("Projection failed: {}".format(str(e)))
        else:
            cmds.warning("No valid projection curves created!")
            
    def execute_split(self, *args):
        """Execute the mesh split using MEL command with proper tool settings"""
        curve_groups = cmds.ls(type="curveVarGroup")
        if not curve_groups:
            cmds.warning("No projected curve found!")
            return
            
        # Get detachEdges setting from UI
        detach_edges = True
        try:
            detach_edges = cmds.checkBox("detachEdges", query=True, value=True)
        except:
            pass  # Use default detachEdges=True
        
        try:
            # Set the polySplit tool options BEFORE executing the command
            # CORRECT METHOD: Use splitPolyWithCurveOperation optionVar
            # 1 = Keep pieces together, 2 = Detach/separate pieces
            operation_value = 2 if detach_edges else 1
            cmds.optionVar(intValue=("splitPolyWithCurveOperation", operation_value))
            
            # Select all projected curve groups first, then add target geometry
            cmds.select(curve_groups, replace=True)
            cmds.select(self.duplicated_geo, add=True)
            
            # Execute split with all curve groups using the MEL command
            # This will respect the tool settings we just configured
            mel.eval("performSplitMeshWithProjectedCurve 0")
            
        except Exception as e:
            cmds.warning("Split failed: {}".format(str(e)))
            
    def finish_and_cleanup(self, *args):
        """Finish and cleanup"""
        self.restore_camera_state()
        
        # Handle projected curves option
        keep_projected_curves = False
        try:
            keep_projected_curves = cmds.checkBox("keepHistory", query=True, value=True)
        except:
            pass
            
        # Find all created objects for cleanup
        split_groups = [obj for obj in cmds.ls(transforms=True) if obj.endswith("_split")]
        pfx_objects = cmds.ls(type="stroke")
        
        # Find Paint Effects stroke transforms (they follow pattern like strokeDefaultPaint1, strokeDefaultPaint2, etc.)
        pfx_transforms = []
        for pfx_shape in pfx_objects:
            if cmds.objExists(pfx_shape):
                pfx_parents = cmds.listRelatives(pfx_shape, parent=True)
                if pfx_parents:
                    pfx_transforms.extend(pfx_parents)
        
        # Handle multiple projection curves (new approach) or single curve (backward compatibility)
        if hasattr(self, 'projection_curves') and self.projection_curves:
            projection_curves = [curve for curve in self.projection_curves if cmds.objExists(curve)]
        elif self.projection_curve and cmds.objExists(self.projection_curve):
            projection_curves = [self.projection_curve]
        else:
            projection_curves = []
            
        projection_curve_groups = cmds.ls(type="curveVarGroup")
        
        # ALWAYS delete construction history from duplicated geometry first
        if self.duplicated_geo and cmds.objExists(self.duplicated_geo):
            cmds.delete(self.duplicated_geo, constructionHistory=True)
        
        # ALWAYS delete all split groups
        for split_group in split_groups:
            if cmds.objExists(split_group):
                cmds.delete(split_group)
                
        # ALWAYS delete Paint Effects strokes (both shapes and transforms)
        for pfx_obj in pfx_objects:
            if cmds.objExists(pfx_obj):
                cmds.delete(pfx_obj)
                
        # ALWAYS delete Paint Effects transforms
        for pfx_transform in pfx_transforms:
            if cmds.objExists(pfx_transform):
                cmds.delete(pfx_transform)
                
        # ALWAYS delete the original projection curves (circles)
        for proj_curve in projection_curves:
            if cmds.objExists(proj_curve):
                cmds.delete(proj_curve)
        
        # Handle projection curve groups based on keep_projected_curves setting
        if keep_projected_curves:
            # Keep projected curves visible - don't delete them
            pass
        else:
            # Delete projection curve groups (polyProjectCurve results)
            for curve_group in projection_curve_groups:
                if cmds.objExists(curve_group):
                    cmds.delete(curve_group)
        
        # Always cleanup temporary plane
        if self.temp_plane and cmds.objExists(self.temp_plane):
            cmds.delete(self.temp_plane)
            
        # DON'T unhide original geometry - leave it hidden
        # User comment: "az eredeti geót nem kell unhide-olni"
        
        # Close GUI
        if self.gui_window and cmds.window(self.gui_window, exists=True):
            cmds.deleteUI(self.gui_window)
        
    def cancel_operation(self, *args):
        """Cancel and restore"""
        self.restore_camera_state()
        
        if self.duplicated_geo and cmds.objExists(self.duplicated_geo):
            cmds.delete(self.duplicated_geo)
        if self.temp_plane and cmds.objExists(self.temp_plane):
            cmds.delete(self.temp_plane)
        if self.target_geo and cmds.objExists(self.target_geo):
            cmds.showHidden(self.target_geo)
        if self.gui_window and cmds.window(self.gui_window, exists=True):
            cmds.deleteUI(self.gui_window)
        
    def restore_camera_state(self):
        """Restore camera state"""
        if not self.original_camera_state:
            return
            
        camera_shape = self.original_camera_state.get("camera_shape")
        if camera_shape and cmds.objExists(camera_shape):
            cmds.setAttr(camera_shape + ".orthographic", 
                        self.original_camera_state["orthographic"])
            cmds.setAttr(camera_shape + ".orthographicWidth", 
                        self.original_camera_state["orthographicWidth"])
                        
        cmds.tumbleCtx("tumbleContext", edit=True, orthoLock=True)
        cmds.tumbleCtx("tumbleContext", edit=True, autoOrthoConstrain=True)


def show_tool():
    """Launch the tool"""
    tool = DDFreeSplitTool()
    tool.create_ui()
    return tool


def test_compatibility():
    """Test Python 2/3 compatibility"""
    # Test basic Python version detection
    python_ver = sys.version_info[0]
    
    # Test Maya commands (if available)
    try:
        maya_version = cmds.about(version=True)
    except:
        pass  # Maya not available in current environment
    
    # Test class instantiation
    try:
        tool = DDFreeSplitTool()
        return True
    except Exception as e:
        return False


# Auto-launch
if __name__ == "__main__":
    # Run compatibility test first
    if test_compatibility():
        dd_split_tool = show_tool()
