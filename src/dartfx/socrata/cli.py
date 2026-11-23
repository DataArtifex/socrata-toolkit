import csv
import json
import os
import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import requests
import typer
from dotenv import find_dotenv, load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dartfx.socrata.__about__ import __version__
from dartfx.socrata.cdif import CdifGenerator, resolve_serialization_flavor
from dartfx.socrata.dcat import DcatGenerator, DcatProfile
from dartfx.socrata.socrata import (
    SERVERS,
    SocrataDataset,
    SocrataServer,
    get_known_servers,
    jinja_env,
)

load_dotenv(find_dotenv(usecwd=True))


def _normalize_smart_dashes() -> None:
    """Sanitize macOS smart dashes (en-dash, em-dash) and bare -o flag in sys.argv."""
    normalized: list[str] = []
    i = 0
    argv = sys.argv
    while i < len(argv):
        arg = argv[i]
        if any(arg.startswith(prefix) for prefix in ("-–", "—", "–", "−")):
            clean = arg.replace("-–", "--").replace("—", "--").replace("−", "-")
            if clean.startswith("–"):
                clean = "--" + clean[1:] if len(clean) > 2 else "-" + clean[1:]
            arg = clean

        if arg in ("-o", "--output"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                normalized.append("--output=AUTO")
                i += 1
                continue

        normalized.append(arg)
        i += 1
    sys.argv[:] = normalized


_normalize_smart_dashes()

app = typer.Typer(
    name="dartfx-socrata",
    help="CLI for discovering, searching, and exporting catalog metadata from Socrata servers.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


class _ConsoleProxy:
    """Dynamic proxy for Console that binds to active sys.stdout/sys.stderr per call."""

    def __init__(self, stderr: bool = False) -> None:
        self._stderr = stderr

    def __getattr__(self, name: str) -> Any:
        return getattr(Console(stderr=self._stderr), name)


console = _ConsoleProxy()
err_console = _ConsoleProxy(stderr=True)


class OutputFormat(StrEnum):
    TABLE = "table"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    MD = "md"


class SerializationFlavor(StrEnum):
    JSON = "json"
    JSON_LD = "json-ld"
    TTL = "ttl"
    XML = "xml"
    N3 = "n3"


class SearchFormat(StrEnum):
    TABLE = "table"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    MD = "md"
    CDIF_DISCOVERY = "cdif-discovery"


class MetadataFormat(StrEnum):
    SOCRATA = "socrata"
    NATIVE = "native"
    JSON = "json"
    DCAT = "dcat"
    CDIF = "cdif"
    CDIF_DISCOVERY = "cdif-discovery"
    CDIF_DATA_DESCRIPTION = "cdif-data-description"
    CROISSANT = "croissant"
    DDI = "ddi"
    MARKDOWN = "markdown"
    MD = "md"


ExportFormat = MetadataFormat


class DataFormat(StrEnum):
    CSV = "csv"
    JSON = "json"


ENV_MAP: dict[str, tuple[str, str, str]] = {
    "python": ("python-pandas", "python", "py"),
    "python-pandas": ("python-pandas", "python", "py"),
    "pandas": ("python-pandas", "python", "py"),
    "py": ("python-pandas", "python", "py"),
    "r": ("r-socrata", "r", "R"),
    "r-socrata": ("r-socrata", "r", "R"),
    "ruby": ("soda-ruby", "ruby", "rb"),
    "soda-ruby": ("soda-ruby", "ruby", "rb"),
    "rb": ("soda-ruby", "ruby", "rb"),
    "dotnet": ("soda-dotnet", "csharp", "cs"),
    "soda-dotnet": ("soda-dotnet", "csharp", "cs"),
    "csharp": ("soda-dotnet", "csharp", "cs"),
    "cs": ("soda-dotnet", "csharp", "cs"),
    ".net": ("soda-dotnet", "csharp", "cs"),
    "stata": ("stata", "stata", "do"),
    "do": ("stata", "stata", "do"),
    "sas": ("sas", "sas", "sas"),
    "powershell": ("powershell", "powershell", "ps1"),
    "ps": ("powershell", "powershell", "ps1"),
    "ps1": ("powershell", "powershell", "ps1"),
    "jquery": ("jquery", "javascript", "js"),
    "javascript": ("jquery", "javascript", "js"),
    "js": ("jquery", "javascript", "js"),
}


def _resolve_enum_prefix[E: StrEnum](value: str, enum_cls: type[E], param_name: str = "--format") -> E:
    """Resolve an enum value by exact match or unique case-insensitive prefix."""
    cleaned = value.strip().lower()
    for member in enum_cls:
        if member.value == cleaned:
            return member
    matches = [member for member in enum_cls if member.value.startswith(cleaned)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        options = ", ".join(m.value for m in matches)
        raise typer.BadParameter(f"Ambiguous value '{value}' for {param_name}. Matches: {options}")
    valid = ", ".join(m.value for m in enum_cls)
    raise typer.BadParameter(f"Invalid value '{value}' for {param_name}. Choose from: {valid}")


def get_server(hostname: str | None = None, disk_cache_dir: str | None = None) -> SocrataServer:
    """Helper to create a configured SocrataServer instance."""
    resolved_host = hostname or os.environ.get("SOCRATA_SERVER") or "data.sfgov.org"
    cache_dir = disk_cache_dir or os.environ.get("SOCRATA_CACHE_DIR")
    return SocrataServer(host=resolved_host, disk_cache_root=cache_dir)


def _resolve_output_path(output: str | None, prefix: str, ext: str) -> Path | None:
    """Resolve destination file path, supporting AUTO naming."""
    if not output:
        return None
    out_str = output.strip()
    if out_str.lower() in ("auto", "__auto__", "-"):
        return Path(f"dartfx-socrata.{prefix}.{ext}")
    return Path(out_str)


def _write_or_print(
    content: str,
    out_path: Path | None,
    success_message: str = "Output saved to:",
) -> None:
    """Write text content to file or print to standard output."""
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"[bold green]✓ {success_message}[/] {out_path}")
    else:
        typer.echo(content.rstrip("\n"))


@app.command()
def version() -> None:
    """Display the version of dartfx-socrata."""
    console.print(f"dartfx-socrata version: [bold green]{__version__}[/bold green]")


@app.command(name="servers")
@app.command(name="list", help="Alias for 'servers'. List known Socrata portals and servers.")
def list_servers(
    query: Annotated[
        str | None,
        typer.Option("--query", "-q", help="Filter portals by name, hostname, country, or domain."),
    ] = None,
    format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.TABLE,
    json_output: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
    markdown_output: Annotated[bool, typer.Option("--markdown", "--md", help="Output results as Markdown")] = False,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write output to a file")] = None,
    file: Annotated[
        Path | None,
        typer.Option("--file", help="Path to custom servers.yaml / data.yaml registry"),
    ] = None,
) -> None:
    """List known Socrata open data portals."""
    known = get_known_servers(file) if file else SERVERS
    items: list[dict[str, Any]] = []
    for host, meta in known.items():
        name = str(meta.get("name", host))
        publishers = list(meta.get("publisher", []))
        spatial = list(meta.get("spatial", []))
        custodian = meta.get("custodian") or {}
        geocov = meta.get("geocoverage") or {}
        domains = list(meta.get("domains") or [])
        country_code = meta.get("country_code")

        if query:
            q_lower = query.lower()
            searchable = " ".join(
                [
                    host,
                    name,
                    str(country_code or ""),
                    str(custodian.get("name", "")),
                    str(geocov.get("description", "")),
                    " ".join(domains),
                ]
            ).lower()
            if q_lower not in searchable:
                continue

        pub_name = (
            publishers[0]
            if publishers
            else (str(custodian.get("name")) if isinstance(custodian, dict) and custodian.get("name") else host)
        )
        spatial_desc = (
            spatial[0]
            if spatial
            else (str(geocov.get("description")) if isinstance(geocov, dict) and geocov.get("description") else "-")
        )

        items.append(
            {
                "hostname": host,
                "name": name,
                "publisher": pub_name,
                "spatial": spatial_desc,
                "country_code": country_code,
                "domains": domains,
                "custodian": custodian,
                "geocoverage": geocov,
                "url": meta.get("url") or f"https://{host}",
            }
        )

    effective_format = OutputFormat.JSON if json_output else (OutputFormat.MARKDOWN if markdown_output else format)
    ext = (
        "json"
        if effective_format == OutputFormat.JSON
        else (
            "csv"
            if effective_format == OutputFormat.CSV
            else "md"
            if effective_format in (OutputFormat.MARKDOWN, OutputFormat.MD)
            else "txt"
        )
    )
    out_path = _resolve_output_path(output, "servers", ext)

    if effective_format == OutputFormat.JSON:
        json_str = json.dumps(items, indent=2)
        if out_path:
            _write_or_print(json_str, out_path, "Server directory saved to:")
        else:
            console.print_json(json_str)
        return

    if effective_format in (OutputFormat.MARKDOWN, OutputFormat.MD):
        md_lines = [
            "| Portal Name | Hostname | Publisher | Spatial Coverage |",
            "|:---|:---|:---|:---|",
        ]
        for it in items:
            name_val = it["name"].replace("|", "\\|")
            host_val = f"[{it['hostname']}]({it['url']})"
            pub_val = str(it["publisher"]).replace("|", "\\|")
            sp_val = str(it["spatial"]).replace("|", "\\|")
            md_lines.append(f"| {name_val} | {host_val} | {pub_val} | {sp_val} |")
        _write_or_print("\n".join(md_lines), out_path, "Server directory saved to:")
        return

    if effective_format == OutputFormat.CSV:
        from io import StringIO

        buf = StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["hostname", "name", "publisher", "spatial", "url"],
            extrasaction="ignore",
        )
        writer.writeheader()
        for it in items:
            writer.writerow(it)
        _write_or_print(buf.getvalue(), out_path, "Server directory saved to:")
        return

    # Table format
    table = Table(title=f"Known Socrata Open Data Portals ({len(items)} found)")
    table.add_column("Portal Name", style="cyan")
    table.add_column("Hostname", style="magenta")
    table.add_column("Publisher", style="green")
    table.add_column("Spatial Coverage", style="yellow")

    for it in items:
        clickable_host = f"[link={it['url']}]{it['hostname']}[/link]"
        table.add_row(str(it["name"]), clickable_host, str(it["publisher"]), str(it["spatial"]))

    if out_path:
        fc = Console(record=True, width=120)
        fc.print(table)
        _write_or_print(fc.export_text(), out_path, "Server directory saved to:")
    else:
        console.print(table)


@app.command()
def info(
    hostname: Annotated[
        str | None,
        typer.Argument(
            help="Socrata server hostname (e.g. data.sfgov.org)",
            envvar="SOCRATA_SERVER",
        ),
    ] = None,
    format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.TABLE,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write output to a file")] = None,
) -> None:
    """Get metadata and status for a specific Socrata portal."""
    server_client = get_server(hostname)
    resolved_host = server_client.host

    with console.status(f"[bold green]Fetching portal info for {resolved_host}..."):
        try:
            catalog_probe = server_client.search_datasets(limit=1)
            total_datasets: int | None = catalog_probe.get("resultSetSize")
            online = True
            error_message = None
        except Exception as e:
            total_datasets = None
            online = False
            error_message = str(e)

    info_data: dict[str, Any] = {
        "hostname": resolved_host,
        "name": server_client.name,
        "url": server_client.host_url,
        "online": online,
        "total_datasets": total_datasets,
        "publisher": server_client.publisher,
        "spatial": server_client.spatial,
        "discovery_api": f"https://{resolved_host}/api/catalog/v1",
    }
    if error_message:
        info_data["error"] = error_message

    effective_format = OutputFormat.JSON if json_output else format
    info_ext = "json" if effective_format == OutputFormat.JSON else "txt"
    out_path = _resolve_output_path(output, f"info.{resolved_host}", info_ext)

    if effective_format == OutputFormat.JSON:
        json_str = json.dumps(info_data, indent=2)
        if out_path:
            _write_or_print(json_str, out_path, "Portal info saved to:")
        else:
            console.print_json(json_str)
        return

    status_str = (
        "[bold green]Online[/bold green]" if online else f"[bold red]Offline / Unreachable[/bold red] ({error_message})"
    )
    count_str = f"{total_datasets:,}" if total_datasets is not None else "Unknown"
    pub_str = ", ".join(server_client.publisher) if server_client.publisher else resolved_host
    spatial_str = ", ".join(server_client.spatial) if server_client.spatial else "Not specified"

    panel_text = (
        f"[bold cyan]Portal Name:[/] {server_client.name}\n"
        f"[bold cyan]Hostname:[/] [link={server_client.host_url}]{resolved_host}[/link]\n"
        f"[bold cyan]Status:[/] {status_str}\n"
        f"[bold cyan]Catalog Datasets:[/] {count_str}\n"
        f"[bold cyan]Publisher:[/] {pub_str}\n"
        f"[bold cyan]Spatial Coverage:[/] {spatial_str}\n"
        f"[bold cyan]Discovery API:[/] https://{resolved_host}/api/catalog/v1\n"
    )

    panel = Panel(panel_text, title=f"Socrata Portal: {resolved_host}", border_style="cyan")
    if out_path:
        fc = Console(record=True, width=100)
        fc.print(panel)
        _write_or_print(fc.export_text(), out_path, "Portal info saved to:")
    else:
        console.print(panel)


@app.command(name="search")
@app.command(name="catalog", help="Alias for 'search'. Search datasets in the Socrata catalog.")
def search(
    query: Annotated[str, typer.Argument(help="Search query term (or empty string to browse)")] = "",
    server: Annotated[
        str | None,
        typer.Option("--server", "-s", envvar="SOCRATA_SERVER", help="Socrata server hostname"),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Number of results to return")] = 25,
    offset: Annotated[int, typer.Option("--offset", help="Pagination offset")] = 0,
    category: Annotated[str | None, typer.Option("--category", "-c", help="Filter by domain category")] = None,
    order: Annotated[
        str | None,
        typer.Option("--order", help="Sort order (updatedAt, createdAt, name, page_views_total)"),
    ] = None,
    sort_order: Annotated[str | None, typer.Option("--sort-order", help="Sort direction: 'asc' or 'desc'")] = None,
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format (table, json, csv, markdown, cdif-discovery; unique prefixes supported)",
        ),
    ] = SearchFormat.TABLE.value,
    flavor: Annotated[
        SerializationFlavor | None,
        typer.Option("--flavor", help="Serialization flavor for CDIF output (json, json-ld, ttl, xml, n3)"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output results as JSON")] = False,
    markdown_output: Annotated[bool, typer.Option("--markdown", "--md", help="Output results as Markdown")] = False,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write output to a file")] = None,
) -> None:
    """Search for datasets in a Socrata catalog."""
    server_client = get_server(server)

    with console.status(f"[bold green]Searching catalog on {server_client.host} for '{query}'..."):
        try:
            results_data = server_client.search_datasets(
                q=query if query else None,
                limit=limit,
                offset=offset,
                order=order,
                sort_order=sort_order,
                categories=category,
            )
        except Exception as e:
            console.print(f"[bold red]Error searching catalog:[/] {e}")
            raise typer.Exit(code=1) from e

    results = results_data.get("results", [])
    total = results_data.get("resultSetSize", len(results))

    resolved_format = _resolve_enum_prefix(format, SearchFormat)
    effective_format: SearchFormat = (
        SearchFormat.JSON if json_output else (SearchFormat.MARKDOWN if markdown_output else resolved_format)
    )

    if effective_format == SearchFormat.CDIF_DISCOVERY:
        generator = CdifGenerator(server=server_client)
        cdif_models = generator.build_from_search_results(results_data)
        chosen_flavor = flavor.value if flavor else SerializationFlavor.JSON_LD.value
        target_fmt, cdif_ext = resolve_serialization_flavor(chosen_flavor, default="json-ld")
        cdif_content = generator.serialize(cdif_models, flavor=chosen_flavor)
        out_path = _resolve_output_path(output, "search.cdif-discovery", cdif_ext)
        if out_path:
            _write_or_print(cdif_content, out_path, "CDIF Discovery search results saved to:")
        elif target_fmt in ("json", "json-ld"):
            console.print_json(cdif_content)
        else:
            typer.echo(cdif_content.rstrip("\n"))
        return

    ext = (
        "json"
        if effective_format == SearchFormat.JSON
        else (
            "csv"
            if effective_format == SearchFormat.CSV
            else "md"
            if effective_format in (SearchFormat.MARKDOWN, SearchFormat.MD)
            else "txt"
        )
    )
    out_path = _resolve_output_path(output, "search", ext)

    if effective_format == SearchFormat.JSON:
        json_str = json.dumps(results_data, indent=2)
        if out_path:
            _write_or_print(json_str, out_path, "Search results saved to:")
        else:
            console.print_json(json_str)
        return

    flattened_rows: list[dict[str, Any]] = []
    for item in results:
        res = item.get("resource", {})
        classification = item.get("classification", {})
        ds_id = res.get("id") or item.get("id", "N/A")
        ds_name = res.get("name") or res.get("title") or ds_id
        cat = classification.get("domain_category") or (
            classification.get("categories", [None])[0] if classification.get("categories") else "N/A"
        )
        views = res.get("page_views", {}).get("page_views_total")
        views_str = f"{views:,}" if isinstance(views, int) else "-"
        updated = res.get("updatedAt", "")[:10] if res.get("updatedAt") else "-"
        desc = res.get("description") or ""
        short_desc = desc.replace("\n", " ").strip()
        if len(short_desc) > 65:
            short_desc = short_desc[:62] + "..."
        permalink = item.get("permalink") or f"https://{server_client.host}/d/{ds_id}"

        flattened_rows.append(
            {
                "id": ds_id,
                "name": ds_name,
                "category": cat or "N/A",
                "views": views_str,
                "updated": updated,
                "description": short_desc,
                "permalink": permalink,
            }
        )

    if effective_format in (SearchFormat.MARKDOWN, SearchFormat.MD):
        md_lines = [
            f"# Catalog Search: '{query}' on {server_client.host} (Total: {total:,})",
            "",
            "| ID | Title / Dataset | Category | Views | Updated |",
            "|:---|:---|:---|---:|:---:|",
        ]
        for row in flattened_rows:
            id_link = f"[{row['id']}]({row['permalink']})"
            title_esc = str(row["name"]).replace("|", "\\|")
            cat_esc = str(row["category"]).replace("|", "\\|")
            md_lines.append(f"| {id_link} | {title_esc} | {cat_esc} | {row['views']} | {row['updated']} |")
        _write_or_print("\n".join(md_lines), out_path, "Search results saved to:")
        return

    if effective_format == SearchFormat.CSV:
        from io import StringIO

        buf = StringIO()
        csv_fields = ["id", "name", "category", "views", "updated", "description", "permalink"]
        writer = csv.DictWriter(buf, fieldnames=csv_fields)
        writer.writeheader()
        for row in flattened_rows:
            writer.writerow(row)
        _write_or_print(buf.getvalue(), out_path, "Search results saved to:")
        return

    # Table format
    title_text = f"Catalog Search on {server_client.host} for '{query or '*'}' (Total: {total:,})"
    table = Table(title=title_text)
    table.add_column("ID", style="magenta")
    table.add_column("Title / Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Views", style="yellow", justify="right")
    table.add_column("Updated", style="dim", justify="center")
    table.add_column("Description", style="white")

    for row in flattened_rows:
        clickable_id = f"[link={row['permalink']}]{row['id']}[/link]"
        table.add_row(
            clickable_id,
            row["name"],
            row["category"],
            row["views"],
            row["updated"],
            row["description"],
        )

    if out_path:
        fc = Console(record=True, width=130)
        fc.print(table)
        _write_or_print(fc.export_text(), out_path, "Search results saved to:")
    else:
        console.print(table)


@app.command(name="dataset")
@app.command(name="show", help="Alias for 'dataset'. Inspect dataset metadata.")
@app.command(name="inspect", help="Alias for 'dataset'. Inspect dataset metadata.")
def show_dataset(
    identifier: Annotated[str, typer.Argument(help="Socrata dataset 4x4 ID (e.g. vw6y-z8j6)")],
    server: Annotated[
        str | None,
        typer.Option("--server", "-s", envvar="SOCRATA_SERVER", help="Socrata server hostname"),
    ] = None,
    format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.TABLE,
    json_output: Annotated[bool, typer.Option("--json", help="Output raw view metadata as JSON")] = False,
    markdown_output: Annotated[
        bool,
        typer.Option("--markdown", "--md", help="Output dataset summary as Markdown"),
    ] = False,
    refresh: Annotated[bool, typer.Option("--refresh", help="Bypass cache and fetch fresh from server")] = False,
    cache_dir: Annotated[str | None, typer.Option("--cache-dir", help="Directory for disk cache")] = None,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write output to a file")] = None,
) -> None:
    """Display comprehensive metadata and schema summary for a Socrata dataset."""
    server_client = get_server(server, disk_cache_dir=cache_dir)

    with console.status(f"[bold green]Fetching dataset '{identifier}' from {server_client.host}..."):
        try:
            if refresh and identifier in server_client.memory_cache:
                del server_client.memory_cache[identifier]
            dataset = SocrataDataset(server=server_client, id=identifier)
        except Exception as e:
            console.print(f"[bold red]Error fetching dataset:[/] {e}")
            raise typer.Exit(code=1) from e

    effective_format = OutputFormat.JSON if json_output else (OutputFormat.MARKDOWN if markdown_output else format)
    ds_ext = (
        "json"
        if effective_format == OutputFormat.JSON
        else ("md" if effective_format in (OutputFormat.MARKDOWN, OutputFormat.MD) else "txt")
    )
    out_path = _resolve_output_path(output, f"dataset.{identifier}", ds_ext)

    if effective_format == OutputFormat.JSON:
        json_str = json.dumps(dataset.data, indent=2)
        if out_path:
            _write_or_print(json_str, out_path, "Dataset JSON saved to:")
        else:
            console.print_json(json_str)
        return

    if effective_format in (OutputFormat.MARKDOWN, OutputFormat.MD):
        md_text = dataset.get_markdown()
        if out_path:
            _write_or_print(md_text, out_path, "Dataset Markdown saved to:")
        else:
            typer.echo(md_text)
        return

    # Table format: Overview Panel + Variables Table
    records_str = f"{dataset.get_record_count():,}" if dataset.get_record_count() is not None else "Unknown"
    vars_str = str(dataset.get_variable_count())
    pub_date = dataset.publication_date.strftime("%Y-%m-%d %H:%M") if dataset.publication_date else "-"
    mod_date = (
        dataset.rows_updated_at.strftime("%Y-%m-%d %H:%M")
        if dataset.rows_updated_at
        else (dataset.view_last_modified.strftime("%Y-%m-%d %H:%M") if dataset.view_last_modified else "-")
    )
    tags_str = ", ".join(dataset.tags) if dataset.tags else "None"
    desc_str = dataset.description.strip() if dataset.description else "No description provided."
    if len(desc_str) > 300:
        desc_str = desc_str[:297] + "..."

    summary_text = (
        f"[bold cyan]Title:[/] {dataset.name}\n"
        f"[bold cyan]ID:[/] {dataset.id}\n"
        f"[bold cyan]Portal:[/] {server_client.host}\n"
        f"[bold cyan]Landing Page:[/] [link={dataset.landing_page}]{dataset.landing_page}[/link]\n"
        f"[bold cyan]API Endpoint:[/] [link={dataset.api_endpoint_url}]{dataset.api_endpoint_url}[/link]\n"
        f"[bold cyan]CSV Download:[/] [link={dataset.csv_download_url}]{dataset.csv_download_url}[/link]\n"
        f"[bold cyan]License:[/] {dataset.license}\n"
        f"[bold cyan]Records:[/] {records_str}   [bold cyan]Variables:[/] {vars_str}\n"
        f"[bold cyan]Published:[/] {pub_date}   [bold cyan]Last Modified:[/] {mod_date}\n"
        f"[bold cyan]Tags:[/] {tags_str}\n\n"
        f"[bold cyan]Description:[/] {desc_str}"
    )
    panel = Panel(summary_text, title=f"Dataset: {dataset.name} ({dataset.id})", border_style="cyan")

    table = Table(title=f"Columns / Variables for {dataset.id}")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Field Name", style="magenta")
    table.add_column("Label", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Cardinality", style="green", justify="right")
    table.add_column("Non-Null", style="blue", justify="right")
    table.add_column("Top Examples / Categories", style="white")

    for idx, var in enumerate(dataset.get_visible_variables(), start=1):
        card_str = f"{var.cardinality:,}" if var.cardinality is not None else "-"
        non_null_str = f"{var.non_null:,}" if var.non_null is not None else "-"
        examples: list[str] = []
        if var.top:
            for item in var.top[:3]:
                val = str(item.get("item", ""))
                examples.append(val if len(val) <= 20 else val[:17] + "...")
        examples_str = ", ".join(examples) if examples else "-"

        table.add_row(
            str(idx),
            var.name,
            var.label,
            var.socrata_data_type,
            card_str,
            non_null_str,
            examples_str,
        )

    if out_path:
        fc = Console(record=True, width=120)
        fc.print(panel)
        fc.print(table)
        _write_or_print(fc.export_text(), out_path, "Dataset overview saved to:")
    else:
        console.print(panel)
        console.print(table)


@app.command(name="variables")
@app.command(name="columns", help="Alias for 'variables'. Inspect dataset column schema.")
def list_variables(
    identifier: Annotated[str, typer.Argument(help="Socrata dataset 4x4 ID (e.g. vw6y-z8j6)")],
    server: Annotated[
        str | None,
        typer.Option("--server", "-s", envvar="SOCRATA_SERVER", help="Socrata server hostname"),
    ] = None,
    include_hidden: Annotated[
        bool,
        typer.Option("--include-hidden", "-a", help="Include all hidden columns (computed/deleted)"),
    ] = False,
    include_computed: Annotated[bool, typer.Option("--include-computed", help="Include computed columns")] = False,
    include_deleted: Annotated[bool, typer.Option("--include-deleted", help="Include deleted columns")] = False,
    format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format")] = OutputFormat.TABLE,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    markdown_output: Annotated[bool, typer.Option("--markdown", "--md", help="Output as Markdown")] = False,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write output to a file")] = None,
) -> None:
    """Inspect all column variables and metadata statistics for a dataset."""
    server_client = get_server(server)

    with console.status(f"[bold green]Fetching columns for '{identifier}' from {server_client.host}..."):
        try:
            dataset = SocrataDataset(server=server_client, id=identifier)
        except Exception as e:
            console.print(f"[bold red]Error fetching dataset:[/] {e}")
            raise typer.Exit(code=1) from e

    exclude_hidden = not include_hidden
    exclude_computed = not include_computed and not include_hidden
    exclude_deleted = not include_deleted and not include_hidden

    variables = dataset.get_variables(
        exclude_hidden=exclude_hidden,
        exclude_deleted=exclude_deleted,
        exclude_computed=exclude_computed,
    )

    effective_format = OutputFormat.JSON if json_output else (OutputFormat.MARKDOWN if markdown_output else format)
    v_ext = (
        "json"
        if effective_format == OutputFormat.JSON
        else (
            "csv"
            if effective_format == OutputFormat.CSV
            else "md"
            if effective_format in (OutputFormat.MARKDOWN, OutputFormat.MD)
            else "txt"
        )
    )
    out_path = _resolve_output_path(output, f"variables.{identifier}", v_ext)

    rows: list[dict[str, Any]] = []
    for var in variables:
        examples = []
        if var.top:
            for item in var.top[:5]:
                examples.append(f"{item.get('item')} ({item.get('count')})")
        rows.append(
            {
                "position": var.position,
                "field_name": var.name,
                "label": var.label,
                "data_type": var.socrata_data_type,
                "render_type": var.socrata_render_type,
                "cardinality": var.cardinality,
                "count": var.count,
                "non_null": var.non_null,
                "null": var.null,
                "smallest": var.smallest,
                "largest": var.largest,
                "is_computed": var.is_computed,
                "is_deleted": var.is_deleted,
                "top": var.top,
            }
        )

    if effective_format == OutputFormat.JSON:
        json_str = json.dumps(rows, indent=2, default=str)
        if out_path:
            _write_or_print(json_str, out_path, "Variables JSON saved to:")
        else:
            console.print_json(json_str)
        return

    if effective_format in (OutputFormat.MARKDOWN, OutputFormat.MD):
        md_lines = [
            f"# Variables for Dataset: {dataset.name} ({dataset.id})",
            "",
            "| Pos | Field Name | Label | Socrata Type | Cardinality | Non-Null | Null | Examples |",
            "|:---:|:---|:---|:---|---:|---:|---:|:---|",
        ]
        for r in rows:
            examples_str = ", ".join(str(x.get("item")) for x in (r["top"] or [])[:3])
            c_str = f"{r['cardinality']:,}" if r["cardinality"] is not None else "-"
            nn_str = f"{r['non_null']:,}" if r["non_null"] is not None else "-"
            nl_str = f"{r['null']:,}" if r["null"] is not None else "-"
            lbl_esc = str(r["label"]).replace("|", "\\|")
            md_lines.append(
                f"| {r['position']} | `{r['field_name']}` | {lbl_esc} | {r['data_type']} | "
                f"{c_str} | {nn_str} | {nl_str} | {examples_str} |"
            )
        _write_or_print("\n".join(md_lines), out_path, "Variables Markdown saved to:")
        return

    if effective_format == OutputFormat.CSV:
        from io import StringIO

        buf = StringIO()
        csv_cols = [
            "position",
            "field_name",
            "label",
            "data_type",
            "render_type",
            "cardinality",
            "count",
            "non_null",
            "null",
            "smallest",
            "largest",
        ]
        writer = csv.DictWriter(buf, fieldnames=csv_cols, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        _write_or_print(buf.getvalue(), out_path, "Variables CSV saved to:")
        return

    # Table format
    table = Table(title=f"Variables Schema for {dataset.name} ({dataset.id})")
    table.add_column("Pos", style="dim", justify="right")
    table.add_column("Field Name", style="magenta")
    table.add_column("Label", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Cardinality", style="green", justify="right")
    table.add_column("Non-Null", style="blue", justify="right")
    table.add_column("Null", style="red", justify="right")
    table.add_column("Top Examples (Frequency)", style="white")

    for r in rows:
        c_str = f"{r['cardinality']:,}" if r["cardinality"] is not None else "-"
        nn_str = f"{r['non_null']:,}" if r["non_null"] is not None else "-"
        nl_str = f"{r['null']:,}" if r["null"] is not None else "-"
        ex_parts = []
        if r["top"]:
            for item in r["top"][:3]:
                ex_parts.append(f"{item.get('item')} ({item.get('count')})")
        ex_str = ", ".join(ex_parts) if ex_parts else "-"

        table.add_row(
            str(r["position"]),
            r["field_name"],
            r["label"],
            r["data_type"],
            c_str,
            nn_str,
            nl_str,
            ex_str,
        )

    if out_path:
        fc = Console(record=True, width=130)
        fc.print(table)
        _write_or_print(fc.export_text(), out_path, "Variables table saved to:")
    else:
        console.print(table)


@app.command(name="metadata")
def metadata(
    dataset_ids: Annotated[list[str], typer.Argument(help="One or more Socrata dataset IDs (e.g. vw6y-z8j6)")],
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help=(
                "Metadata format: socrata (default), dcat, cdif-discovery, cdif-data-description, "
                "cdif, croissant, ddi, markdown, json (unique prefixes like cdif-disco, cdif-data supported)"
            ),
        ),
    ] = MetadataFormat.SOCRATA.value,
    flavor: Annotated[
        SerializationFlavor | None,
        typer.Option(
            "--flavor",
            help=(
                "Serialization flavor for multi-serialization formats like CDIF and DCAT (json, json-ld, ttl, xml, n3)"
            ),
        ),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-p",
            help="Format-dependent profile (e.g., for dcat: us [default], w3c, ap, ap-hvd)",
        ),
    ] = None,
    rdf_format: Annotated[
        str,
        typer.Option("--rdf-format", "-r", help="RDF serialization format for DCAT (turtle, json-ld, pretty-xml, nt)"),
    ] = "turtle",
    server: Annotated[
        str | None,
        typer.Option("--server", "-s", envvar="SOCRATA_SERVER", help="Socrata server hostname"),
    ] = None,
    include_computed: Annotated[
        bool,
        typer.Option("--include-computed", help="Include computed variables (Croissant, CDIF)"),
    ] = False,
    include_stats: Annotated[
        bool,
        typer.Option("--include-stats/--no-stats", help="Include summary statistics (CDIF data description)"),
    ] = True,
    include_codes: Annotated[
        bool | None,
        typer.Option(
            "--include-codes/--no-codes",
            help="Include code classifications (Croissant, CDIF data description)",
        ),
    ] = None,
    max_codes: Annotated[
        int | None,
        typer.Option("--max-codes", help="Maximum codes per variable (Croissant, CDIF data description)"),
    ] = None,
    threshold: Annotated[int, typer.Option("--threshold", help="Category count threshold (DDI-Codebook)")] = 500,
    cache_dir: Annotated[str | None, typer.Option("--cache-dir", help="Directory for disk cache")] = None,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write exported metadata to a file")] = None,
) -> None:
    """Export dataset metadata in Socrata JSON, DCAT, CDIF Discovery/Data Description, Croissant, DDI, or Markdown."""
    resolved_format = _resolve_enum_prefix(format, MetadataFormat)
    dcat_profile: DcatProfile = DcatProfile.US
    if profile is not None:
        if resolved_format == MetadataFormat.DCAT:
            dcat_profile = _resolve_enum_prefix(profile, DcatProfile, param_name="--profile")
        else:
            raise typer.BadParameter(f"--profile is not supported for format '{resolved_format.value}'.")
    server_client = get_server(server, disk_cache_dir=cache_dir)

    if not dataset_ids:
        console.print("[bold red]Error:[/] At least one dataset ID must be provided.")
        raise typer.Exit(code=1)

    with console.status(f"[bold green]Generating {resolved_format} metadata for {len(dataset_ids)} dataset(s)..."):
        try:
            if resolved_format in (MetadataFormat.SOCRATA, MetadataFormat.NATIVE, MetadataFormat.JSON):
                if len(dataset_ids) == 1:
                    ds = SocrataDataset(server=server_client, id=dataset_ids[0])
                    combined_content = json.dumps(ds.data, indent=2)
                else:
                    multi_data = [SocrataDataset(server=server_client, id=did).data for did in dataset_ids]
                    combined_content = json.dumps(multi_data, indent=2)

                out_path = _resolve_output_path(output, f"metadata.{dataset_ids[0]}", "json")
                if out_path:
                    _write_or_print(combined_content, out_path, "Socrata metadata saved to:")
                else:
                    console.print_json(combined_content)
                return

            if resolved_format == MetadataFormat.DCAT:
                dcat_datasets: list[SocrataDataset | str] = list(dataset_ids)
                generator = DcatGenerator(server=server_client, datasets=dcat_datasets, profile=dcat_profile)
                graph = generator.get_graph()

                if flavor is not None:
                    target_rdf, ext = resolve_serialization_flavor(flavor.value)
                    if target_rdf == "json":
                        target_rdf = "json-ld"
                else:
                    clean_rdf = rdf_format.lower()
                    if clean_rdf in ("ttl", "turtle"):
                        target_rdf = "turtle"
                        ext = "ttl"
                    elif clean_rdf in ("jsonld", "json-ld", "json"):
                        target_rdf = "json-ld"
                        ext = "json"
                    elif clean_rdf in ("xml", "rdf", "pretty-xml"):
                        target_rdf = "pretty-xml"
                        ext = "xml"
                    elif clean_rdf == "nt":
                        target_rdf = "nt"
                        ext = "nt"
                    elif clean_rdf == "n3":
                        target_rdf = "n3"
                        ext = "n3"
                    else:
                        target_rdf = clean_rdf
                        ext = "rdf"

                raw_bytes_or_str = graph.serialize(format=target_rdf)
                content = (
                    raw_bytes_or_str.decode("utf-8") if isinstance(raw_bytes_or_str, bytes) else str(raw_bytes_or_str)
                )
                out_path = _resolve_output_path(output, f"dcat.{dataset_ids[0]}", ext)

                if out_path:
                    _write_or_print(content, out_path, "DCAT metadata saved to:")
                else:
                    if target_rdf == "json-ld":
                        console.print_json(content)
                    else:
                        typer.echo(content.rstrip("\n"))
                return

            if resolved_format in (
                MetadataFormat.CDIF,
                MetadataFormat.CDIF_DISCOVERY,
                MetadataFormat.CDIF_DATA_DESCRIPTION,
            ):
                cdif_profile = (
                    "data_description" if resolved_format == MetadataFormat.CDIF_DATA_DESCRIPTION else "discovery"
                )
                chosen_flavor = flavor.value if flavor else SerializationFlavor.JSON_LD.value
                target_fmt, cdif_ext = resolve_serialization_flavor(chosen_flavor, default="json-ld")
                cdif_generator = CdifGenerator(server=server_client, datasets=list(dataset_ids))
                cdif_models = cdif_generator.get_models(
                    profile=cdif_profile,
                    include_computed=include_computed,
                    include_stats=include_stats,
                    include_codes=include_codes if include_codes is not None else False,
                    max_codes=max_codes if max_codes is not None else 20,
                )
                cdif_content = cdif_generator.serialize(cdif_models, flavor=chosen_flavor)
                file_prefix = f"{resolved_format.value}.{dataset_ids[0]}"
                out_path = _resolve_output_path(output, file_prefix, cdif_ext)
                if out_path:
                    _write_or_print(cdif_content, out_path, f"{resolved_format.value.upper()} metadata saved to:")
                elif target_fmt in ("json", "json-ld"):
                    console.print_json(cdif_content)
                else:
                    typer.echo(cdif_content.rstrip("\n"))
                return

            all_contents: list[str] = []
            for ds_id in dataset_ids:
                ds = SocrataDataset(server=server_client, id=ds_id)
                if resolved_format == MetadataFormat.CROISSANT:
                    croissant_obj = ds.get_croissant(
                        include_computed=include_computed,
                        include_codes=include_codes if include_codes is not None else True,
                        max_codes=max_codes if max_codes is not None else 100,
                    )
                    content = json.dumps(croissant_obj.to_json(), indent=2, default=str)
                    ext = "croissant.json"
                elif resolved_format == MetadataFormat.DDI:
                    content = ds.get_ddi_codebook(category_count_threshold=threshold)
                    ext = "ddic.xml"
                elif resolved_format in (MetadataFormat.MARKDOWN, MetadataFormat.MD):
                    content = ds.get_markdown()
                    ext = "md"
                else:
                    raise ValueError(f"Unsupported format: {resolved_format}")
                all_contents.append(content)

        except Exception as e:
            console.print(f"[bold red]Metadata Error:[/] {e}")
            raise typer.Exit(code=1) from e

    combined_content = "\n\n".join(all_contents)
    out_path = _resolve_output_path(output, f"{resolved_format.value}.{dataset_ids[0]}", ext)

    if out_path:
        _write_or_print(combined_content, out_path, f"{resolved_format.value.upper()} metadata saved to:")
    else:
        if resolved_format == MetadataFormat.CROISSANT and len(all_contents) == 1:
            console.print_json(all_contents[0])
        else:
            typer.echo(combined_content.rstrip("\n"))


