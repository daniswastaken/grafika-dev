import json
import os
import struct

tool_mats_dir = 'tool/data/materials'
user_json_dir = r'C:\Users\daniswastaken\Documents\matsJSON\jsonT'

BUFFER_TYPE_MAP = {'Type2D': 0, 'Type2DArray': 1, 'Type3D': 3, 'TypeCube': 4}
ACCESS_MAP = {'Read': 1, 'Write': 2, 'ReadWrite': 3}

def import_all():
    if not os.path.exists(user_json_dir):
        print(f"Error: Directory {user_json_dir} not found.")
        return

    count_merged = 0
    count_new = 0

    for filename in os.listdir(user_json_dir):
        if not filename.endswith('.json'):
            continue
            
        mat_name = filename[:-5]
        user_json_path = os.path.join(user_json_dir, filename)
        
        with open(user_json_path, 'r') as f:
            user = json.load(f)
            
        base_path = os.path.join(tool_mats_dir, mat_name + '.material.json')
        
        # Parse Uniforms (with matrix byte-to-float fix)
        new_uniforms = []
        for name, data in user.get('propertyFieldMap', {}).items():
            u_type = data.get('type', 2)
            if u_type == 1: u_type = 2
            
            if 'matrixData' in data:
                raw_data = data['matrixData']
                if all(isinstance(x, int) for x in raw_data) and len(raw_data) % 4 == 0:
                    byte_array = bytes([(b + 256) % 256 for b in raw_data])
                    num_floats = len(byte_array) // 4
                    u_data = list(struct.unpack("<" + "f" * num_floats, byte_array))
                else:
                    u_data = raw_data
            else:
                u_data = data.get('vectorData', [])
            new_uniforms.append([name, u_type, data.get('num', 1), u_data])
            
        # Parse Buffers
        new_buffers = []
        for name, data in user.get('samplerDefinitionMap', {}).items():
            b_type = BUFFER_TYPE_MAP.get(data.get('type', 'Type2D'), 0)
            access = ACCESS_MAP.get(data.get('access', 'Read'), 1)
            reg = data.get('reg', 0)
            new_buffers.append([name, reg, reg, b_type, data.get('precision', 0), access, data.get('textureFormat', ''), "white", 0, 1, "", -1])
            
        version = user.get('version', 25)
        parent = user.get('parentName', user.get('parent', ""))
        overrides = user.get('uniform_overrides', {})

        if os.path.exists(base_path):
            # Merge with existing base
            with open(base_path, 'r') as f:
                base = json.load(f)
                
            base[1] = version
            base[3] = parent
            base[6] = new_buffers
            base[7] = new_uniforms
            base[8] = overrides
            
            with open(base_path, 'w') as f:
                json.dump(base, f, separators=(',', ':'))
            count_merged += 1
            print(f"Merged existing: {mat_name}")
        else:
            # Create new minimal 0.8.3 format material (no passes)
            # [format_version, version, name, parent, flag_defs, input_defs, buffers, uniforms, overrides, passes]
            base = [1, version, mat_name, parent, {}, [], new_buffers, new_uniforms, overrides, []]
            
            with open(base_path, 'w') as f:
                json.dump(base, f, separators=(',', ':'))
            count_new += 1
            print(f"Imported new: {mat_name}")

    print(f"\nDone! Merged {count_merged} existing materials, imported {count_new} new materials.")

if __name__ == "__main__":
    import_all()
