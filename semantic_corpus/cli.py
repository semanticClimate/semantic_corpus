"""Command-line interface for semantic_corpus."""

import argparse
import json
import sys
import yaml
from pathlib import Path
from typing import Optional

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.core.exceptions import CorpusError, RepositoryError


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Semantic Corpus - Creation and management of personal scientific corpora",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Configuration file path'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create corpus command
    create_parser = subparsers.add_parser('create', help='Create a new corpus')
    create_parser.add_argument('--name', '-n', required=True, help='Corpus name')
    create_parser.add_argument('--path', '-p', type=str, help='Corpus directory path')
    
    # Search papers command
    search_parser = subparsers.add_parser('search', help='Search for papers in repositories')
    search_parser.add_argument('--query', '-q', required=True, help='Search query')
    search_parser.add_argument('--repository', '-r', default='europe_pmc', help='Repository to search')
    search_parser.add_argument('--limit', '-l', type=int, default=10, help='Maximum number of results')
    search_parser.add_argument('--output', '-o', type=str, help='Output directory')
    
    # Download papers command
    download_parser = subparsers.add_parser('download', help='Download papers from repositories')
    download_parser.add_argument('--query', '-q', required=True, help='Search query')
    download_parser.add_argument('--repository', '-r', default='europe_pmc', help='Repository to search')
    download_parser.add_argument('--limit', '-l', type=int, default=10, help='Maximum number of results')
    download_parser.add_argument('--output', '-o', required=True, type=str, help='Output directory')
    download_parser.add_argument('--formats', '-f', default='xml,pdf', help='File formats to download')
    
    return parser


def create_corpus_command(args) -> None:
    """Handle create corpus command."""
    try:
        if args.path:
            corpus_dir = Path(args.path) / args.name
        else:
            corpus_dir = Path.cwd() / args.name
        
        corpus_manager = CorpusManager(corpus_dir)
        print(f"Corpus '{args.name}' created successfully at {corpus_dir}")
        
    except CorpusError as e:
        print(f"Error creating corpus: {e.message}", file=sys.stderr)
        sys.exit(1)


def search_papers_command(args) -> None:
    """Handle search papers command."""
    try:
        repo = RepositoryFactory.get_repository(args.repository)
        results = repo.search_papers(query=args.query, limit=args.limit)
        
        print(f"Found {len(results)} papers")
        
        for i, paper in enumerate(results, 1):
            title = paper.get('title', 'No title')
            print(f"{i}. {title}")
        
        if args.output:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save results to file
            results_file = output_dir / "search_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"Results saved to {results_file}")
        
    except RepositoryError as e:
        print(f"Error searching papers: {e.message}", file=sys.stderr)
        sys.exit(1)


def download_papers_command(args) -> None:
    """Handle download papers command."""
    try:
        repo = RepositoryFactory.get_repository(args.repository)
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Search for papers
        results = repo.search_papers(query=args.query, limit=args.limit)
        print(f"Found {len(results)} papers, starting download...")
        
        downloaded_count = 0
        format_list = [f.strip() for f in args.formats.split(',')]
        
        for paper in results:
            paper_id = paper.get('pmcid') or paper.get('arxiv_id') or paper.get('pmid')
            if not paper_id:
                continue
            
            try:
                result = repo.download_paper(paper_id, output_dir, format_list)
                if result['success']:
                    downloaded_count += 1
                    print(f"Downloaded {paper_id}")
            except Exception as e:
                print(f"Failed to download {paper_id}: {e}")
        
        print(f"Downloaded {downloaded_count} papers to {output_dir}")
        
    except RepositoryError as e:
        print(f"Error downloading papers: {e.message}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Handle configuration file if provided
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Override args with config values
                for key, value in config.items():
                    if hasattr(args, key):
                        setattr(args, key, value)
    
    # Execute command
    if args.command == 'create':
        create_corpus_command(args)
    elif args.command == 'search':
        search_papers_command(args)
    elif args.command == 'download':
        download_papers_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