@app.command(name="export")
def export_data(
    dataset_id: Annotated[str, typer.Argument(help="Socrata dataset 4x4 ID (e.g. vw6y-z8j6)")],
    format: Annotated[
        DataFormat,
        typer.Option("--format", "-f", help="Data export format (csv, json)"),
    ] = DataFormat.CSV,
    limit: Annotated[int | None, typer.Option("--limit", "-l", help="Maximum number of records to export")] = None,
    where: Annotated[str | None, typer.Option("--where", "-w", help="SoQL query $where filter condition")] = None,
    select: Annotated[str | None, typer.Option("--select", help="SoQL query $select column list")] = None,
    order: Annotated[str | None, typer.Option("--order", help="SoQL query $order sort clause")] = None,
    server: Annotated[
        str | None,
        typer.Option("--server", "-s", envvar="SOCRATA_SERVER", help="Socrata server hostname"),
    ] = None,
    app_token: Annotated[
        str | None,
        typer.Option("--app-token", envvar="SOCRATA_APP_TOKEN", help="Socrata App Token (optional)"),
    ] = None,
    cache_dir: Annotated[str | None, typer.Option("--cache-dir", help="Directory for disk cache")] = None,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write exported data to a file")] = None,
) -> None:
    """Export dataset data records from Socrata in CSV or JSON format."""
    server_client = get_server(server, disk_cache_dir=cache_dir)
    endpoint = f"https://{server_client.host}/resource/{dataset_id}.{format.value}"

    params: dict[str, Any] = {}
    if limit is not None:
        params["$limit"] = limit
    if where is not None:
        params["$where"] = where
    if select is not None:
        params["$select"] = select
    if order is not None:
        params["$order"] = order

    headers: dict[str, str] = {
        "User-Agent": "dartfx-socrata/0.1.0 (https://github.com/DataArtifex/socrata-toolkit)",
    }
    token = app_token or os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token

    with console.status(f"[bold green]Exporting {format.value.upper()} data for {dataset_id}..."):
        try:
            resp = requests.get(endpoint, params=params, headers=headers, timeout=60)
            if resp.status_code != 200:
                console.print(f"[bold red]Data Export Error ({resp.status_code}):[/] {resp.text[:300]}")
                raise typer.Exit(code=1)
            content = resp.text
        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[bold red]Data Export Error:[/] {e}")
            raise typer.Exit(code=1) from e

    out_path = _resolve_output_path(output, f"data.{dataset_id}", format.value)
    if out_path:
        _write_or_print(content, out_path, f"{format.value.upper()} data saved to:")
    else:
        if format == DataFormat.JSON:
            try:
                console.print_json(content)
            except Exception:
                typer.echo(content.rstrip("\n"))
        else:
            typer.echo(content.rstrip("\n"))


