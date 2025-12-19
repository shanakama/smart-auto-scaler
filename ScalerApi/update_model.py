#!/usr/bin/env python3

"""
Script to update ScalerApi with new DQN model
"""

import os
import shutil
import sys

def main():
    print("Updating ScalerApi with new multi-head DQN model...")
    
    # Paths
    current_dir = os.path.dirname(__file__)
    new_rl_dir = "/Users/shanakamadushanka/Desktop/MscProject/msc-research/new-rl"
    final_models_dir = os.path.join(current_dir, "final-models")
    
    # Create final-models directory if it doesn't exist
    os.makedirs(final_models_dir, exist_ok=True)
    
    # Step 1: Copy trained model if it exists
    model_files = ["best_model.pth", "final_model.pth"]
    model_copied = False
    
    for model_file in model_files:
        source_path = os.path.join(new_rl_dir, model_file)
        if os.path.exists(source_path):
            dest_path = os.path.join(final_models_dir, "best_model.pth")
            shutil.copy2(source_path, dest_path)
            print(f"✅ Copied {model_file} to {dest_path}")
            model_copied = True
            break
    
    # Look in training results directories
    if not model_copied:
        for item in os.listdir(new_rl_dir):
            if item.startswith("training_results_"):
                results_dir = os.path.join(new_rl_dir, item)
                for model_file in ["best_model.pth", "final_model.pth"]:
                    source_path = os.path.join(results_dir, model_file)
                    if os.path.exists(source_path):
                        dest_path = os.path.join(final_models_dir, "best_model.pth")
                        shutil.copy2(source_path, dest_path)
                        print(f"✅ Copied {model_file} from {results_dir} to {dest_path}")
                        model_copied = True
                        break
                if model_copied:
                    break
    
    if not model_copied:
        print("⚠️ No trained model found. You'll need to train a model first.")
        print("Run: python3 train_dqn_scaler.py --episodes 1000")
    
    # Step 2: Update imports in existing files
    files_to_update = {
        'app.py': 'from scaling_service_new import ScalingService',
        'api_routes.py': 'from dqn_model_wrapper_new import get_dqn_model'
    }
    
    for filename, new_import in files_to_update.items():
        filepath = os.path.join(current_dir, filename)
        if os.path.exists(filepath):
            # Read current content
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Update imports (simple replacement)
            if 'scaling_service' in filename:
                content = content.replace('from scaling_service import', 'from scaling_service_new import')
            elif 'dqn_model_wrapper' in content:
                content = content.replace('from dqn_model_wrapper import', 'from dqn_model_wrapper_new import')
            
            # Write back
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"✅ Updated {filename}")
    
    # Step 3: Create a backup and replace old files
    backup_files = {
        'dqn_model_wrapper.py': 'dqn_model_wrapper_old.py',
        'scaling_service.py': 'scaling_service_old.py'
    }
    
    for old_file, backup_name in backup_files.items():
        old_path = os.path.join(current_dir, old_file)
        backup_path = os.path.join(current_dir, backup_name)
        new_path = os.path.join(current_dir, old_file.replace('.py', '_new.py'))
        
        if os.path.exists(old_path):
            # Backup old file
            shutil.copy2(old_path, backup_path)
            print(f"✅ Backed up {old_file} to {backup_name}")
            
            # Replace with new version
            if os.path.exists(new_path):
                shutil.copy2(new_path, old_path)
                print(f"✅ Replaced {old_file} with new version")
    
    print("\n🎉 ScalerApi has been updated with the new multi-head DQN model!")
    print("\nNew features:")
    print("- ✅ Separate CPU and Memory scaling decisions")
    print("- ✅ Future resource usage predictions") 
    print("- ✅ Enhanced confidence scoring")
    print("- ✅ Detailed decision explanations")
    print("- ✅ Improved state representation with time features")
    
    print("\nTo test the integration:")
    print("1. Start the API: python3 app.py")
    print("2. Test endpoints:")
    print("   - GET /recommendations")
    print("   - POST /scale")
    print("   - GET /pod-history/<pod_name>")

if __name__ == "__main__":
    main()