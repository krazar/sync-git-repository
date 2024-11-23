from repo_manager import GitRepoManager
import os
from dotenv import load_dotenv
from pathlib import Path

def main():
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment variables
    folder_path = os.getenv('REPOS_FOLDER')
    github_token = os.getenv('GITHUB_TOKEN')
    
    # Validate environment variables
    if not folder_path:
        print("Error: REPOS_FOLDER environment variable is not set")
        return
    
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is not set")
        return
    
    # Validate folder exists
    if not os.path.isdir(folder_path):
        print(f"Error: Folder {folder_path} does not exist")
        return
    
    manager = GitRepoManager(folder_path, github_token)
    
    # Find all repositories
    repos = manager.find_git_repositories()
    
    if not repos:
        print("No git repositories found!")
        return
    
    print(f"Found {len(repos)} repositories to process")
    
    # Process each repository
    for repo_path in repos:
        print(f"\nProcessing repository: {repo_path.name}")
        
        # Create or get GitHub repository and add remote
        github_repo = manager.create_or_get_github_repo(repo_path)
        
        if github_repo:
            # Only sync if we have a valid GitHub repository
            manager.sync_repository(repo_path, "origin", "github")
        else:
            print(f"Skipping sync for {repo_path.name} due to GitHub repository issues")
        
        print(f"Finished processing {repo_path.name}")
    
    print("\nAll repositories processed!")

if __name__ == "__main__":
    main() 
