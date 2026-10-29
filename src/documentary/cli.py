"""命令行入口 `doc`。定时任务和手动运行用的是同一条命令（architecture.md 第 1 节）。"""

from __future__ import annotations

import sys
from enum import StrEnum
from typing import Annotated

import typer

from documentary import __version__
from documentary.core.config import (
    ConfigError,
    Settings,
    check_config,
    load_catalog,
    load_settings,
)
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
    typer.echo(f"TMDB key：{'已设置' if settings.tmdb_api_key else '未设置（采集 TMDB 时需要）'}")
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


class Source(StrEnum):
    tmdb = "tmdb"


@app.command()
def discover(
    source: Annotated[Source, typer.Option(help="只跑某个来源（迭代 1 只有 tmdb）")] = Source.tmdb,
    brand: Annotated[str | None, typer.Option(help="只跑某个品牌，写编号，如 UK-2")] = None,
    series: Annotated[str | None, typer.Option(help="只跑某个重点栏目，写简称，如 nova")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="只抓取和初筛，列出会新增什么，不写数据库")
    ] = False,
) -> None:
    """发现新内容（迭代 1：TMDB，试点品牌和栏目）。"""
    from documentary.core.http import SourceError
    from documentary.pipeline.discover import TargetNotFound, discover_tmdb

    if brand and series:
        typer.secho("✗ --brand 和 --series 只能选一个", fg="red", err=True)
        raise typer.Exit(2)
    settings = _settings()
    try:
        catalog = load_catalog(settings.config_dir)
    except ConfigError as e:
        for line in e.lines:
            typer.secho(f"✗ {line}", fg="red", err=True)
        raise typer.Exit(1) from None
    if not db_status(settings).up_to_date:
        typer.secho("✗ 数据库未初始化或需要升级，先运行 uv run doc db upgrade", fg="red", err=True)
        raise typer.Exit(1)

    params = {"source": source.value, "brand": brand, "series": series, "dry_run": dry_run}
    engine = make_engine(settings)

    def go(run_id: int | None):
        return discover_tmdb(
            engine,
            settings,
            catalog,
            brand=brand,
            series=series,
            dry_run=dry_run,
            run_id=run_id,
            progress=typer.echo,
        )

    try:
        if dry_run:  # dry-run 什么都不写，运行记录也不记
            result = go(None)
        else:
            with record_run(engine, "discover", params=params) as run:
                try:
                    result = go(run.id)
                except SourceError as e:
                    run.stats = {"fatal": str(e)}
                    raise
                run.stats = result.stats()
                run.status = result.status
    except TargetNotFound as e:
        typer.secho(f"✗ {e}", fg="red", err=True)
        raise typer.Exit(2) from None
    except SourceError as e:
        typer.secho(f"✗ {e}", fg="red", err=True)
        raise typer.Exit(1) from None
    finally:
        engine.dispose()
    _print_discover(result)
    if result.status != "success":
        raise typer.Exit(1)


def _print_discover(result) -> None:
    from documentary.pipeline.prescreen import EXCLUDE, INCLUDE
    from documentary.pipeline.states import TRACKING_ZH

    sugg_zh = {INCLUDE: "建议收录", EXCLUDE: "建议排除", None: "需人工"}
    if result.dry_run:
        for t in result.targets:
            if not t.new:
                continue
            typer.echo(f"\n—— {t.label}：会新增 {len(t.new)} 条 ——")
            for it in t.new:
                year = it.year or "    "
                typer.echo(
                    f"  {year}  {it.title}  [{TRACKING_ZH.get(it.status, it.status)}"
                    f"，{sugg_zh[it.suggestion]}]  TMDB {it.tmdb_id}"
                )
    verb = "会新增" if result.dry_run else "新增"
    typer.echo(f"\n汇总（TMDB 请求 {result.requests} 次）：")
    total = 0
    for t in result.targets:
        n_inc = sum(1 for i in t.new if i.suggestion == INCLUDE)
        n_exc = sum(1 for i in t.new if i.suggestion == EXCLUDE)
        n_man = len(t.new) - n_inc - n_exc
        total += len(t.new)
        if t.skipped:
            line = "没有运行（前面出错已停止）"
        elif t.error:
            line = f"失败：{t.error}"
        else:
            since = f"{t.since} 起" if t.since else ""
            line = f"{since}找到 {t.found}，{verb} {len(t.new)}"
            if t.new:
                line += f"（建议收录 {n_inc}、建议排除 {n_exc}、需人工 {n_man}）"
            if t.seasons_added or t.episodes_added:
                line += f"，新季 {t.seasons_added}、新集 {t.episodes_added}"
        color = "red" if (t.error or t.skipped) else None
        typer.secho(f"  {t.label:<40} {line}", fg=color)
    typer.echo(f"  合计{verb} {total} 条")
    if result.dry_run:
        typer.secho("dry-run：没有写数据库", fg="yellow")
    elif result.status == "success":
        typer.secho("✓ 完成", fg="green")
    elif result.status == "partial":
        typer.secho("⚠ 部分失败：失败的品牌/栏目下次从各自上次成功的时间继续", fg="yellow")
    else:
        typer.secho("✗ 失败", fg="red")


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
