#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AtlasVibe CLI - Main entry point for the application.
"""

import os
import sys
import subprocess
import click
from pathlib import Path
import shutil
import platform


def get_app_dir() -> Path:
    """Get the installed app directory."""
    # When installed via pip, the app files are in the package directory
    import atlasvibe
    # The actual app files are in the parent directory of the atlasvibe package
    return Path(atlasvibe.__file__).parent.parent


def setup_environment() -> None:
    """Set up the environment for running AtlasVibe."""
    app_dir = get_app_dir()
    
    # Set environment variables
    os.environ['ATLASVIBE_HOME'] = str(app_dir)
    
    # Add Python paths - include the pkgs directory so imports work
    python_paths = [
        str(app_dir),
        str(app_dir / 'captain'),
        str(app_dir / 'pkgs'),  # This allows "from atlasvibe import ..." to work
        str(app_dir / 'pkgs' / 'atlasvibe'),
        str(app_dir / 'pkgs' / 'atlasvibe_sdk'),
    ]
    
    # Also add to sys.path for immediate effect
    for path in python_paths:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    new_pythonpath = ':'.join(python_paths + [current_pythonpath] if current_pythonpath else python_paths)
    os.environ['PYTHONPATH'] = new_pythonpath


@click.group()
@click.version_option()
def cli():
    """AtlasVibe - Visual Programming IDE for Python."""
    setup_environment()


@cli.command()
@click.option('--port', default=5392, help='Port to run the server on')
@click.option('--log-level', default='INFO', help='Logging level')
def server(port: int, log_level: str):
    """Run the AtlasVibe backend server."""
    app_dir = get_app_dir()
    main_py = app_dir / 'main.py'
    
    if not main_py.exists():
        click.echo(f"Error: main.py not found at {main_py}", err=True)
        sys.exit(1)
    
    # Run the server
    cmd = [sys.executable, str(main_py), '--port', str(port), '--log-level', log_level]
    
    click.echo(f"Starting AtlasVibe server on port {port}...")
    try:
        subprocess.run(cmd, cwd=str(app_dir))
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")


@cli.command()
@click.option('--dev', is_flag=True, help='Run in development mode')
def ui(dev: bool):
    """Run the AtlasVibe Electron UI."""
    app_dir = get_app_dir()
    
    if dev:
        # Development mode - run with npm/pnpm
        click.echo("Starting AtlasVibe in development mode...")
        
        # Check if pnpm is available
        if shutil.which('pnpm'):
            cmd = ['pnpm', 'run', 'dev']
        else:
            cmd = ['npm', 'run', 'dev']
            
        try:
            subprocess.run(cmd, cwd=str(app_dir))
        except KeyboardInterrupt:
            click.echo("\nDevelopment server stopped.")
    else:
        # Production mode - run the built Electron app
        electron_path = app_dir / 'electron'
        
        if platform.system() == 'Darwin':
            app_path = electron_path / 'atlasvibe.app' / 'Contents' / 'MacOS' / 'atlasvibe'
        elif platform.system() == 'Windows':
            app_path = electron_path / 'atlasvibe.exe'
        else:
            app_path = electron_path / 'atlasvibe'
            
        if not app_path.exists():
            click.echo(f"Error: Electron app not found at {app_path}", err=True)
            click.echo("You may need to build the app first or use --dev mode")
            sys.exit(1)
            
        click.echo("Starting AtlasVibe UI...")
        try:
            subprocess.run([str(app_path)], cwd=str(app_dir))
        except KeyboardInterrupt:
            click.echo("\nUI closed.")


@cli.command()
def run():
    """Run both server and UI (default command)."""
    import threading
    import time
    
    app_dir = get_app_dir()
    
    # Start server in a separate thread
    server_thread = threading.Thread(
        target=lambda: subprocess.run(
            [sys.executable, str(app_dir / 'main.py')],
            cwd=str(app_dir)
        )
    )
    server_thread.daemon = True
    server_thread.start()
    
    # Wait a bit for server to start
    click.echo("Starting AtlasVibe server...")
    time.sleep(2)
    
    # Start UI
    click.echo("Starting AtlasVibe UI...")
    ui.callback(dev=False)


@cli.command()
@click.argument('path', type=click.Path())
def init(path: str):
    """Initialize a new AtlasVibe project."""
    project_path = Path(path)
    
    if project_path.exists():
        click.echo(f"Error: Path {project_path} already exists", err=True)
        sys.exit(1)
    
    # Create project structure
    project_path.mkdir(parents=True)
    (project_path / 'atlasvibe_blocks').mkdir()
    (project_path / 'flows').mkdir()
    
    # Create a default project file
    project_file = project_path / 'project.atlasvibe'
    project_file.write_text('{}')  # Empty JSON for now
    
    click.echo(f"Created new AtlasVibe project at {project_path}")


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()