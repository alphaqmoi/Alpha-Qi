import os
import tempfile
import logging
from pathlib import Path
import shutil
from huggingface_hub import HfApi, login, HfFolder
from huggingface_hub.utils import RepositoryNotFoundError, RevisionNotFoundError

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def validate_token(token):
    """
    Validate the Hugging Face token by attempting to log in.
    
    Args:
        token (str): The Hugging Face token to validate
        
    Returns:
        bool: True if token is valid, False otherwise
    """
    try:
        # Try to log in with the provided token
        login(token=token, add_to_git_credential=False)
        # If login succeeds, token is valid
        api = HfApi(token=token)
        # Try to get user info to confirm token works
        user_info = api.whoami()
        logger.info(f"Successfully authenticated as {user_info.get('name', 'unknown')}")
        return True
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return False

def upload_to_hub(token, repo_name, model_files, private=True, create_repo=True):
    """
    Upload model files to Hugging Face Hub.
    
    Args:
        token (str): Hugging Face API token
        repo_name (str): Name of the repository to upload to
        model_files (list): List of file objects from Flask's request.files
        private (bool): Whether the repository should be private
        create_repo (bool): Whether to create a new repository
        
    Returns:
        dict: Result of the upload operation with 'success' flag and optional 'error' or 'repo_url'
    """
    # Create a temporary directory to store the model files
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize the Hugging Face API client
        api = HfApi(token=token)
        
        # Check if repository exists if not creating a new one
        if not create_repo:
            try:
                api.repo_info(repo_id=repo_name)
            except RepositoryNotFoundError:
                return {
                    'success': False,
                    'error': f"Repository '{repo_name}' not found. Enable 'Create new repository' option or use an existing repository."
                }
        
        # Save uploaded files to temporary directory
        saved_paths = []
        for file in model_files:
            if file.filename:
                file_path = os.path.join(temp_dir, file.filename)
                file.save(file_path)
                saved_paths.append(file_path)
                logger.debug(f"Saved file to {file_path}")
        
        if not saved_paths:
            return {
                'success': False,
                'error': "No valid files were uploaded"
            }
        
        # Create the repository if needed
        if create_repo:
            logger.info(f"Creating new repository: {repo_name}")
            api.create_repo(
                repo_id=repo_name,
                private=private,
                exist_ok=True
            )
            
        # Upload all files to the repository
        logger.info(f"Uploading files to {repo_name}")
        
        # Upload each file individually
        for file_path in saved_paths:
            file_name = os.path.basename(file_path)
            api.upload_file(
                path_or_fileobj=file_path,
                path_in_repo=file_name,
                repo_id=repo_name,
                commit_message=f"Upload {file_name}"
            )
            logger.info(f"Uploaded {file_name} to {repo_name}")
        
        # Build the repository URL
        repo_url = f"https://huggingface.co/{repo_name}"
        
        return {
            'success': True,
            'repo_url': repo_url
        }
    
    except RepositoryNotFoundError:
        return {
            'success': False,
            'error': f"Repository '{repo_name}' not found and could not be created. Check your permissions."
        }
    except RevisionNotFoundError:
        return {
            'success': False,
            'error': f"The main branch of repository '{repo_name}' was not found."
        }
    except Exception as e:
        logger.error(f"Error uploading to Hugging Face Hub: {str(e)}")
        return {
            'success': False,
            'error': f"Upload failed: {str(e)}"
        }
    finally:
        # Clean up the temporary directory
        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"Removed temporary directory {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {str(e)}")
