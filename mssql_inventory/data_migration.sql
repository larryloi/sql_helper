-- MSSQL linked-server -> local-server batch migration script
-- Usage: edit variables below and run on the target SQL Server instance (the sink).
-- Assumptions:
--  - Linked server name is reachable and called 'LINKEDSVR_ABC'
--  - Source and sink tables have compatible schemas (same columns/order).
--  - Primary key column exists and is provided via @pk_column.
--  - atime and btime are DATETIME2-like columns on the source table.
--  - Use schema names if different than 'dbo'.

SET NOCOUNT ON;
SET XACT_ABORT ON;  -- ensures transactions abort on error

-- ======== PARAMETERS (edit these before running) ========
DECLARE
    @LinkedServer SYSNAME = N'LINKEDSVR_ABC',     -- linked server name
    @src_db SYSNAME      = N'SrcDatabase',        -- source database on linked server
    @src_schema SYSNAME  = N'dbo',                -- source schema (commonly dbo)
    @src_table SYSNAME   = N'SrcTable',           -- source table name
    @sink_db SYSNAME     = N'TargetDatabase',     -- local sink database
    @sink_schema SYSNAME = N'dbo',                -- sink schema
    @sink_table SYSNAME  = N'TargetTable',        -- sink table name
    @pk_column SYSNAME   = N'id',                 -- primary key column name (on source and sink)
    @pk_type SYSNAME     = N'BIGINT',             -- 'BIGINT' or 'UNIQUEIDENTIFIER' or other SQL type that fits pk
    @BatchSize INT       = 1000,                  -- number of rows per batch
    @atime DATETIME2     = '2025-01-01T00:00:00', -- start time (inclusive)
    @btime DATETIME2     = '2025-12-31T00:00:00'; -- end time (exclusive)
-- ======================================================

-- Validate some sensible defaults
IF @BatchSize <= 0 SET @BatchSize = 1000;

-- Temp tables for keys
IF OBJECT_ID('tempdb..#AllKeys') IS NOT NULL DROP TABLE #AllKeys;
IF OBJECT_ID('tempdb..#BatchKeys') IS NOT NULL DROP TABLE #BatchKeys;

IF @pk_type = 'UNIQUEIDENTIFIER'
BEGIN
    CREATE TABLE #AllKeys (pk UNIQUEIDENTIFIER NOT NULL);
    CREATE TABLE #BatchKeys (pk UNIQUEIDENTIFIER NOT NULL);
END
ELSE
BEGIN
    -- default numeric PK
    CREATE TABLE #AllKeys (pk BIGINT NOT NULL);
    CREATE TABLE #BatchKeys (pk BIGINT NOT NULL);
END

-- Build dynamic SQL to pull all matching PKs from the linked server into #AllKeys.
-- We'll parameterize @atime and @btime so we can safely pass them to sp_executesql.
DECLARE @sql NVARCHAR(MAX);
SET @sql = N'
INSERT INTO #AllKeys (pk)
SELECT ' + QUOTENAME(@pk_column) + N'
FROM ' + QUOTENAME(@LinkedServer) + N'.' + QUOTENAME(@src_db) + N'.' + QUOTENAME(@src_schema) + N'.' + QUOTENAME(@src_table) + N' WITH (NOLOCK)
WHERE ' + QUOTENAME(N'atime') + N' >= @atime AND ' + QUOTENAME(N'btime') + N' < @btime
ORDER BY ' + QUOTENAME(N'atime') + N', ' + QUOTENAME(@pk_column) + N';';

-- Execute dynamic SQL, passing time parameters
EXEC sp_executesql
    @sql,
    N'@atime DATETIME2, @btime DATETIME2',
    @atime = @atime, @btime = @btime;

