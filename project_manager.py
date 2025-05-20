import os
import json
import shutil
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ProjectManager:
    def __init__(self, base_dir: str = "projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.current_project = None
        self.project_config = {}
        
    def create_project(self, name: str, description: str = "") -> Dict:
        """Create a new project with the given name and description."""
        project_dir = self.base_dir / name
        if project_dir.exists():
            raise ValueError(f"Project '{name}' already exists")
            
        project_dir.mkdir(parents=True)
        
        config = {
            "name": name,
            "description": description,
            "created_at": str(datetime.datetime.now()),
            "files": [],
            "settings": {
                "ai_model": "default",
                "version_control": True,
                "auto_save": True
            }
        }
        
        with open(project_dir / "project.json", "w") as f:
            json.dump(config, f, indent=2)
            
        self.project_config = config
        self.current_project = name
        return config
        
    def open_project(self, name: str) -> Dict:
        """Open an existing project."""
        project_dir = self.base_dir / name
        if not project_dir.exists():
            raise ValueError(f"Project '{name}' does not exist")
            
        with open(project_dir / "project.json", "r") as f:
            config = json.load(f)
            
        self.project_config = config
        self.current_project = name
        return config
        
    def list_projects(self) -> List[Dict]:
        """List all available projects."""
        projects = []
        for project_dir in self.base_dir.iterdir():
            if project_dir.is_dir():
                config_path = project_dir / "project.json"
                if config_path.exists():
                    with open(config_path, "r") as f:
                        projects.append(json.load(f))
        return projects
        
    def add_file(self, file_path: str, content: str = "") -> Dict:
        """Add a new file to the current project."""
        if not self.current_project:
            raise ValueError("No project is currently open")
            
        project_dir = self.base_dir / self.current_project
        file_path = Path(file_path)
        
        # Create parent directories if they don't exist
        (project_dir / file_path.parent).mkdir(parents=True, exist_ok=True)
        
        # Write file content
        with open(project_dir / file_path, "w") as f:
            f.write(content)
            
        # Update project config
        file_info = {
            "path": str(file_path),
            "added_at": str(datetime.datetime.now()),
            "last_modified": str(datetime.datetime.now())
        }
        
        self.project_config["files"].append(file_info)
        self._save_project_config()
        
        return file_info
        
    def get_file_content(self, file_path: str) -> str:
        """Get the content of a file in the current project."""
        if not self.current_project:
            raise ValueError("No project is currently open")
            
        project_dir = self.base_dir / self.current_project
        file_path = Path(file_path)
        
        if not (project_dir / file_path).exists():
            raise ValueError(f"File '{file_path}' does not exist in project")
            
        with open(project_dir / file_path, "r") as f:
            return f.read()
            
    def update_file(self, file_path: str, content: str) -> Dict:
        """Update the content of a file in the current project."""
        if not self.current_project:
            raise ValueError("No project is currently open")
            
        project_dir = self.base_dir / self.current_project
        file_path = Path(file_path)
        
        if not (project_dir / file_path).exists():
            raise ValueError(f"File '{file_path}' does not exist in project")
            
        with open(project_dir / file_path, "w") as f:
            f.write(content)
            
        # Update file info in project config
        for file_info in self.project_config["files"]:
            if file_info["path"] == str(file_path):
                file_info["last_modified"] = str(datetime.datetime.now())
                break
                
        self._save_project_config()
        return file_info
        
    def _save_project_config(self):
        """Save the current project configuration."""
        if not self.current_project:
            return
            
        project_dir = self.base_dir / self.current_project
        with open(project_dir / "project.json", "w") as f:
            json.dump(self.project_config, f, indent=2) 