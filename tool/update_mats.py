import json
import os
import argparse

# Buffer Type and Access Maps for Lazurite 0.8.x
BUFFER_TYPE_MAP = {
    'texture2D': 0,
    'texture2DArray': 1,
    'external2D': 2,
    'texture3D': 3,
    'textureCube': 4,
    'textureCubeArray': 5,
    'structBuffer': 6,
    'rawBuffer': 7,
    'accelerationStructure': 8,
    'shadow2D': 9,
    'shadow2DArray': 10,
    # Compatibility with other tools
    'Type2D': 0,
    'Type2DArray': 1,
    'Type3D': 3,
    'TypeCube': 4
}

ACCESS_MAP = {
    'undefined': 0,
    'readonly': 1,
    'writeonly': 2,
    'readwrite': 3,
    # Compatibility
    'Read': 1,
    'Write': 2,
    'ReadWrite': 3
}

def update_materials(tool_mats_dir, user_json_dir):
    if not os.path.exists(user_json_dir):
        print(f"Error: Source JSON directory '{user_json_dir}' not found.")
        return

    for filename in os.listdir(tool_mats_dir):
        if not filename.endswith('.material.json'):
            continue
        
        mat_name = filename.replace('.material.json', '')
        user_json_path = os.path.join(user_json_dir, mat_name + '.json')
        
        base_path = os.path.join(tool_mats_dir, filename)
        with open(base_path, 'r') as f:
            base = json.load(f)
            
        # 1. Upgrade base to 0.8.x format if it's an old Newb format
        # [format_version, version, name, parent, flag_defs, input_defs, buffers, uniforms, overrides, passes]
        
        # Upgrade buffers in base
        new_base_buffers = []
        for b in base[6]:
            if len(b) < 12: # Old format detected
                # Pad to 12 elements: [name, reg1, reg2, type, precision, access, format, def_tex, unordered, always_one, path, sampler]
                new_b = [b[0], b[1], b[1], b[2], b[3], b[4], b[5], "white", 0, 1, "", -1]
                new_base_buffers.append(new_b)
            else:
                new_base_buffers.append(b)
        base[6] = new_base_buffers

        # Upgrade uniforms in base
        new_base_uniforms = []
        for u in base[7]:
            if len(u) < 4: # Old format
                # [name, type, count, default]
                new_base_uniforms.append([u[0], u[1], u[2], []])
            else:
                new_base_uniforms.append(u)
        base[7] = new_base_uniforms

        # 2. Merge New User Data
        if os.path.exists(user_json_path):
            print(f"Merging updated data for {mat_name}...")
            with open(user_json_path, 'r') as f:
                user = json.load(f)
            
            base[1] = user.get('version', base[1])
            base[3] = user.get('parentName', user.get('parent', base[3]))
            
            # Update uniforms from user
            new_uniforms = []
            for name, data in user.get('propertyFieldMap', {}).items():
                u_type = data.get('type', 2)
                if u_type == 1: u_type = 2 # Map Vector to vec4
                new_uniforms.append([name, u_type, data.get('num', 1), data.get('vectorData', data.get('matrixData', []))])
            base[7] = new_uniforms
            
            # Update buffers from user
            new_buffers = []
            for name, data in user.get('samplerDefinitionMap', {}).items():
                b_type_str = data.get('type', 'texture2D')
                b_type = BUFFER_TYPE_MAP.get(b_type_str, 0)
                access_str = data.get('access', 'readonly')
                access = ACCESS_MAP.get(access_str, 1)
                reg = data.get('reg', 0)
                new_buffers.append([name, reg, reg, b_type, data.get('precision', 0), access, data.get('textureFormat', ''), "white", 0, 1, "", -1])
            base[6] = new_buffers
            
            if 'uniform_overrides' in user:
                base[8] = user['uniform_overrides']
        
        # Save updated material
        with open(base_path, 'w') as f:
            json.dump(base, f, separators=(',', ':'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update Lazurite material.json files from unpacked JSON headers.')
    parser.add_argument('--src', required=True, help='Path to the directory containing unpacked .json files (e.g. from MaterialBinTool)')
    parser.add_argument('--target', default='tool/data/materials', help='Path to the tool/data/materials directory (default: tool/data/materials)')
    
    args = parser.parse_args()
    
    update_materials(args.target, args.src)
    print("Materials updated successfully!")