-- Quick check: if no rows, exit.
IF (SELECT COUNT(1) FROM #AllKeys) = 0
BEGIN
    PRINT 'No rows found matching the time range - nothing to migrate.';
    GOTO CleanupAndExit;
END

-- Create a forward-only fast cursor over #AllKeys to iterate
DECLARE cur_keys CURSOR LOCAL FAST_FORWARD FOR
    SELECT pk FROM #AllKeys ORDER BY pk;

OPEN cur_keys;

DECLARE @current_pk_sql_variant sql_variant; -- generic holder
-- Use typed variables for fetch (choose correct local var, per pk type)
IF @pk_type = 'UNIQUEIDENTIFIER'
BEGIN
    DECLARE @pk_guid UNIQUEIDENTIFIER;
END
ELSE
BEGIN
    DECLARE @pk_bigint BIGINT;
END

DECLARE @count_in_batch INT = 0;

-- Helper: build static identifier strings for sink/source
DECLARE
    @sink_full NVARCHAR(4000) = QUOTENAME(DB_NAME()) + N'.' + QUOTENAME(@sink_schema) + N'.' + QUOTENAME(@sink_table),
    @sink_local_obj NVARCHAR(4000) = QUOTENAME(@sink_db) + N'.' + QUOTENAME(@sink_schema) + N'.' + QUOTENAME(@sink_table),
    @src_fulllink NVARCHAR(4000) = QUOTENAME(@LinkedServer) + N'.' + QUOTENAME(@src_db) + N'.' + QUOTENAME(@src_schema) + N'.' + QUOTENAME(@src_table);

-- Loop through cursor, accumulate PKs into #BatchKeys. When reach @BatchSize, do a batch insert.
WHILE 1 = 1
BEGIN
    -- Fetch next
    IF @pk_type = 'UNIQUEIDENTIFIER'
        FETCH NEXT FROM cur_keys INTO @pk_guid;
    ELSE
        FETCH NEXT FROM cur_keys INTO @pk_bigint;

    IF @@FETCH_STATUS <> 0
        BREAK;

    -- Insert into batch temp table
    IF @pk_type = 'UNIQUEIDENTIFIER'
        INSERT INTO #BatchKeys (pk) VALUES (@pk_guid);
    ELSE
        INSERT INTO #BatchKeys (pk) VALUES (@pk_bigint);

    SET @count_in_batch = @count_in_batch + 1;

    IF @count_in_batch >= @BatchSize
    BEGIN
        -- Perform the batch insert from source -> sink, within a transaction
        BEGIN TRY
            BEGIN TRAN;

            -- Build dynamic SQL to insert rows matching batch keys from linked server to local sink.
            -- We also filter out rows already present in sink (NOT EXISTS) to avoid duplicates.
            DECLARE @insert_sql NVARCHAR(MAX) = N'
INSERT INTO ' + QUOTENAME(@sink_db) + N'.' + QUOTENAME(@sink_schema) + N'.' + QUOTENAME(@sink_table) + N'
(
    -- insert all columns (SELECT *). Ensure sink schema matches source schema.
    -- If you prefer explicit column list, replace SELECT * with SELECT col1, col2, ...
)
SELECT src.*
FROM ' + @src_fulllink + N' AS src WITH (NOLOCK)
WHERE src.' + QUOTENAME(@pk_column) + N' IN (SELECT pk FROM #BatchKeys) 
  AND NOT EXISTS (
      SELECT 1 FROM ' + QUOTENAME(@sink_db) + N'.' + QUOTENAME(@sink_schema) + N'.' + QUOTENAME(@sink_table) + N' sink
      WHERE sink.' + QUOTENAME(@pk_column) + N' = src.' + QUOTENAME(@pk_column) + N'
  );';

            -- Execute insert
            EXEC sp_executesql @insert_sql;

            COMMIT TRAN;
            PRINT CONCAT('Committed batch of ', @count_in_batch, ' rows.');
        END TRY
        BEGIN CATCH
            IF XACT_STATE() <> 0 ROLLBACK TRAN;
            DECLARE @err_code INT = ERROR_NUMBER();
            DECLARE @err_msg NVARCHAR(4000) = ERROR_MESSAGE();
            PRINT CONCAT('Error during batch insert: ', @err_code, ' - ', @err_msg);
            -- depending on policy, you may choose to abort entirely:
            -- BREAK; or continue to next batch
        END CATCH

        -- Clear batch
        DELETE FROM #BatchKeys;
        SET @count_in_batch = 0;
    END
END

-- After cursor finished, if remaining items in #BatchKeys, do one more insert
IF (SELECT COUNT(1) FROM #BatchKeys) > 0
BEGIN
    BEGIN TRY
        BEGIN TRAN;

        DECLARE @insert_sql_last NVARCHAR(MAX) = N'
INSERT INTO ' + QUOTENAME(@sink_db) + N'.' + QUOTENAME(@sink_schema) + N'.' + QUOTENAME(@sink_table) + N'
SELECT src.*
FROM ' + @src_fulllink + N' AS src WITH (NOLOCK)
WHERE src.' + QUOTENAME(@pk_column) + N' IN (SELECT pk FROM #BatchKeys)
  AND NOT EXISTS (
      SELECT 1 FROM ' + QUOTENAME(@sink_db) + N'.' + QUOTENAME(@sink_schema) + N'.' + QUOTENAME(@sink_table) + N' sink
      WHERE sink.' + QUOTENAME(@pk_column) + N' = src.' + QUOTENAME(@pk_column) + N'
  );';

        EXEC sp_executesql @insert_sql_last;

        COMMIT TRAN;
        PRINT CONCAT('Committed final batch of ', (SELECT COUNT(1) FROM #BatchKeys), ' rows.');
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRAN;
        PRINT CONCAT('Error during final batch insert: ', ERROR_MESSAGE());
    END CATCH

    DELETE FROM #BatchKeys;
END

-- Cleanup
CLOSE cur_keys;
DEALLOCATE cur_keys;

CleanupAndExit:
DROP TABLE IF EXISTS #AllKeys;
DROP TABLE IF EXISTS #BatchKeys;

PRINT 'Migration completed.';