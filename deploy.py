"""
Deploy script for Hugging Face Spaces.
Uploads the project to a HF Space and triggers a Docker build.

Usage:
    python deploy.py
    python deploy.py --repo-id your-username/your-space

Requires:
    pip install huggingface_hub
    huggingface-cli login   (or set HF_TOKEN env var)
"""

import argparse
import os
import sys

from huggingface_hub import HfApi, login


def main():
    parser = argparse.ArgumentParser(description="Deploy to Hugging Face Spaces")
    parser.add_argument(
        "--repo-id",
        type=str,
        default="sarayusapa/scalerthon",
        help="HF Space repo ID (e.g. username/space-name)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="HF token (defaults to HF_TOKEN env var or cached login)",
    )
    args = parser.parse_args()

    # Authenticate
    token = args.token or os.environ.get("HF_TOKEN")
    if token:
        login(token=token)
    else:
        print("No HF_TOKEN found. Please run: huggingface-cli login")
        sys.exit(1)

    api = HfApi()

    # Create the space if it doesn't exist
    print(f"Creating/updating Space: {args.repo_id}")
    api.create_repo(
        repo_id=args.repo_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
    )

    # Upload all project files
    print(f"Uploading files to {args.repo_id} ...")
    api.upload_folder(
        folder_path=os.path.dirname(os.path.abspath(__file__)),
        repo_id=args.repo_id,
        repo_type="space",
        ignore_patterns=[".git", ".venv", "__pycache__", ".DS_Store", "deploy.py"],
    )

    space_url = f"https://huggingface.co/spaces/{args.repo_id}"
    print(f"\nDone! Space is building at: {space_url}")
    print(f"Health check: {space_url.replace('spaces/', '')}/health")


if __name__ == "__main__":
    main()
