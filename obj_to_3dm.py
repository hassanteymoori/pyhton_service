import os.path

from flask import Flask, request, jsonify
import trimesh
import rhino3dm
import numpy as np

app = Flask(__name__)


def clean_obj_file(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        lines = infile.readlines()
        current_material = None
        custom_material_counter = 1

        for line in lines:
            if line.startswith('usemtl'):
                current_material = line.strip()
            elif line.startswith('f'):
                if (current_material):
                    outfile.write(current_material + '\n')
                else:
                    custom_material = f'usemtl M_{custom_material_counter}\n'
                    outfile.write(custom_material)
                    current_material = custom_material.strip()
                    custom_material_counter += 1
                outfile.write(line)
            else:
                outfile.write(line)


def convert_obj_to_3dm(obj_path, output_3dm_path):
    print(output_3dm_path)
    # Load the OBJ file using trimesh
    scene = trimesh.load(obj_path, group_material=False, skip_materials=False, maintain_order=True)

    # Create a new 3dm file
    model = rhino3dm.File3dm()

    # Check if the loaded object is a scene with multiple geometries
    if isinstance(scene, trimesh.Scene):
        meshes = scene.dump()
    else:
        meshes = [scene]

    # Define a 90-degree rotation matrix around the X-axis
    rotation_matrix = np.array([
        [1, 0, 0],
        [0, 0, -1],
        [0, 1, 0]
    ])

    for mesh in meshes:
        vertices = mesh.vertices
        faces = mesh.faces

        rhino_mesh = rhino3dm.Mesh()

        for vertex in vertices:
            rotated_vertex = np.dot(rotation_matrix, vertex)
            rhino_mesh.Vertices.Add(rotated_vertex[0], rotated_vertex[1], rotated_vertex[2])
            # rhino_mesh.Vertices.Add(vertex[0], vertex[2], vertex[1])  # Swap Y and Z axes
            # rhino_mesh.Vertices.Add(vertex[0], vertex[1], vertex[2]) # X, Y, Z

        for face in faces:
            if len(face) == 3:  # Triangular face
                rhino_mesh.Faces.AddFace(face[0], face[1], face[2])
            elif len(face) == 4:  # Quad face
                rhino_mesh.Faces.AddFace(face[0], face[1], face[2], face[3])

        model.Objects.AddMesh(rhino_mesh)

    # Save the 3dm file
    model.Write(output_3dm_path)
    return output_3dm_path


@app.route('/convert', methods=['POST'])
def handle_convert():
    data = request.json

    input_obj = data['inputObj']
    clean_obj = data['cleanObj']
    output_3dm = data['output3dm']

    clean_obj_file(input_obj, clean_obj)
    result = convert_obj_to_3dm(clean_obj, output_3dm)

    if os.path.exists(output_3dm):
        return jsonify({"status": 1, "output_file": result})

    return jsonify({"status": 0, "output_file": ''})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