@app.command(name="code")
@app.command(name="codegen", help="Alias for 'code'. Generate client code for dataset access.")
def generate_code(
    identifier: Annotated[str, typer.Argument(help="Socrata dataset 4x4 ID (e.g. vw6y-z8j6)")],
    env: Annotated[
        str,
        typer.Option(
            "--env",
            "-e",
            help="Target language/tool (python-pandas, r-socrata, stata, sas, ruby, dotnet, ps1, jquery)",
        ),
    ] = "python-pandas",
    server: Annotated[
        str | None,
        typer.Option("--server", "-s", envvar="SOCRATA_SERVER", help="Socrata server hostname"),
    ] = None,
    cache_dir: Annotated[str | None, typer.Option("--cache-dir", help="Directory for disk cache")] = None,
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write generated code to a file")] = None,
) -> None:
    """Generate client data access code for a dataset across supported programming environments."""
    server_client = get_server(server, disk_cache_dir=cache_dir)

    env_clean = env.lower().strip()
    if env_clean not in ENV_MAP:
        valid_envs = sorted({v[0] for v in ENV_MAP.values()})
        console.print(f"[bold red]Error:[/] Unknown environment '{env}'. Supported: {', '.join(valid_envs)}")
        raise typer.Exit(code=1)

    target_env, _lexer_name, file_ext = ENV_MAP[env_clean]

    with console.status(f"[bold green]Generating {target_env} code for {identifier}..."):
        try:
            try:
                dataset = SocrataDataset(server=server_client, id=identifier)
                code_text = dataset.get_code(target_env)
            except Exception:
                template_file = f"generate_{target_env}.j2"
                template = jinja_env.get_template(template_file)
                code_text = template.render(host=server_client.host, dataset_id=identifier)
        except Exception as e:
            console.print(f"[bold red]Code generation error:[/] {e}")
            raise typer.Exit(code=1) from e

    out_path = _resolve_output_path(output, f"code.{identifier}", file_ext)

    if out_path:
        _write_or_print(code_text, out_path, f"{target_env} script saved to:")
    else:
        typer.echo(code_text.rstrip("\n"))


if __name__ == "__main__":
    app()
