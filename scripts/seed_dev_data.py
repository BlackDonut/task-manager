"""開発用シードデータ挿入スクリプト。

チケット一覧画面（SCR-T001）で全パターンが表示されるよう不足データを追加する。

追加するパターン:
  - tracker × status の全組み合わせ（特に rejected / feature:closed / support:in_progress）
  - 全リリースタイプ・ステータスのリリースに紐づくチケット（0件リリースの解消）
  - 先行チケット依存関係（predecessor_ids の表示確認）
  - 担当者なし・期日なし・期日超過など各種パターン

実行方法:
  python scripts/seed_dev_data.py

注意:
  - 開発環境専用。本番環境では絶対に実行しないこと
  - 冪等性なし（重複挿入に注意）
"""

from __future__ import annotations

import asyncio
import datetime
import sys

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# ---- 接続設定 ---------------------------------------------------------------

DSN = (
    "mssql+aioodbc://sa:initP%40ss01@localhost:1433/task_manager_db"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
)

NOW = datetime.datetime(2026, 5, 8, 12, 0, 0)

# 日付定数（今日基準）
TODAY = datetime.date(2026, 5, 8)
YESTERDAY = datetime.date(2026, 5, 7)
PAST_OVERDUE = datetime.date(2026, 4, 1)   # 期限超過
PAST_WEEK = datetime.date(2026, 5, 3)       # 1週間以内（at-risk）
NEAR_FUTURE = datetime.date(2026, 6, 30)    # 近未来
FAR_FUTURE = datetime.date(2026, 12, 31)    # 遠未来


# ---- ヘルパー ---------------------------------------------------------------

def _ticket(
    product_id: int,
    tracker: str,
    status: str,
    priority: str,
    subject: str,
    *,
    assignee_id: int | None = None,
    due_date: datetime.date | None = NEAR_FUTURE,
    done_ratio: int = 0,
    parent_id: int | None = None,
    depth: int = 0,
    release_id: int | None = None,
) -> dict:
    return {
        "product_id": product_id,
        "tracker": tracker,
        "status": status,
        "priority": priority,
        "subject": subject,
        "assignee_id": assignee_id,
        "due_date": due_date.isoformat() if due_date else None,
        "done_ratio": done_ratio,
        "parent_id": parent_id,
        "depth": depth,
        "release_id": release_id,
        "delete_flg": 0,
        "created_at": NOW.isoformat(sep=" "),
        "updated_at": NOW.isoformat(sep=" "),
    }


async def insert_tickets(conn, tickets: list[dict]) -> list[int]:
    """チケットを一括挿入してIDリストを返す。"""
    ids = []
    for t in tickets:
        await conn.execute(text(
            "INSERT INTO tickets "
            "(product_id, tracker, status, priority, subject, assignee_id, "
            " due_date, done_ratio, parent_id, depth, release_id, delete_flg, "
            " created_at, updated_at) "
            "VALUES "
            "(:product_id, :tracker, :status, :priority, :subject, :assignee_id, "
            " :due_date, :done_ratio, :parent_id, :depth, :release_id, :delete_flg, "
            " :created_at, :updated_at)"
        ), t)
        r = await conn.execute(text("SELECT @@IDENTITY"))
        ids.append(int(r.scalar()))
    return ids


