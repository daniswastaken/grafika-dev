import os
import shutil
import subprocess

platforms = ['android', 'windows', 'merged', 'ios']
build_dir = 'build'

if os.path.exists(build_dir):
    shutil.rmtree(build_dir)
os.makedirs(build_dir)

def run_build(p, lite=False):
    config = "lite" if lite else "full"
    print(f"Building {p} ({config})...")
    
    cmd = ["python", "tool", "mats", "-p", p]
    if lite:
        cmd.append("--lite")
        
    subprocess.run(cmd, check=True)
    
    # Move result to specific folder
    src = os.path.join(build_dir, p)
    dst = os.path.join(build_dir, f"{p}_{config}")
    
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.rename(src, dst)
    print(f"  Saved to {dst}")

for p in platforms:
    run_build(p, lite=False)
    run_build(p, lite=True)

print("Batch compilation complete!")
