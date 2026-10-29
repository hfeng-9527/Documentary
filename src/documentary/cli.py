"""命令行入口 `doc`。定时任务和手动运行用的是同一条命令（architecture.md 第 1 节）。"""

from __future__ import annotations

import sys

import typer

from documentary import __version__
from documentary.core.config import ConfigError, Settings, check_config, load_settings
from documentary.core.db import db_status, make_engine, record_run, upgrade
from documentary.core.logging import setup_logging

app = typer.Typer(help="纪录片跟踪", no_args_is_help=True, add_completion=False)
db_app = typer.Typer(help="数据库", no_args_is_help=True)
app.add_typer(db_app, name="db")


@app.callback()
def _main() -> None:
    # Windows 上把输出重定向到文件时默认是 GBK，中文以外的符号（✓ 等）会报错，统一用 UTF-8
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower() != "utf-8":
            stream.reconfigure(encoding="utf-8")


def _settings() -> Settings:
    try:
        settings = load_settings()
    except ConfigError as e:
        for line in e.lines:
            typer.secho(f"✗ {line}", fg="red", err=True)
        raise typer.Exit(1) from None
    setup_logging(settings)
    return settings


@app.command()
def version() -> None:
    """显示版本号。"""
    typer.echo(__version__)


@app.command("check-config")
def check_config_cmd() -> None:
    """检查 .env 和 config/*.yaml，并记一条运行记录。"""
    settings = _settings()
    typer.echo(f"数据目录：{settings.data_dir}")
    typer.echo(f"配置目录：{settings.config_dir}")
    typer.echo(f"代理：{settings.proxy_url or '未设置（迭代 1 起境外接口需要）'}")
    typer.echo("")

    result = check_config(settings.config_dir)
    for name, st in result.stats.items():
        missing = "" if st.missing_ids is None else f"，还没查编号 {st.missing_ids}"
        typer.echo(f"  {name:<15} {st.count:>3} 条{missing}")
    if result.warnings:
        typer.echo(f"\n提醒（{len(result.warnings)} 条，现在不用处理）：")
        for w in result.warnings:
            typer.secho(f"  · {w}", fg="yellow")
    if result.errors:
        typer.echo(f"\n错误（{len(result.errors)} 条）：")
        for e in result.errors:
            typer.secho(f"  ✗ {e}", fg="red")

    _save_run(settings, result)

    if result.ok:
        typer.secho("\n✓ 配置检查通过", fg="green")
    else:
        typer.secho("\n✗ 配置检查未通过", fg="red")
        raise typer.Exit(1)


def _save_run(settings: Settings, result) -> None:
    if not db_status(settings).up_to_date:
        typer.secho(
            "\n（数据库未初始化或需要升级，这次没有记运行记录。先运行 doc db upgrade）", fg="yellow"
        )
        return
    engine = make_engine(settings)
    try:
        with record_run(engine, "check-config") as run:
            run.stats = {
                "errors": len(result.errors),
                "warnings": len(result.warnings),
                "files": {n: st.count for n, st in result.stats.items()},
            }
            if not result.ok:
                run.status = "failed"
    finally:
        engine.dispose()


@db_app.command("upgrade")
def db_upgrade() -> None:
    """建库，或升级到最新表结构（升级前自动备份）。"""
    settings = _settings()
    status, backup = upgrade(settings)
    if backup:
        typer.echo(f"已备份：{backup}")
    typer.secho(f"✓ 数据库已是最新（表结构版本 {status.current}）：{settings.db_path}", fg="green")


@app.command()
def web() -> None:
    """启动网页。"""
    import uvicorn

    from documentary.web.app import create_app

    settings = _settings()
    typer.echo(f"网页地址：http://{settings.web_host}:{settings.web_port}  （Ctrl+C 停止）")
    uvicorn.run(create_app(settings), host=settings.web_host, port=settings.web_port)
