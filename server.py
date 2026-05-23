from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import trimesh
import os
import numpy as np

app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app) 

# Forces Python to serve the HTML file
@app.route('/')
def serve_website():
    return send_file('index.html')

# Forces Python to serve your 3D models properly
@app.route('/models/<path:filename>')
def serve_models(filename):
    return send_file(os.path.join('models', filename))

@app.route('/carve', methods=['POST'])
def carve_shoe():
    data = request.json
    print("\n--- ✂️ INITIATING SOLID BLOCK CUT (CHOICE 2) ---")    
    category = data.get('category', 'upper')
    tool_type = data.get('tool')
    size = float(data.get('size'))
    
    x, y, z = float(data.get('x')), float(data.get('y')), float(data.get('z'))
    rx, ry, rz = float(data.get('rx')), float(data.get('ry')), float(data.get('rz'))
    
    original_file = f"models/{category}.gltf"
    if category == 'sole' and not os.path.exists(original_file):
        original_file = "models/sole 1.gltf"
        
    carved_file = f"models/carved_{category}.glb"
    
    if os.path.exists(carved_file):
        print(f"1. Loading previous cut from {carved_file}...")
        file_to_load = carved_file
    else:
        print(f"1. Loading original model from {original_file}...")
        file_to_load = original_file

    try:
        scene = trimesh.load(file_to_load, force='scene')
            
       print("2. Calculating exact Laser trajectory...")
        # Get the mathematical trajectory of the laser
        transform = trimesh.transformations.euler_matrix(rx, ry, rz, 'rxyz')
        transform[:3, 3] = [x, y, z]
        inv_transform = np.linalg.inv(transform)
        
        print("3. Melting scene into a single mesh...")
        solid_block = scene.dump(concatenate=True)
        
        print("4. Blasting hole using Pure Math (Non-Manifold Safe)...")
        # Move all shoe vertices into the "local coordinate space" of the laser to measure them
        local_verts = trimesh.transformations.transform_points(solid_block.vertices, inv_transform)
        
        # Find exactly which vertices are touching the laser beam
        if tool_type == 'cylinder':
            # Cylinder math: x^2 + y^2 <= radius^2
            r_sq = local_verts[:, 0]**2 + local_verts[:, 1]**2
            inside = (r_sq <= size**2) & (np.abs(local_verts[:, 2]) <= 250)
        else:
            # Cuboid math: bounding box check
            inside = (np.abs(local_verts[:, 0]) <= size) & \
                     (np.abs(local_verts[:, 1]) <= 250) & \
                     (np.abs(local_verts[:, 2]) <= size)
                     
        # Find which triangles (faces) of the shoe are inside the laser and delete them
        faces_inside = inside[solid_block.faces]
        hit_faces = faces_inside.any(axis=1) 
        keep_faces = ~hit_faces
        
        solid_block.update_faces(keep_faces)
        solid_block.remove_unreferenced_vertices()
        
        carved = solid_block
        print("   ✅ SUCCESS! Triangles instantly deleted.")
        
        print("5. Saving...")
        new_scene = trimesh.Scene()
        new_scene.add_geometry(carved, node_name=f'{category}_mesh')
        
        with open(carved_file, 'wb') as f:
            f.write(new_scene.export(file_type='glb'))
            
        return jsonify({"status": "success", "message": "Cut complete!"})
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/undo', methods=['POST'])
def undo_carve():
    category = request.json.get('category', 'upper')
    carved_file = f"models/carved_{category}.glb"
    print(f"\n--- ⏪ UNDO INITIATED FOR {category.upper()} ---")
    try:
        if os.path.exists(carved_file):
            os.remove(carved_file)
            print(f"✅ Deleted {carved_file}")
        return jsonify({"status": "success", "message": "Undo complete!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/reset-session', methods=['POST'])
def reset_session():
    print(f"\n--- 🧹 FULL SESSION RESET INITIATED ---")
    cats_to_reset = request.json.get('categories', ['upper', 'sole'])
    for cat in cats_to_reset:
        carved_file = f"models/carved_{cat}.glb"
        if os.path.exists(carved_file):
            try:
                os.remove(carved_file)
                print(f"✅ Reset: Deleted {carved_file}")
            except:
                pass
    return jsonify({"status": "success", "message": "Reset complete."})

if __name__ == '__main__':
    print("\n[SYS] ** Footlabs Studio API is ONLINE & READY! **\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
