import os
import shutil

src_materials = 'src/materials'
common_material_path = 'src/common/material.json'
common_uniforms_dir = 'src/common/uniforms'

with open(common_material_path, 'r') as f:
    common_material_content = f.read()

for material_name in os.listdir(src_materials):
    material_dir = os.path.join(src_materials, material_name)
    if not os.path.isdir(material_dir):
        continue
    
    # Fix material.json
    mat_json_path = os.path.join(material_dir, 'material.json')
    if os.path.isfile(mat_json_path):
        with open(mat_json_path, 'r') as f:
            content = f.read().strip()
        if content == '../../common/material.json':
            print(f"Fixing material.json in {material_name}")
            with open(mat_json_path, 'w') as f:
                f.write(common_material_content)
    
    # Fix uniforms
    uniforms_path = os.path.join(material_dir, 'uniforms')
    if os.path.isfile(uniforms_path):
        with open(uniforms_path, 'r') as f:
            content = f.read().strip()
        if content == '../../common/uniforms/':
            print(f"Fixing uniforms in {material_name}")
            os.remove(uniforms_path)
            os.makedirs(uniforms_path)
            for filename in os.listdir(common_uniforms_dir):
                shutil.copy2(os.path.join(common_uniforms_dir, filename), os.path.join(uniforms_path, filename))
