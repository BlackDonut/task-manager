-- Migration: add task_groups / ticket_group_members tables
-- ORM: app/models/task_group.py
-- Run: sqlcmd -S <server> -d task_manager_db -U sa -P <password> -C -i scripts\migrate_add_task_groups.sql
-- Idempotent: safe to run multiple times

-- ---- task_groups table ------------------------------------------------------
IF OBJECT_ID('dbo.task_groups', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.task_groups (
        id          INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        name        NVARCHAR(200) NOT NULL,
        description TEXT              NULL,
        delete_flg  SMALLINT      NOT NULL DEFAULT 0,
        created_by  INT               NULL REFERENCES dbo.users(id),
        created_at  DATETIME      NOT NULL,
        updated_at  DATETIME      NOT NULL
    );
END
GO

-- ---- ticket_group_members table --------------------------------------------
IF OBJECT_ID('dbo.ticket_group_members', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ticket_group_members (
        id          INT      NOT NULL IDENTITY(1,1) PRIMARY KEY,
        group_id    INT      NOT NULL REFERENCES dbo.task_groups(id),
        ticket_id   INT      NOT NULL REFERENCES dbo.tickets(id),
        added_at    DATETIME NOT NULL,
        CONSTRAINT uq_ticket_group_member UNIQUE (group_id, ticket_id)
    );
END
GO
