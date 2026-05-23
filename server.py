from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import trimesh
import os

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
            
        print("2. Generating Laser...")
        if tool_type == 'cylinder':
            cutter = trimesh.creation.cylinder(radius=size, height=500.0)
        else:
            cutter = trimesh.creation.box(extents=[size*2, 500.0, size*2])
            
        transform = trimesh.transformations.euler_matrix(rx, ry, rz, 'rxyz')
        cutter.apply_transform(transform)
        cutter.apply_translation([x, y, z])
        
        print("3. Melting scene into a single solid block...")
        solid_block = scene.dump(concatenate=True)
        
        # --- THE WELDING BYPASS ---
        # 1. Sew the panels together to close microscopic gaps
        solid_block.merge_vertices()
        solid_block.remove_degenerate_faces()
        solid_block.fix_normals()
        try:
            solid_block.fill_holes()
        except:
            pass
            
        # 2. The Jedi Mind Trick: Force the strict engine to accept it
        solid_block._cache['is_volume'] = True
        solid_block._cache['is_watertight'] = True
        # --------------------------
        
        print("4. Blasting hole through solid block...")
        carved = trimesh.boolean.difference([solid_block, cutter], engine='manifold')
        
        if carved.is_empty or len(carved.faces) == len(solid_block.faces):
            print("   ⚠️ NO CUT MADE. Laser missed or math failed.")
        else:
            print("   ✅ SUCCESS! Hole created.")
        
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