async def seed() -> None:  # noqa: PLR0912, PLR0915
    engine = create_async_engine(DSN, echo=False)
    async with engine.begin() as conn:

        # ---- 現在のデータを把握 -------------------------------------------------

        # フェーズチケット（親候補）取得
        r = await conn.execute(text(
            "SELECT id, product_id FROM tickets "
            "WHERE delete_flg=0 AND tracker='phase' ORDER BY id"
        ))
        phase_rows = r.fetchall()
        phase_by_product: dict[int, list[int]] = {}
        for pid_col, prod_id in phase_rows:
            phase_by_product.setdefault(prod_id, []).append(pid_col)

        # depth=1チケット（孫チケットの親候補）取得
        r = await conn.execute(text(
            "SELECT TOP 8 id, product_id FROM tickets "
            "WHERE delete_flg=0 AND depth=1 AND tracker='task' ORDER BY id"
        ))
        depth1_rows = r.fetchall()
        depth1_by_product: dict[int, list[int]] = {}
        for tid, prod_id in depth1_rows:
            depth1_by_product.setdefault(prod_id, []).append(tid)

        # 0件リリース（チケットが1件も紐づいていないリリース）を取得
        r = await conn.execute(text(
            "SELECT pr.id, pr.product_id, pr.release_type, pr.status "
            "FROM product_releases pr "
            "WHERE pr.delete_flg=0 "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM tickets t "
            "  WHERE t.release_id = pr.id AND t.delete_flg=0"
            ") "
            "ORDER BY pr.product_id, pr.id"
        ))
        empty_releases = r.fetchall()
        print(f"0件リリース: {len(empty_releases)} 件")
        for rel_id, prod_id, rel_type, rel_status in empty_releases:
            print(f"  id={rel_id} product_id={prod_id} type={rel_type} status={rel_status}")

        # ---- 1. tracker × status 全組み合わせ追加 --------------------------------
        # 追加対象:
        #   bug/rejected, feature/closed, feature/rejected,
        #   phase/resolved, phase/rejected,
        #   support/in_progress, support/rejected, task/rejected

        print("\n[1] tracker × status 全組み合わせを追加...")
        missing_combos: list[tuple[int, str, str, str, int | None]] = []
        # (product_id, tracker, status, priority, phase_parent_id)

        for prod_id in [1, 2, 3, 4]:
            phases = phase_by_product.get(prod_id, [])
            parent = phases[0] if phases else None

            # bug/rejected — 担当者なし・期日なし（却下理由: 仕様外バグ）
            missing_combos.append((prod_id, "bug", "rejected", "normal", parent))
            # feature/closed
            missing_combos.append((prod_id, "feature", "closed", "normal", parent))
            # feature/rejected — 担当者なし（機能要件却下）
            missing_combos.append((prod_id, "feature", "rejected", "low", None))
            # phase/resolved — フェーズ完了
            missing_combos.append((prod_id, "phase", "resolved", "normal", None))
            # phase/rejected — フェーズ却下
            missing_combos.append((prod_id, "phase", "rejected", "low", None))
            # support/in_progress
            missing_combos.append((prod_id, "support", "in_progress", "high", parent))
            # support/rejected
            missing_combos.append((prod_id, "support", "rejected", "normal", None))
            # task/rejected — 担当者なし・期日なし
            missing_combos.append((prod_id, "task", "rejected", "low", None))

        combo_tickets = []
        for i, (prod_id, tracker, status, priority, parent_id) in enumerate(missing_combos):
            depth = 1 if parent_id else 0
            # trackerとstatusを組み合わせた題名
            tracker_ja = {"bug": "バグ", "feature": "機能", "phase": "フェーズ",
                          "support": "サポート", "task": "タスク"}[tracker]
            status_ja = {"new": "新規", "in_progress": "進行中", "resolved": "解決済み",
                         "closed": "終了", "rejected": "却下"}[status]
            subject = f"[{status_ja}] {tracker_ja} テストデータ（製品{prod_id}）"

            # rejected/closedは done_ratio=100
            done_ratio = 100 if status in ("resolved", "closed") else 0
            # 期日: rejected/closedは過去日、in_progressは近未来
            due_date: datetime.date | None
            if status in ("rejected", "closed", "resolved"):
                due_date = PAST_OVERDUE
            elif status == "in_progress":
                due_date = NEAR_FUTURE
            elif tracker == "phase":
                due_date = FAR_FUTURE
            else:
                due_date = None

            # 担当者: rejectedの半数はnull（却下で担当者未設定）
            assignee_id: int | None = (i % 5) + 1 if status != "rejected" else None

            combo_tickets.append(_ticket(
                prod_id, tracker, status, priority, subject,
                assignee_id=assignee_id,
                due_date=due_date,
                done_ratio=done_ratio,
                parent_id=parent_id,
                depth=depth,
            ))

        new_ids = await insert_tickets(conn, combo_tickets)
        print(f"  {len(new_ids)} 件挿入完了: {new_ids}")

        # ---- 2. 0件リリースにチケットを追加 ---------------------------------------
        print("\n[2] 0件リリースにチケットを追加...")
        release_tickets = []
        for rel_id, prod_id, rel_type, rel_status in empty_releases:
            phases = phase_by_product.get(prod_id, [])
            parent_phase_id = phases[0] if phases else None

            # リリース種別ラベル
            type_ja = {
                "initial": "初回リリース",
                "spec_change": "仕様変更",
                "version_upgrade": "バージョンアップ",
                "maintenance": "保守",
            }[rel_type]
            status_ja = {"planning": "計画中", "in_progress": "進行中", "completed": "完了"}[rel_status]

            # 各0件リリースにタスク3件 + バグ1件 + フェーズ配下タスク1件を追加
            rel = rel_id  # release_id 用ショートハンド

            # ルートタスク（担当者あり・期日あり）
            release_tickets.append(_ticket(
                prod_id, "task", "new", "normal",
                f"【{type_ja}/{status_ja}】セットアップ作業",
                assignee_id=1, due_date=NEAR_FUTURE, release_id=rel,
            ))
            # 担当者なしタスク
            release_tickets.append(_ticket(
                prod_id, "task", "new", "high",
                f"【{type_ja}/{status_ja}】技術調査",
                assignee_id=None, due_date=FAR_FUTURE, release_id=rel,
            ))
            # 進行中タスク
            release_tickets.append(_ticket(
                prod_id, "task", "in_progress", "normal",
                f"【{type_ja}/{status_ja}】実装作業",
                assignee_id=2, due_date=NEAR_FUTURE, done_ratio=50, release_id=rel,
            ))
            # バグ
            release_tickets.append(_ticket(
                prod_id, "bug", "new", "urgent",
                f"【{type_ja}/{status_ja}】不具合#1",
                assignee_id=3, due_date=PAST_WEEK, release_id=rel,
            ))
            # フェーズ配下タスク（親あり depth=1）
            if parent_phase_id:
                release_tickets.append(_ticket(
                    prod_id, "task", "new", "low",
                    f"【{type_ja}/{status_ja}】フェーズ配下作業",
                    assignee_id=4, due_date=FAR_FUTURE,
                    parent_id=parent_phase_id, depth=1, release_id=rel,
                ))

        release_ids = await insert_tickets(conn, release_tickets)
        print(f"  {len(release_ids)} 件挿入完了")

        # ---- 3. 先行チケット依存関係を追加（predecessor表示確認用） ----------------
        print("\n[3] 先行チケット依存関係を追加...")
        # 新規挿入したIDのうち最初の数件で predecessor 関係を作る
        added_all = new_ids + release_ids
        if len(added_all) >= 4:
            # 挿入したIDを2ペアで先行→後続にする
            pairs = [
                (added_all[0], added_all[1]),
                (added_all[2], added_all[3]),
            ]
            dep_count = 0
            for pred_id, succ_id in pairs:
                # 同一製品チケット同士か確認してから挿入
                r = await conn.execute(text(
                    "SELECT product_id FROM tickets WHERE id=:id"
                ), {"id": pred_id})
                p1 = r.scalar()
                r = await conn.execute(text(
                    "SELECT product_id FROM tickets WHERE id=:id"
                ), {"id": succ_id})
                p2 = r.scalar()
                if p1 == p2:
                    # 重複チェック
                    r = await conn.execute(text(
                        "SELECT COUNT(*) FROM ticket_dependencies "
                        "WHERE predecessor_id=:p AND successor_id=:s"
                    ), {"p": pred_id, "s": succ_id})
                    if r.scalar() == 0:
                        await conn.execute(text(
                            "INSERT INTO ticket_dependencies (predecessor_id, successor_id) "
                            "VALUES (:p, :s)"
                        ), {"p": pred_id, "s": succ_id})
                        dep_count += 1
            print(f"  {dep_count} 件の依存関係を追加")

        # ---- 4. 完了確認 --------------------------------------------------------
        print("\n[4] 最終データ確認...")
        r = await conn.execute(text(
            "SELECT tracker, status, COUNT(*) as cnt "
            "FROM tickets WHERE delete_flg=0 "
            "GROUP BY tracker, status "
            "ORDER BY tracker, status"
        ))
        print("tracker × status 一覧:")
        for row in r:
            print(f"  {row[0]:10} | {row[1]:12} | {row[2]} 件")

        r = await conn.execute(text(
            "SELECT pr.release_type, pr.status, COUNT(t.id) as cnt "
            "FROM product_releases pr "
            "LEFT JOIN tickets t ON t.release_id = pr.id AND t.delete_flg=0 "
            "WHERE pr.delete_flg=0 "
            "GROUP BY pr.release_type, pr.status "
            "ORDER BY pr.release_type, pr.status"
        ))
        print("\nリリースタイプ × ステータスごとチケット数:")
        for row in r:
            flag = "" if row[2] > 0 else " ← 0件（警告）"
            print(f"  {row[0]:20} | {row[1]:12} | {row[2]} 件{flag}")

        r = await conn.execute(text(
            "SELECT COUNT(*) FROM ticket_dependencies"
        ))
        print(f"\nticket_dependencies: {r.scalar()} 件")

        r = await conn.execute(text(
            "SELECT COUNT(*) FROM tickets WHERE delete_flg=0"
        ))
        print(f"tickets 総件数: {r.scalar()} 件")

    print("\n✅ シード完了")


if __name__ == "__main__":
    asyncio.run(seed())
