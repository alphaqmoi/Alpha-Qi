import os
import subprocess
from typing import Dict, List, Optional, Generator
import logging
from pathlib import Path
import json
import tempfile
import shutil

logger = logging.getLogger(__name__)

class TerminalGitManager:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.current_dir = self.workspace_path
        
    def run_command(self, command: str, cwd: Optional[str] = None) -> Dict:
        """Run a terminal command and return the result."""
        try:
            if cwd:
                cwd = Path(cwd)
            else:
                cwd = self.current_dir
                
            process = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True
            )
            
            return {
                "success": process.returncode == 0,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "return_code": process.returncode
            }
        except Exception as e:
            logger.error(f"Error running command: {str(e)}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }
            
    def git_init(self) -> Dict:
        """Initialize a Git repository."""
        return self.run_command("git init")
        
    def git_add(self, files: List[str]) -> Dict:
        """Add files to Git staging area."""
        files_str = " ".join(files)
        return self.run_command(f"git add {files_str}")
        
    def git_commit(self, message: str) -> Dict:
        """Commit changes to Git repository."""
        return self.run_command(f'git commit -m "{message}"')
        
    def git_status(self) -> Dict:
        """Get Git repository status."""
        return self.run_command("git status")
        
    def git_diff(self, staged: bool = False) -> Dict:
        """Get Git diff of changes."""
        command = "git diff --staged" if staged else "git diff"
        return self.run_command(command)
        
    def git_branch(self, name: Optional[str] = None) -> Dict:
        """Create or switch to a Git branch."""
        if name:
            return self.run_command(f"git checkout -b {name}")
        else:
            return self.run_command("git branch")
            
    def git_merge(self, branch: str) -> Dict:
        """Merge a branch into the current branch."""
        return self.run_command(f"git merge {branch}")
        
    def git_pull(self, remote: str = "origin", branch: str = "main") -> Dict:
        """Pull changes from a remote repository."""
        return self.run_command(f"git pull {remote} {branch}")
        
    def git_push(self, remote: str = "origin", branch: str = "main") -> Dict:
        """Push changes to a remote repository."""
        return self.run_command(f"git push {remote} {branch}")
        
    def git_log(self, max_count: int = 10) -> Dict:
        """Get Git commit history."""
        return self.run_command(f"git log -n {max_count} --pretty=format:'%h|%an|%ae|%ad|%s'")
        
    def git_remote_add(self, name: str, url: str) -> Dict:
        """Add a remote repository."""
        return self.run_command(f"git remote add {name} {url}")
        
    def git_remote_remove(self, name: str) -> Dict:
        """Remove a remote repository."""
        return self.run_command(f"git remote remove {name}")
        
    def git_remote_list(self) -> Dict:
        """List remote repositories."""
        return self.run_command("git remote -v")
        
    def git_stash(self, message: Optional[str] = None) -> Dict:
        """Stash changes."""
        command = f'git stash save "{message}"' if message else "git stash"
        return self.run_command(command)
        
    def git_stash_pop(self) -> Dict:
        """Pop the most recent stash."""
        return self.run_command("git stash pop")
        
    def git_stash_list(self) -> Dict:
        """List all stashes."""
        return self.run_command("git stash list")
        
    def git_reset(self, commit: str, hard: bool = False) -> Dict:
        """Reset to a specific commit."""
        command = f"git reset {'--hard' if hard else '--soft'} {commit}"
        return self.run_command(command)
        
    def git_revert(self, commit: str) -> Dict:
        """Revert a specific commit."""
        return self.run_command(f"git revert {commit}")
        
    def git_clean(self, force: bool = False) -> Dict:
        """Clean untracked files."""
        command = "git clean -fd" if force else "git clean -n"
        return self.run_command(command)
        
    def git_config(self, key: str, value: str, global_: bool = False) -> Dict:
        """Set Git configuration."""
        scope = "--global" if global_ else "--local"
        return self.run_command(f"git config {scope} {key} {value}")
        
    def git_config_get(self, key: str, global_: bool = False) -> Dict:
        """Get Git configuration."""
        scope = "--global" if global_ else "--local"
        return self.run_command(f"git config {scope} {key}")
        
    def git_config_list(self, global_: bool = False) -> Dict:
        """List Git configuration."""
        scope = "--global" if global_ else "--local"
        return self.run_command(f"git config {scope} --list")
        
    def git_ignore(self, patterns: List[str]) -> Dict:
        """Add patterns to .gitignore."""
        gitignore_path = self.current_dir / ".gitignore"
        
        try:
            with open(gitignore_path, "a") as f:
                for pattern in patterns:
                    f.write(f"{pattern}\n")
            return {"success": True, "message": "Patterns added to .gitignore"}
        except Exception as e:
            logger.error(f"Error updating .gitignore: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def git_show(self, commit: str) -> Dict:
        """Show details of a specific commit."""
        return self.run_command(f"git show {commit}")
        
    def git_blame(self, file: str) -> Dict:
        """Show who changed each line in a file."""
        return self.run_command(f"git blame {file}")
        
    def git_checkout(self, target: str) -> Dict:
        """Checkout a specific commit, branch, or file."""
        return self.run_command(f"git checkout {target}")
        
    def git_fetch(self, remote: str = "origin") -> Dict:
        """Fetch changes from a remote repository."""
        return self.run_command(f"git fetch {remote}")
        
    def git_merge_base(self, commit1: str, commit2: str) -> Dict:
        """Find the common ancestor of two commits."""
        return self.run_command(f"git merge-base {commit1} {commit2}")
        
    def git_rebase(self, branch: str) -> Dict:
        """Rebase the current branch onto another branch."""
        return self.run_command(f"git rebase {branch}")
        
    def git_cherry_pick(self, commit: str) -> Dict:
        """Apply changes from a specific commit."""
        return self.run_command(f"git cherry-pick {commit}")
        
    def git_tag(self, name: str, message: Optional[str] = None) -> Dict:
        """Create a tag."""
        command = f'git tag -a {name} -m "{message}"' if message else f"git tag {name}"
        return self.run_command(command)
        
    def git_tag_list(self) -> Dict:
        """List all tags."""
        return self.run_command("git tag -l")
        
    def git_tag_delete(self, name: str) -> Dict:
        """Delete a tag."""
        return self.run_command(f"git tag -d {name}")
        
    def git_tag_push(self, name: str, remote: str = "origin") -> Dict:
        """Push a tag to a remote repository."""
        return self.run_command(f"git push {remote} {name}")
        
    def git_tag_push_all(self, remote: str = "origin") -> Dict:
        """Push all tags to a remote repository."""
        return self.run_command(f"git push {remote} --tags") 