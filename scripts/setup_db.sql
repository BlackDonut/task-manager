-- =====================================================================
-- setup_db.sql
-- データベース・全テーブル作成 + 初期データ投入スクリプト
--
-- 実行手順:
--   1. SQL Server Management Studio (SSMS) または sqlcmd で実行する
--   2. 接続先: localhost の既定インスタンス（Windows 認証）
--   3. 初回のみ: マスター DB に接続した状態でデータベースを作成する
--
-- sqlcmd での実行例（Windows 認証）:
--   sqlcmd -S localhost -E -i scripts\setup_db.sql
--
-- sqlcmd での実行例（SA 認証）:
--   sqlcmd -S localhost -U sa -P <password> -i scripts\setup_db.sql
-- =====================================================================

-- =====================================================================
-- Step 1: データベース作成
-- =====================================================================
USE [master];
GO

IF DB_ID(N'task_manager_db') IS NULL
BEGIN
    CREATE DATABASE [task_manager_db];
    PRINT N'データベース task_manager_db を作成しました。';
END
ELSE
    PRINT N'データベース task_manager_db は既に存在します。スキップ。';
GO

USE [task_manager_db];
GO

-- =====================================================================
-- Step 2: users テーブル作成
-- =====================================================================
IF OBJECT_ID('dbo.users', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[users] (
        id           INT           IDENTITY(1,1) NOT NULL,
        login_id     NVARCHAR(100) NOT NULL,
        display_name NVARCHAR(100) NOT NULL,
        delete_flg   SMALLINT      NOT NULL CONSTRAINT DF_users_delete_flg DEFAULT 0,
        CONSTRAINT PK_users PRIMARY KEY (id),
        CONSTRAINT UQ_users_login_id UNIQUE (login_id)
    );

    CREATE INDEX IX_users_login_id ON [dbo].[users] (login_id) WHERE delete_flg = 0;

    PRINT N'users テーブルを作成しました。';
END
ELSE
    PRINT N'users テーブルは既に存在します。スキップ。';
GO

-- =====================================================================
-- Step 3: projects テーブル作成
-- =====================================================================
IF OBJECT_ID('dbo.projects', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[projects] (
        id         INT           IDENTITY(1,1) NOT NULL,
        name       NVARCHAR(200) NOT NULL,
        delete_flg SMALLINT      NOT NULL CONSTRAINT DF_projects_delete_flg DEFAULT 0,
        CONSTRAINT PK_projects PRIMARY KEY (id)
    );

    CREATE INDEX IX_projects_name ON [dbo].[projects] (name) WHERE delete_flg = 0;

    PRINT N'projects テーブルを作成しました。';
END
ELSE
    PRINT N'projects テーブルは既に存在します。スキップ。';
GO

-- =====================================================================
-- Step 4: tickets テーブル作成
-- =====================================================================
IF OBJECT_ID('dbo.tickets', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[tickets] (
        id          INT           IDENTITY(1,1) NOT NULL,
        project_id  INT           NOT NULL,
        tracker     NVARCHAR(20)  NOT NULL,
        status      NVARCHAR(20)  NOT NULL,
        priority    NVARCHAR(20)  NOT NULL,
        subject     NVARCHAR(500) NOT NULL,
        assignee_id INT           NULL,
        due_date    DATE          NULL,
        done_ratio  INT           NOT NULL CONSTRAINT DF_tickets_done_ratio DEFAULT 0,
        delete_flg  SMALLINT      NOT NULL CONSTRAINT DF_tickets_delete_flg DEFAULT 0,
        created_at  DATETIME2     NOT NULL CONSTRAINT DF_tickets_created_at DEFAULT SYSDATETIME(),
        updated_at  DATETIME2     NOT NULL CONSTRAINT DF_tickets_updated_at DEFAULT SYSDATETIME(),
        CONSTRAINT PK_tickets          PRIMARY KEY (id),
        CONSTRAINT FK_tickets_project  FOREIGN KEY (project_id)  REFERENCES [dbo].[projects](id),
        CONSTRAINT FK_tickets_assignee FOREIGN KEY (assignee_id) REFERENCES [dbo].[users](id),
        -- tracker の値はアプリ側 Literal 定義（schemas.py）と一致させること
        CONSTRAINT CK_tickets_tracker  CHECK (tracker  IN ('bug', 'feature', 'support', 'task')),
        -- status の値はアプリ側 Literal 定義（schemas.py）と一致させること
        CONSTRAINT CK_tickets_status   CHECK (status   IN ('new', 'in_progress', 'resolved', 'closed', 'rejected')),
        -- priority の値はアプリ側 Literal 定義（schemas.py）と一致させること
        CONSTRAINT CK_tickets_priority CHECK (priority IN ('urgent', 'high', 'normal', 'low')),
        CONSTRAINT CK_tickets_done_ratio CHECK (done_ratio BETWEEN 0 AND 100)
    );

    CREATE INDEX IX_tickets_project_id ON [dbo].[tickets] (project_id) WHERE delete_flg = 0;
    CREATE INDEX IX_tickets_status     ON [dbo].[tickets] (status)     WHERE delete_flg = 0;
    CREATE INDEX IX_tickets_updated_at ON [dbo].[tickets] (updated_at DESC) WHERE delete_flg = 0;

    PRINT N'tickets テーブルを作成しました。';
END
ELSE
    PRINT N'tickets テーブルは既に存在します。スキップ。';
GO

-- =====================================================================
-- Step 5: 初期データ投入（冪等: 既に存在する場合はスキップ）
-- =====================================================================

-- --- users ---
IF NOT EXISTS (SELECT 1 FROM [dbo].[users] WHERE login_id = 'yamada.taro')
BEGIN
    INSERT INTO [dbo].[users] (login_id, display_name) VALUES
        ('yamada.taro',   N'山田 太郎'),
        ('sato.hanako',   N'佐藤 花子'),
        ('suzuki.ichiro', N'鈴木 一郎'),
        ('tanaka.yuki',   N'田中 雪'),
        ('ito.kenji',     N'伊藤 賢二');
    PRINT N'users 初期データを投入しました。';
END
ELSE
    PRINT N'users 初期データは既に存在します。スキップ。';
GO

-- --- projects ---
IF NOT EXISTS (SELECT 1 FROM [dbo].[projects] WHERE delete_flg = 0)
BEGIN
    INSERT INTO [dbo].[projects] (name) VALUES
        (N'基幹システム刷新'),
        (N'モバイルアプリ開発'),
        (N'インフラ整備');
    PRINT N'projects 初期データを投入しました。';
END
ELSE
    PRINT N'projects 初期データは既に存在します。スキップ。';
GO

-- --- tickets ---
IF NOT EXISTS (SELECT 1 FROM [dbo].[tickets] WHERE delete_flg = 0)
BEGIN
    -- project_id / assignee_id は IDENTITY のため SELECT で取得する
    DECLARE @proj1 INT = (SELECT id FROM [dbo].[projects] WHERE name = N'基幹システム刷新');
    DECLARE @proj2 INT = (SELECT id FROM [dbo].[projects] WHERE name = N'モバイルアプリ開発');
    DECLARE @proj3 INT = (SELECT id FROM [dbo].[projects] WHERE name = N'インフラ整備');

    DECLARE @u1 INT = (SELECT id FROM [dbo].[users] WHERE login_id = 'yamada.taro');
    DECLARE @u2 INT = (SELECT id FROM [dbo].[users] WHERE login_id = 'sato.hanako');
    DECLARE @u3 INT = (SELECT id FROM [dbo].[users] WHERE login_id = 'suzuki.ichiro');
    DECLARE @u4 INT = (SELECT id FROM [dbo].[users] WHERE login_id = 'tanaka.yuki');
    DECLARE @u5 INT = (SELECT id FROM [dbo].[users] WHERE login_id = 'ito.kenji');

    INSERT INTO [dbo].[tickets]
        (project_id, tracker,    status,       priority, subject,                                     assignee_id, due_date,     done_ratio)
    VALUES
        (@proj1, 'bug',     'new',        'urgent', N'ログイン画面でセッションが切れない不具合',      @u1, '2026-05-15', 0),
        (@proj1, 'feature', 'in_progress','high',   N'ダッシュボードに遅延タスク一覧を追加',          @u2, '2026-05-30', 40),
        (@proj1, 'task',    'in_progress','normal',  N'DB 接続プールのチューニング',                  @u3, '2026-06-10', 20),
        (@proj1, 'bug',     'resolved',   'high',   N'一覧画面で N+1 クエリが発生している',           @u1, '2026-04-30', 100),
        (@proj1, 'support', 'closed',     'low',    N'環境変数設定手順の問い合わせ',                  NULL,'2026-04-20', 100),
        (@proj2, 'feature', 'new',        'high',   N'プッシュ通知機能の実装',                        @u4, '2026-06-01', 0),
        (@proj2, 'bug',     'in_progress','urgent', N'iOS 端末でクラッシュする問題',                  @u5, '2026-05-10', 60),
        (@proj2, 'task',    'new',        'normal',  N'API レスポンスのキャッシュ戦略を検討',          @u4, '2026-06-20', 0),
        (@proj2, 'feature', 'in_progress','low',    N'ダークモード対応',                              @u2, '2026-07-01', 15),
        (@proj2, 'bug',     'rejected',   'normal',  N'フォント描画ズレ（仕様範囲内と判断）',          NULL, NULL,        0),
        (@proj3, 'task',    'new',        'urgent', N'本番サーバの SSL 証明書更新',                   @u3, '2026-05-08', 0),
        (@proj3, 'feature', 'in_progress','high',   N'CI/CD パイプラインの構築',                     @u1, '2026-05-31', 50),
        (@proj3, 'task',    'resolved',   'normal',  N'ログ収集基盤の整備',                           @u5, '2026-04-25', 100),
        (@proj3, 'bug',     'in_progress','high',   N'バックアップジョブが夜間に失敗する',             @u3, '2026-05-12', 30);

    PRINT N'tickets 初期データを投入しました。';
END
ELSE
    PRINT N'tickets 初期データは既に存在します。スキップ。';
GO

-- =====================================================================
-- Step 6: 確認クエリ
-- =====================================================================
SELECT
    t.TABLE_NAME,
    p.row_count AS [行数]
FROM INFORMATION_SCHEMA.TABLES t
JOIN sys.dm_db_partition_stats p
    ON p.object_id = OBJECT_ID(t.TABLE_NAME)
    AND p.index_id IN (0, 1)
WHERE t.TABLE_TYPE = 'BASE TABLE'
  AND t.TABLE_SCHEMA = 'dbo'
  AND t.TABLE_NAME IN ('users', 'projects', 'tickets')
ORDER BY t.TABLE_NAME;
GO

PRINT N'セットアップ完了。';
GO
