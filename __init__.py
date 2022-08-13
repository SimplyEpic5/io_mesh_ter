bl_info = {
    "name": "Torque DTS format",
    "author": "port & bansheerubber & irrelevant.irreverent & Eagle517",
    "version": (0, 3, 6),
    "blender": (2, 81, 0),
    "location": "File > Import-Export",
    "description": "Import-Export DTS, Import DTS mesh, UV's, "
                   "materials and textures",
    "warning": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"}



bl_info = {
    "name": "Torque Terrain (TER) format",
    "author": "port",
    "version": (0, 0, 2),
    "blender": (2, 81, 0),
    "location": "File > Import-Export",
    "description": "Import Torque Terrain (TER) files",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import-Export"
}

if "bpy" in locals():
    import importlib
    if "import_ter" in locals():
        importlib.reload(import_ter)

import os

import bpy
from . import import_ter
from bpy.props import (
        StringProperty,
        BoolProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        )
from bpy.types import (
        Operator,
        )

class ImportTER(bpy.types.Operator, ImportHelper):
    """Load a Torque TER File"""
    bl_idname = "import_mesh.import_ter"
    bl_label = "Import Torque Terrain"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ".ter"

    filter_glob: StringProperty(
        default="*.ter",
        options={'HIDDEN'},
    )
    
    prompt_tex_path: BoolProperty(
        name="Select Texture Path",
        description="Select a seperate texture path?",
        default=False,
    )

    def execute(self, context):
        # keywords = self.as_keywords(ignore=("filter_glob",
        #                                     "split_mode",
        #                                     ))
        ter_file = self.filepath
            
        if self.prompt_tex_path:
            bpy.ops.import_mesh.choose_ter_tex('INVOKE_DEFAULT', ter_file=ter_file)
        else:
            bpy.ops.import_mesh.load_ter('EXEC_DEFAULT', ter_file=ter_file, tex_path=None)

        return {'FINISHED'}

# Select a texture directory
class TexFileChooser(Operator):
    bl_idname = "import_mesh.choose_ter_tex"
    bl_label = "Set Texture Path"

    directory: bpy.props.StringProperty(
        name="Texture Path",
        description="Texture Path"
    )
    
    ter_file: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        ter_file = self.ter_file
        tex_path = self.directory
        bpy.ops.import_mesh.load_ter('EXEC_DEFAULT', ter_file=ter_file, tex_path=self.directory)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class LoadTER(Operator):
    """Load a Torque TER File"""
    bl_idname = "import_mesh.load_ter"
    bl_label = "Load Torque Terrain From File"
    bl_options = {"PRESET", "UNDO"}

    ter_file: bpy.props.StringProperty(options={'HIDDEN'})
    tex_path: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        # keywords = self.as_keywords(ignore=("filter_glob",
        #                                     "split_mode",
        #                                     ))
        
        ter_file = self.ter_file
        tex_path = self.tex_path
        
        if ter_file is None or ter_file == "":
            return {'CANCELLED'}
        
        return import_ter.load(context, ter_file, tex_path)

def menu_import(self, context):
    self.layout.operator(ImportTER.bl_idname, text="Torque Terrain (.ter)")

def register():
    bpy.utils.register_class(ImportTER)
    bpy.utils.register_class(TexFileChooser)
    bpy.utils.register_class(LoadTER)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)

def unregister():
    bpy.utils.unregister_class(ImportTER)
    bpy.utils.unregister_class(TexFileChooser)
    bpy.utils.unregister_class(LoadTER)
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    

if __name__ == "__main__":
    register()
