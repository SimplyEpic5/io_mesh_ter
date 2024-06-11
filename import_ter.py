import os
from struct import unpack, calcsize

import bpy
from bpy_extras.io_utils import unpack_list

FileVersion = 3
MaterialGroups = 13
BlockSize = 256
BlockSize2 = BlockSize * BlockSize

def read(fd, fmt):
    return unpack(fmt, fd.read(calcsize(fmt)))

def read_str(fd):
     return fd.read(read(fd, "B")[0]).decode("cp1252")

def read_str_32(fd):
     return fd.read(read(fd, "I")[0]).decode("cp1252")

class TerrainFile:
      pass

def root_name(path):
     return os.path.basename(path).rsplit(".", 1)[0]

def read_ter(fd):
    version, = read(fd, "B")
    print(version)
    #assert version == FileVersion, "unsupported format version"

    ret = TerrainFile()

    ret.heightMap = read(fd, str(BlockSize2) + "H")
    ret.materialFlags = read(fd, str(BlockSize2) + "B")
    ret.materialNames = [read_str(fd) for k in range(MaterialGroups)]
    ret.materialAlpha = [None] * MaterialGroups

    for k in range(MaterialGroups):
        if ret.materialNames[k]:
            ret.materialAlpha[k] = read(fd, str(BlockSize2) + "B")

    ret.textureScript = read_str_32(fd)
    ret.heightfieldScript = read_str_32(fd)

    return ret

texture_extensions = ("png", "jpg")

def resolve_texture(filepath, name):
    dirname = os.path.dirname(filepath)

    while True:
        texbase = os.path.join(dirname, name)

        for extension in texture_extensions:
            texname = texbase + "." + extension

            if os.path.isfile(texname):
                return texname

        if os.path.ismount(dirname):
            break

        prevdir, dirname = dirname, os.path.dirname(dirname)

        if prevdir == dirname:
            break

def load(context, filepath, tex_path):
    with open(filepath, "rb") as fd:
        ter = read_ter(fd)

    name = root_name(filepath)
    me = bpy.data.meshes.new(name)

    # Create a new material
    mat = bpy.data.materials.new("TerrainMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear all nodes
    while nodes: nodes.remove(nodes[0])

    # Create output node
    output = nodes.new('ShaderNodeOutputMaterial')

    # Create Principled BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # Load all textures and create mix nodes
    prev_tex_node = None
    for i, orig_path in enumerate(ter.materialNames):
        if not orig_path:
            continue

        texture_path = tex_path or filepath
        mat_name = root_name(orig_path)
        mat_file = resolve_texture(texture_path, mat_name)

        if mat_file:
            try:
                image = bpy.data.images.load(mat_file)
            except:
                print("Cannot load image", mat_file)
                continue

            # Create texture node
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = image

            # Create attribute node for alpha
            attr_node = nodes.new('ShaderNodeAttribute')
            attr_node.attribute_name = f'tex{i}_vertexalphas'

            # Create mix node
            mix_node = nodes.new('ShaderNodeMixRGB')
            mix_node.blend_type = 'ADD'
            mix_node.inputs[1].default_value = (0, 0, 0, 1)  # Set base color to black
            links.new(attr_node.outputs['Color'], mix_node.inputs['Fac'])
            links.new(tex_node.outputs['Color'], mix_node.inputs[2])

            if prev_tex_node is not None:
                links.new(prev_tex_node.outputs['Color'], mix_node.inputs[1])

            prev_tex_node = mix_node

    # Connect last mix node to BSDF
    if prev_tex_node is not None:
        links.new(prev_tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    # Append material to mesh
    me.materials.append(mat)

    verts = []

    for x in range(BlockSize + 1):
        for y in range(BlockSize + 1):
            i = (y % BlockSize) * BlockSize + (x % BlockSize)

            verts.append((
                x * 8 - 1024,
                y * 8 - 1024,
                ter.heightMap[i] / 32
            ))

    faces = []
    face_blocks = []

    for x in range(BlockSize):
        for y in range(BlockSize):
            vert0 = y * 257 + x
            vert1 = y * 257 + x + 1
            vert2 = y * 257 + x + 257
            vert3 = y * 257 + x + 258

            if x % 2 == y % 2:
                faces.append((vert0, vert2, vert3))
                face_blocks.append((x, y))
                faces.append((vert3, vert1, vert0))
                face_blocks.append((x, y))
            else:
                faces.append((vert0, vert2, vert1))
                face_blocks.append((x, y))
                faces.append((vert3, vert1, vert2))
                face_blocks.append((x, y))

    # Create the mesh
    me.from_pydata(verts, [], faces)
    
    # Create a new UV map if it doesn't exist
    # The UV map can be default because it only affects the scale of the terrain textures, not the alphas of the textures
    if not me.uv_layers:
        me.uv_layers.new()
    
    uv_layer = me.uv_layers.active.data
    for poly in me.polygons:
        for i, loop_index in enumerate(poly.loop_indices):
            loop = me.loops[loop_index]
            vertex = me.vertices[loop.vertex_index]
            uv_layer[loop.index].uv = (vertex.co.x/32, vertex.co.y/32) # I'm guessing at the 1/32 scale for the uv. Seems right to me, but may not be 100% correct.
        
    # Set the texture alphas as vertex data
    for tex_i in range(MaterialGroups):
        if ter.materialAlpha[tex_i]:
            # Create a new attribute for the vertices
            vertex_attribute = me.attributes.get(f"tex{tex_i}_vertexalphas") or me.attributes.new(name=f"tex{tex_i}_vertexalphas", type="FLOAT", domain="POINT")
            
            # Initialize a list to hold the sum of the face attributes for each vertex
            vertex_sums = [0] * len(me.vertices)
            vertex_counts = [0] * len(me.vertices)
            
            # For each face, get the texture alpha and set the face's attribute value and materials
            for i in range(len(me.polygons)):
                grid_idx = face_blocks[i][0] * BlockSize + face_blocks[i][1]
                alpha = ter.materialAlpha[tex_i][grid_idx] / 255 # All the alphas of a given face combined add to 255. Normalizing them to 1
                me.polygons[i].material_index = len(me.materials) - 1
                
                # Add value to vertex counts/sums
                for vert_idx in me.polygons[i].vertices:
                    vertex_sums[vert_idx] += alpha
                    vertex_counts[vert_idx] += 1
                
            # For each vertex, calculate the average of the face attributes
            for i in range(len(me.vertices)):
                avg_alpha = vertex_sums[i] / vertex_counts[i]
                vertex_attribute.data[i].value = avg_alpha

    me.validate()
    me.update()

    ob = bpy.data.objects.new(name, me)
    context.collection.objects.link(ob)

    return {"FINISHED"}
