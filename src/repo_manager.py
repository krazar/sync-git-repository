from git import Repo
from github import Github
import os
from pathlib import Path
import logging
from typing import List

class GitRepoManager:
    def __init__(self, folder_path: str, github_token: str):
        self.folder_path = Path(folder_path)
        self.github_client = Github(github_token)
        self.setup_logging()
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def find_git_repositories(self) -> List[Path]:
        """Find all git repositories in the specified folder"""
        git_repos = []
        for item in self.folder_path.glob("*"):
            if item.is_dir() and (item / ".git").exists():
                git_repos.append(item)
        return git_repos
    
    def get_default_branch(self, repo: Repo) -> str:
        """Detect the default branch (main or master)"""
        try:
            # First try to get it from the remote
            default_branch = repo.active_branch.name
            
            # Check if main or master exists
            branches = [ref.name for ref in repo.references]
            if 'main' in branches:
                return 'main'
            elif 'master' in branches:
                return 'master'
            
            return default_branch
        except Exception as e:
            self.logger.warning(f"Could not detect default branch, falling back to 'main': {str(e)}")
            return 'main'
    
    def cleanup_sync_branches(self, repo: Repo):
        """Clean up any sync-related branches"""
        branches_to_remove = [
            "sync_temp",
            "sync_origin_github"  # Old branch name
        ]
        
        for branch_name in branches_to_remove:
            try:
                if branch_name in repo.heads:
                    self.logger.info(f"Removing old branch '{branch_name}'")
                    # Ensure we're not on the branch we're trying to delete
                    if repo.active_branch.name == branch_name:
                        default_branch = self.get_default_branch(repo)
                        repo.heads[default_branch].checkout()
                    repo.delete_head(branch_name, force=True)
            except Exception as e:
                self.logger.warning(f"Could not delete branch '{branch_name}': {str(e)}")

    def sync_repository(self, repo_path: Path, source_remote: str, target_remote: str):
        """Sync repository from source remote to target remote using a temporary branch"""
        try:
            repo = Repo(repo_path)
            
            # Detect default branch
            default_branch = self.get_default_branch(repo)
            self.logger.info(f"Detected default branch '{default_branch}' for {repo_path.name}")
            
            # Clean up any old sync branches
            self.cleanup_sync_branches(repo)
            
            # Create a temporary branch name
            temp_branch = "sync_temp"
            
            # Fetch from source remote
            source = repo.remote(source_remote)
            self.logger.info(f"Fetching from {source_remote} for {repo_path.name}")
            source.fetch()
            
            # Create and checkout new temporary branch from default branch
            current = repo.create_head(temp_branch, commit=f'{source_remote}/{default_branch}')
            current.checkout()
            
            # Pull from source
            source.pull(refspec=f'{default_branch}:{temp_branch}')
            
            # Push to target
            target = repo.remote(target_remote)
            self.logger.info(f"Pushing to {target_remote} for {repo_path.name}")
            target.push(temp_branch)
            
            # Clean up: checkout default branch and delete temporary branch
            try:
                default = repo.heads[default_branch]
                default.checkout()
                repo.delete_head(temp_branch, force=True)
                self.logger.info(f"Cleaned up temporary branch in {repo_path.name}")
            except Exception as e:
                self.logger.warning(f"Could not clean up temp branch: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Error syncing repository {repo_path.name}: {str(e)}")
    
    def get_existing_github_repo(self, repo_name: str):
        """Check if GitHub repository already exists"""
        try:
            return self.github_client.get_user().get_repo(repo_name)
        except Exception:
            return None
    
    def create_or_get_github_repo(self, repo_path: Path):
        """Create private GitHub repository if it doesn't exist and add it as remote"""
        try:
            repo = Repo(repo_path)
            repo_name = repo_path.name
            
            # First check if repository already exists on GitHub
            github_repo = self.get_existing_github_repo(repo_name)
            
            if github_repo:
                self.logger.info(f"Found existing GitHub repository for {repo_name}")
            else:
                # Create new private GitHub repository
                self.logger.info(f"Creating new GitHub repository for {repo_name}")
                github_repo = self.github_client.get_user().create_repo(
                    repo_name,
                    private=True
                )
            
            # Add as remote if it doesn't exist
            remote_name = "github"
            remote_url = github_repo.clone_url
            
            # Check if remote already exists
            existing_remotes = [remote.name for remote in repo.remotes]
            if remote_name not in existing_remotes:
                repo.create_remote(remote_name, remote_url)
                self.logger.info(f"Added GitHub remote to {repo_name}")
            else:
                self.logger.info(f"GitHub remote already exists for {repo_name}")
            
            return github_repo
            
        except Exception as e:
            self.logger.error(f"Error processing GitHub repository for {repo_path.name}: {str(e)}")
            return None
