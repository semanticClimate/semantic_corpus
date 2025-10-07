"""Command-line interface for semantic_corpus."""

import click
import yaml
from pathlib import Path
from typing import Optional

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.core.exceptions import CorpusError, RepositoryError


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def main(ctx: click.Context, config: Optional[str], verbose: bool) -> None:
    """Semantic Corpus - Creation and management of personal scientific corpora."""
    ctx.ensure_object(dict)
    ctx.obj['config'] = config
    ctx.obj['verbose'] = verbose


@main.command()
@click.option('--name', '-n', required=True, help='Corpus name')
@click.option('--path', '-p', type=click.Path(), help='Corpus directory path')
def create_corpus(name: str, path: Optional[str]) -> None:
    """Create a new corpus."""
    try:
        if path:
            corpus_dir = Path(path) / name
        else:
            corpus_dir = Path.cwd() / name
        
        corpus_manager = CorpusManager(corpus_dir)
        click.echo(f"Corpus '{name}' created successfully at {corpus_dir}")
        
    except CorpusError as e:
        click.echo(f"Error creating corpus: {e.message}", err=True)
        raise click.Abort()


@main.command()
@click.option('--query', '-q', required=True, help='Search query')
@click.option('--repository', '-r', default='europe_pmc', help='Repository to search')
@click.option('--limit', '-l', default=10, help='Maximum number of results')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
def search_papers(query: str, repository: str, limit: int, output: Optional[str]) -> None:
    """Search for papers in repositories."""
    try:
        repo = RepositoryFactory.get_repository(repository)
        results = repo.search_papers(query, limit=limit)
        
        click.echo(f"Found {len(results)} papers")
        
        for i, paper in enumerate(results, 1):
            title = paper.get('title', 'No title')
            click.echo(f"{i}. {title}")
        
        if output:
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save results to file
            import json
            results_file = output_dir / "search_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            click.echo(f"Results saved to {results_file}")
        
    except RepositoryError as e:
        click.echo(f"Error searching papers: {e.message}", err=True)
        raise click.Abort()


@main.command()
@click.option('--query', '-q', required=True, help='Search query')
@click.option('--repository', '-r', default='europe_pmc', help='Repository to search')
@click.option('--limit', '-l', default=10, help='Maximum number of results')
@click.option('--output', '-o', required=True, type=click.Path(), help='Output directory')
@click.option('--formats', '-f', default='xml,pdf', help='File formats to download')
def download_papers(query: str, repository: str, limit: int, output: str, formats: str) -> None:
    """Download papers from repositories."""
    try:
        repo = RepositoryFactory.get_repository(repository)
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Search for papers
        results = repo.search_papers(query, limit=limit)
        click.echo(f"Found {len(results)} papers, starting download...")
        
        downloaded_count = 0
        format_list = [f.strip() for f in formats.split(',')]
        
        for paper in results:
            paper_id = paper.get('pmcid') or paper.get('arxiv_id') or paper.get('pmid')
            if not paper_id:
                continue
            
            try:
                result = repo.download_paper(paper_id, output_dir, format_list)
                if result['success']:
                    downloaded_count += 1
                    click.echo(f"Downloaded {paper_id}")
            except Exception as e:
                click.echo(f"Failed to download {paper_id}: {e}")
        
        click.echo(f"Downloaded {downloaded_count} papers to {output_dir}")
        
    except RepositoryError as e:
        click.echo(f"Error downloading papers: {e.message}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()
